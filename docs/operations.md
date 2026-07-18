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
