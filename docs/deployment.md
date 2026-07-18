# Deployment

Live: [`https://tiny-detective-ai.web.app`](https://tiny-detective-ai.web.app) (Flutter web, Firebase Hosting) talking to `https://tiny-detective-api-n7fn34d2jq-ew.a.run.app` (FastAPI, Cloud Run). Both deployed to GCP project `tiny-detective-ai`, region `europe-west1`. Full reasoning: [ADR-0006](architecture-decisions/ADR-0006-deployment-topology.md).

## Topology

```text
GitHub Actions (CI)  --workflow_run(success)-->  GitHub Actions (Deploy)
                                                        |
                                    +-------------------+-------------------+
                                    v                                       v
                            deploy-api (WIF auth)                  deploy-web (needs: deploy-api)
                                    |                                       |
                    Artifact Registry <- build/push                flutter build web
                                    |                          --dart-define=API_BASE_URL=<api_url>
                            Cloud Run deploy                                |
                    (tiny-detective-api-runtime SA)              Firebase Hosting deploy
                                    |                          (firebase-hosting-deployer key)
                    Firestore (native, europe-west1)
                    Secret Manager (ADMIN_API_TOKEN, OPENAI_API_KEY)
```

## CI/CD Pipeline

`.github/workflows/ci.yml` — five jobs, all triggered on every push/PR to `main`:

- `frontend-checks` — `flutter analyze`, `flutter test`, `flutter build web --release`.
- `backend-checks` — full `uv run pytest` (`services/api`).
- `contract-checks` — `uv run pytest tests/contract` only. A deliberately redundant subset of `backend-checks`, kept separate so a broken public API contract shows up in the PR checks list by name, not buried in a generic "backend-checks failed." See ADR-0006.
- `ai-tool-checks` — `uv run pytest` (`tools/ai-content`).
- `docker-build` — `docker build -f services/api/Dockerfile .` (build context is the repo root, not `services/api`, since the live case-generation feature makes `services/api` depend on `tools/ai-content` as a path dependency — see ADR-0007), build-only, no push. Proves the image builds; the real push happens in `deploy.yml`.

`.github/workflows/deploy.yml` — triggered by CI's `workflow_run` completing successfully on `main` (plus `workflow_dispatch` for manual redeploys and for bootstrapping the very first run, since `workflow_run` only starts firing once the workflow file already exists on the default branch). One workflow, two jobs, `deploy-web` declaring `needs: deploy-api` — a simplification from the originally-planned three separate `workflow_run`-chained files; see ADR-0006 for why.

- `deploy-api`: authenticates via Workload Identity Federation, builds and pushes the backend image to Artifact Registry (tagged with the commit SHA), deploys to Cloud Run, deploys `firestore.rules`/`firestore.indexes.json`, then smoke-tests `/health` before the job is allowed to succeed.
- `deploy-web` (`needs: deploy-api`): builds the Flutter web app with `--dart-define=API_BASE_URL` set to the Cloud Run URL `deploy-api` just produced (a job output, not re-derived), deploys it to Firebase Hosting's live channel via a scoped service-account key.

## Public-Demo Cost and Abuse Control

The `/hint` endpoint calls OpenAI on every request and has no authentication — three independent controls, not one, since the URL is now public:

1. Per-IP rate limiting, 5/minute, on `/hint` specifically (`app/api/rate_limiting.py`).
2. `--max-instances=3` on the Cloud Run service, `--min-instances=0` explicit (scale-to-zero when idle).
3. A €10/month GCP budget alert (50/90/100% thresholds) on the billing account.

Free tier covers normal demo traffic completely; these exist for the outlier, not the baseline. Full reasoning in ADR-0006.

## Live Case Generation

`POST /cases/generate` runs the real AI pipeline (generator + logic judge + safety judge, reused directly from `tools/ai-content`) live, on a player's click, and streams real progress via SSE. Bounded by two independent, atomic, Firestore-backed daily counters (a 50/day success cap and a 300/day attempt cap that also counts judge-rejected attempts — cost isn't bounded by successes alone) plus a 3/minute per-IP limit. Real cost, measured against the deployed production service (not just estimated): a single-attempt success cost `$0.00053`; a fully-exhausted 5-attempt request cost `$0.00224` total. Worst case at the attempt cap (300/day) stays under ~$0.15–0.18/day — well inside the existing €10 budget alert. Every result is stored with `source="live_generated"`, distinguishing it from curated content; the actual daily case is never touched by this feature. A real `429` (temporarily lowered cap) and real judge rejections with the visible SSE restart were both directly observed against the live deployment. Full reasoning, including the empirical retry-count tuning and a real concurrency bug found by testing the atomic counter under load: [ADR-0007](architecture-decisions/ADR-0007-live-case-generation.md).

## Startup Guard: Fail Fast on Misconfigured Persistence

`REQUIRE_PERSISTENT_STORAGE=true` is set only in the Cloud Run deploy (`deploy.yml`). At app startup, `app/main.py` checks this against `is_firestore_configured()` and raises immediately if it's true but Firestore isn't actually configured — e.g. a future deploy that forgets to set `GOOGLE_CLOUD_PROJECT`. Without this, that mistake would be silent: the app starts fine on the in-memory fallback, `/health` returns `200` (it doesn't touch storage), and the deploy job's smoke test — the one thing that was supposed to catch a broken deploy — would report success on a backend quietly forgetting every player, hint, and attempt on its next cold start. With the guard, the container fails to start, Cloud Run never reports it healthy, and the smoke test's `curl` gets a connection failure instead of a false positive. No-op locally and under pytest (the env var is never set there), so local dev and the test suite are unaffected.

## Secrets and IAM

- `ADMIN_API_TOKEN` and `OPENAI_API_KEY` live in Secret Manager, injected into Cloud Run via `--set-secrets` (never as plain env vars, never printed during setup).
- `github-actions-deployer` (deploy-time identity, WIF, no stored key) and `tiny-detective-api-runtime` (what Cloud Run actually runs as) are separate service accounts with separate, minimal roles — deploy-time permissions and runtime permissions are not the same blast radius.
- `firebase-hosting-deployer` is the one service account with a stored JSON key (as the `FIREBASE_SERVICE_ACCOUNT` GitHub secret) — scoped to `roles/firebasehosting.admin` only, nothing else.

## Verified Live (not just deployed)

- Public `/cases/daily` does not leak `solution`, `culpritSuspectId`, or `privateReasoning` — checked against the actual response, not assumed from the code.
- `/admin/...` routes return `401` with no token and with a wrong token.
- The 6th `/hint` request within a minute from the same caller returns `429` — confirms the `X-Forwarded-For`-based rate-limit key works through Cloud Run's real proxy layer, which nothing short of a real deploy could confirm.
- Real Firestore documents exist post-deploy across all five collections (`players`, `daily_cases`, `hint_requests`, `cases`, and `case_attempts` once a solution is submitted) — the thing [ADR-0005](architecture-decisions/ADR-0005-firestore-data-model.md) could only ever check against the emulator.
- A full browser playthrough against the live URL — load the daily case, request a hint (real OpenAI call, grounded, non-revealing), submit the correct suspect, see the scored result — works end-to-end.

## What's Still Manual

- Firebase/GCP project creation, billing account linkage, and all IAM/WIF/Secret Manager setup were one-time `gcloud`/`firebase` CLI operations, not scripted into any workflow — reasonable for a single project, would need real infrastructure-as-code (Terraform or similar) if this pattern had to repeat.
- Publishing the daily case (`POST /admin/cases/{id}/publish-daily`) is a manual admin call against production, same as local dev — no scheduled Cloud Run Job exists yet to automate daily rotation (named as a "later" item in `docs/scalability.md`).
- Rotating `firebase-hosting-deployer`'s key or any Secret Manager value is a manual operation, not automated.
