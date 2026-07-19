# Operations

Concrete setup steps for the alerting, budget, and data-retention controls this project relies on — most are real one-time `gcloud`/console operations, not something scripted into CI/CD (same category as the IAM/WIF bootstrapping documented as manual in [ADR-0006](architecture-decisions/ADR-0006-deployment-topology.md)'s "What's Still Manual"). Task numbers below refer to the security/ops audit that added this document.

## 1. GCP Budget Alert (already in place — see ADR-0006)

A €10/month budget alert (50/90/100% thresholds, email to the billing account admin) already exists on the project, set up as part of the original deployment (ADR-0006, decision "Three independent layers of cost/abuse control"). Not re-created here; referenced for completeness since the rest of this document is about the alerts that were *missing*. To inspect or recreate it:

```bash
gcloud billing budgets list --billing-account="$BILLING_ACCOUNT_ID"
```

Console equivalent: Billing → Budgets & alerts, on the linked billing account.

## 2. Uptime Check on `GET /health` + Alerting Policy

```bash
# Uptime check — Cloud Monitoring pings the real deployed URL, not the
# Cloud Run "service is running" signal, which can be green while the app
# itself is broken (e.g. the REQUIRE_PERSISTENT_STORAGE fail-fast guard
# in app/main.py never gets exercised by a synthetic check that only
# looks at container status).
gcloud monitoring uptime create tiny-detective-api-health \
  --resource-type=uptime-url \
  --resource-labels=host=tiny-detective-api-n7fn34d2jq-ew.a.run.app \
  --path=/health \
  --protocol=https \
  --period=5 \
  --timeout=10s

# Alerting policy — fires when the uptime check fails from a majority of
# regions for 5 consecutive minutes. Requires a notification channel
# (email) created first:
gcloud alpha monitoring channels create \
  --display-name="Ops Email" \
  --type=email \
  --channel-labels=email_address=YOUR_EMAIL_HERE

gcloud alpha monitoring policies create \
  --display-name="tiny-detective-api health check failing" \
  --condition-display-name="Uptime check failure" \
  --condition-filter='metric.type="monitoring.googleapis.com/uptime_check/check_passed" AND resource.type="uptime_url"' \
  --condition-threshold-value=1 \
  --condition-threshold-comparison=COMPARISON_LT \
  --condition-threshold-duration=300s \
  --notification-channels=CHANNEL_ID_FROM_PREVIOUS_COMMAND
```

Console equivalent: Monitoring → Uptime checks → Create, then Monitoring → Alerting → Create Policy, condition type "Uptime check", targeting the check just created.

## 3. Cloud Run 5xx Rate Alert

```bash
gcloud alpha monitoring policies create \
  --display-name="tiny-detective-api elevated 5xx rate" \
  --condition-display-name="5xx response rate" \
  --condition-filter='resource.type="cloud_run_revision" AND resource.labels.service_name="tiny-detective-api" AND metric.type="run.googleapis.com/request_count" AND metric.labels.response_code_class="5xx"' \
  --condition-threshold-value=5 \
  --condition-threshold-comparison=COMPARISON_GT \
  --condition-threshold-duration=300s \
  --condition-aggregations=alignmentPeriod=300s,perSeriesAligner=ALIGN_RATE \
  --notification-channels=CHANNEL_ID_FROM_STEP_2
```

Threshold (>5 5xx responses in a 5-minute window) is a starting point for this project's real traffic level, not a scientifically derived number — tighten it if the demo ever sees enough real traffic for that to be noisy, loosen it if it fires on normal cold-start blips. Console equivalent: Monitoring → Alerting → Create Policy, metric `run.googleapis.com/request_count` filtered to `response_code_class = 5xx`.

## 4. OpenAI Spend Limits

Set directly in the OpenAI platform dashboard (not a `gcloud`-scriptable resource — a separate provider, separate control plane):

1. https://platform.openai.com/settings/organization/limits → set a monthly budget (a hard cap here, unlike the GCP budget alert which only notifies — OpenAI's own limit actually stops further spend once hit).
2. https://platform.openai.com/settings/organization/billing/overview → optionally enable email alerts at a lower threshold than the hard cap, so there's warning before requests start failing.

This is a real, separate spend backstop from the GCP budget alert — GCP's alert covers Cloud Run/Firestore cost, this covers the actual OpenAI token spend, which is this project's dominant real cost driver (`/hint`, `/cases/generate`).

## 5. Firestore Point-in-Time Recovery

```bash
gcloud firestore databases update --database='(default)' \
  --point-in-time-recovery \
  --project="$GCP_PROJECT_ID"
```

Enables a 7-day rolling recovery window (Firestore's own default when PITR is on) — protects against an accidental bad write or bug wiping real data (players, attempts, hint history), independent of and complementary to the TTL policies below (PITR is "undo a mistake," TTL is "delete on purpose, on schedule"). Real cost impact: PITR roughly doubles storage cost for affected collections at GCP's current pricing — negligible at this project's actual data volume, worth checking again if that ever changes materially.

## 6. Firestore TTL Policies

The application already writes an `expireAt` field (see `app/infrastructure/firestore/ttl.py`) onto every `case_attempts`, `hint_requests`, and `rate_limits` document — 180 days out for attempts/hints, 7 days out for the daily rate-limit counters. That field alone does nothing: Firestore's TTL feature only starts deleting documents once a policy is explicitly pointed at it, which is the one-time admin step below.

```bash
gcloud firestore fields ttls update expireAt \
  --collection-group=case_attempts \
  --enable-ttl \
  --project="$GCP_PROJECT_ID"

gcloud firestore fields ttls update expireAt \
  --collection-group=hint_requests \
  --enable-ttl \
  --project="$GCP_PROJECT_ID"

gcloud firestore fields ttls update expireAt \
  --collection-group=rate_limits \
  --enable-ttl \
  --project="$GCP_PROJECT_ID"
```

Deliberately **not** applied to `cases`, `players`, or `daily_cases` — curated/live-generated case content and player progress have no natural expiry, and `daily_cases` documents are small and few (one per calendar day the app has run). Verify a policy actually took effect (Firestore TTL deletion isn't instant — GCP's own documentation says it can take up to 24 hours to start, and doesn't guarantee exact-time deletion after that):

```bash
gcloud firestore fields ttls describe expireAt --collection-group=case_attempts --project="$GCP_PROJECT_ID"
```

**Not independently verified against real GCP for this pass** — same honest scope as this project's other real-Firestore-behavior caveats (composite indexes, transaction atomicity under production concurrency, see `docs/scalability.md`): the application-side `expireAt` field is unit- and emulator-tested (the emulator does not enforce or simulate TTL deletion, so that half is inherently untestable without real GCP), but the `gcloud firestore fields ttls update` commands above were written from GCP's documented syntax, not run against a real project from this environment. Run them for real and confirm with `describe` before assuming deletion is actually active.

## 7. Cloud Scheduler: Automated Daily Case Publish

See [ADR-0006's Cloud Scheduler amendment](architecture-decisions/ADR-0006-deployment-topology.md#amendment-automated-daily-case-publishing-via-cloud-scheduler) for why this exists: the daily case's publish step was a manual admin call with no reminder and no fallback, and was genuinely forgotten twice in production. This replaces the human step with a scheduled call to the new `POST /admin/cases/publish-next-daily` endpoint, which picks the case itself.

**Originally set up with a static `X-Admin-Token` header; now uses OIDC instead — kept below only as a documented incident, not the live configuration.** `gcloud scheduler jobs create`/`update` echo the full created/updated job resource back to stdout by default, including any `--headers` value — the first real run of the `create` command below printed the real `X-Admin-Token` in plaintext into a terminal/chat transcript. Treated as a real compromise and rotated (see ADR-0006's amendment). The header-based approach has since been replaced entirely with OIDC verification (below), which structurally cannot leak this way — no secret value is ever stored in the job resource at all, so there's nothing for `describe`, a stray log line, or a forgotten `--quiet` to expose. This block is kept as a record of what not to do, and because the header path still exists in `require_admin` for human/manual admin API use — just no longer for the Scheduler job.

```bash
# DO NOT USE for the Scheduler job — see above. Kept for reference only
# (e.g. manual curl testing of admin endpoints). If a header carrying a
# secret is ever passed to a gcloud command for any reason, always
# redirect output as shown, never run it bare.
ADMIN_TOKEN=$(gcloud secrets versions access latest --secret=ADMIN_API_TOKEN --project="$GCP_PROJECT_ID")
curl -s -X POST -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  https://tiny-detective-api-n7fn34d2jq-ew.a.run.app/admin/cases/publish-next-daily
unset ADMIN_TOKEN
```

**Live configuration: OIDC, verified by the application itself (`app/infrastructure/auth/scheduler_oidc.py`), no secret in the job resource.**

```bash
# One-time: a dedicated service account for the Scheduler job, with no
# extra IAM roles — it doesn't need roles/run.invoker (this service is
# --allow-unauthenticated; the token is verified at the app layer, not by
# Cloud Run's own IAM gate), and needs no Firestore/Secret Manager access
# either. Its only purpose is to be an identity Cloud Scheduler can prove
# via a Google-signed token.
gcloud iam service-accounts create tiny-detective-scheduler \
  --project="$GCP_PROJECT_ID" \
  --display-name="Cloud Scheduler: daily case auto-publish"

gcloud scheduler jobs create http publish-daily-case \
  --location="$GCP_REGION" \
  --schedule="0 6 * * *" \
  --time-zone="Etc/UTC" \
  --uri="https://tiny-detective-api-n7fn34d2jq-ew.a.run.app/admin/cases/publish-next-daily" \
  --http-method=POST \
  --oidc-service-account-email="tiny-detective-scheduler@${GCP_PROJECT_ID}.iam.gserviceaccount.com" \
  --oidc-token-audience="https://tiny-detective-api-n7fn34d2jq-ew.a.run.app/admin/cases/publish-next-daily" \
  --attempt-deadline=30s \
  --max-retry-attempts=3 \
  --project="$GCP_PROJECT_ID"
```

No `--quiet >/dev/null` needed here — there's no secret in the command or its output to suppress, which is the entire point. `SCHEDULER_SERVICE_ACCOUNT_EMAIL` and `SCHEDULER_OIDC_AUDIENCE` (matching the two flags above) are set as Cloud Run env vars in `deploy.yml`, not by a separate manual step — they're ordinary (non-secret) configuration, unlike `ADMIN_API_TOKEN`.

`0 6 * * *` (06:00 UTC) is an arbitrary but fixed daily time, chosen to run well before typical player traffic in the demo's expected timezone — not derived from any real usage data, since none exists yet. Verify the job actually works before trusting it silently:

```bash
gcloud scheduler jobs run publish-daily-case --location="$GCP_REGION" --project="$GCP_PROJECT_ID"
gcloud scheduler jobs describe publish-daily-case --location="$GCP_REGION" --project="$GCP_PROJECT_ID" \
  --format="value(status.code)"
curl -s https://tiny-detective-api-n7fn34d2jq-ew.a.run.app/cases/daily | head -c 200
```

**Alerting on scheduler failure — actually created and verified against real GCP, not just documented.** The first draft of this section guessed at a metric (`cloudscheduler.googleapis.com/job/execution_count`) that turned out not to exist — checked for real via `projects.metricDescriptors.list` and a direct `timeSeries.list` call, both came back empty/404 for that metric type. Real inspection of actual execution logs (`gcloud logging read 'resource.type="cloud_scheduler_job" AND resource.labels.job_id="publish-daily-case"'`) showed Cloud Scheduler instead writes structured `AttemptFinished`/`AttemptStarted` log entries with a real `severity` field (confirmed `INFO` on the job's real successful executions) — GCP's documented behavior is that this becomes `ERROR` on a failed attempt (max-retries-exhausted or non-2xx), the same signal this project's own Error Reporting integration (task 12) already relies on elsewhere. Built the alert on that, as a log-based metric plus a threshold policy — no guessed metric type involved:

```bash
# One-time: a log-based metric counting non-success executions of this
# specific job, from real log structure inspected via `gcloud logging read`
# above, not from documentation alone.
gcloud logging metrics create publish_daily_case_failures \
  --project="$GCP_PROJECT_ID" \
  --description="Cloud Scheduler failed to publish the daily case (publish-daily-case job, non-success execution)" \
  --log-filter='resource.type="cloud_scheduler_job" AND resource.labels.job_id="publish-daily-case" AND severity>=ERROR'

# Reuses the notification channel from §2 if one already exists; this
# project's channel was created fresh in the same pass as this alert
# (§2's channel had been documented but never actually run before this).
gcloud alpha monitoring policies create \
  --display-name="tiny-detective-api daily case publish failing" \
  --project="$GCP_PROJECT_ID" \
  --notification-channels="CHANNEL_ID_FROM_STEP_2" \
  --combiner=OR \
  --condition-display-name="publish-daily-case non-success execution" \
  --condition-filter='resource.type="cloud_scheduler_job" AND metric.type="logging.googleapis.com/user/publish_daily_case_failures"' \
  --duration=0s \
  --if='> 0' \
  --aggregation='{"alignmentPeriod": "3600s", "perSeriesAligner": "ALIGN_COUNT"}'
```

Verified with `gcloud alpha monitoring policies describe <name>` immediately after creation: `enabled: true`, the correct `notificationChannels` entry, and the exact filter above — confirms the policy exists and is wired correctly. What's *not* yet been observed is a real firing (that needs an actual non-success execution, which the job hasn't had) — same honest scope as this project's other real-GCP caveats: configuration is verified, end-to-end firing behavior is not, and won't be until either a real failure happens or one is deliberately (and carefully) provoked.

This alert covers the empty-pool case (§7's `publish-next-daily` returns `409`, which Cloud Scheduler counts as a failed attempt) and every other way the job could fail (endpoint down, network error, 5xx) with one mechanism — broader and simpler than a case specifically targeted at the empty-pool 409, and it complements rather than replaces the deterministic `logger.error(...)` call in `app/api/routes/admin.py`'s `publish_next_daily` route (that one fires the moment the *application* detects an empty catalog, independent of whether Cloud Scheduler's own retry/logging behavior works as expected — two independent signals for the same underlying failure, not one relying on the other).
