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

`POST /cases/generate` runs a real AI pipeline live, on a player's click, and streams real progress via SSE. The generation step is a **hybrid deterministic-logic + LLM-prose-rendering pipeline**, not a single LLM call: who's guilty, which evidence identifies them, and each suspect's alibi are decided by a Python constraint solver (`tools/ai-content/ai_content/logic_builder.py`) and verified correct *before* any LLM call happens; the LLM (`CaseProseRenderer`) is then constrained to writing prose around that fixed structure, never asked to invent or verify the deduction itself. A narrower AI judge and a deterministic fidelity check (verbatim-phrase matching) confirm the rendered prose didn't drift from the given facts; only the safety judge does the same broad, open-ended check it always did. Full design and the four real bugs found getting there: [ADR-0007](architecture-decisions/ADR-0007-live-case-generation.md)'s redesign addendum.

Bounded by two independent, atomic, Firestore-backed daily counters (a 50/day success cap and a 2000/day attempt cap that also counts judge-rejected attempts — cost isn't bounded by successes alone) plus a 3/minute per-IP limit, and up to 5 retries per request (lowered from 10 once the real pass rate made a smaller budget sufficient — see below). Every result is stored with `source="live_generated"`, distinguishing it from curated content; the actual daily case is never touched by this feature.

**The original single-shot LLM pipeline's real production pass rate was ~5-10% per attempt** (investigated by inspecting real rejected candidates directly — a genuine generator quality issue, not judge over-strictness) — assessed as a show-stopper (most players would see failure after a ~30s wait) rather than something to paper over with a bigger retry budget. A controlled test swapping only the generator model to gpt-4o (judges unchanged) landed at the same ~5% rate, cleanly falsifying "a stronger model fixes this" and pointing at a task-design flaw instead: the model was asked to invent a puzzle and verify its own deduction in the same generative pass, with no structural mechanism forcing that check to be real.

**The redesign fixes the root cause: real measured pass rate 32.5% (13/40 across two independent 20-call batches against the real API)** — roughly 6.5x the old rate, at essentially unchanged per-attempt cost (~$0.0007-0.0015/attempt, gpt-4o-mini throughout). At this rate, 5 attempts already clears ~86% eventual success with a much tighter worst-case wait than the old 10-attempt budget needed.

## Startup Guard: Fail Fast on Misconfigured Persistence

`REQUIRE_PERSISTENT_STORAGE=true` is set only in the Cloud Run deploy (`deploy.yml`). At app startup, `app/main.py` checks this against `is_firestore_configured()` and raises immediately if it's true but Firestore isn't actually configured — e.g. a future deploy that forgets to set `GOOGLE_CLOUD_PROJECT`. Without this, that mistake would be silent: the app starts fine on the in-memory fallback, `/health` returns `200` (it doesn't touch storage), and the deploy job's smoke test — the one thing that was supposed to catch a broken deploy — would report success on a backend quietly forgetting every player, hint, and attempt on its next cold start. With the guard, the container fails to start, Cloud Run never reports it healthy, and the smoke test's `curl` gets a connection failure instead of a false positive. No-op locally and under pytest (the env var is never set there), so local dev and the test suite are unaffected.

## Security Headers (Firebase Hosting)

`firebase.json`'s `hosting.headers` applies to every response: HSTS (`max-age=31536000; includeSubDomains`), `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, a `Permissions-Policy` disabling camera/microphone/geolocation (unused by this app), and a `Content-Security-Policy` tuned for Flutter web specifically:

- `script-src 'self' 'wasm-unsafe-eval' https://www.gstatic.com` — the CanvasKit renderer compiles WebAssembly at runtime (needs `'wasm-unsafe-eval'`) and, in this Flutter version, is loaded from Google's CDN (`gstatic.com`) rather than bundled into `build/web/` — see the note below on how that was actually discovered.
- `style-src 'self' 'unsafe-inline'` — Flutter's web shell injects `<style>` tags at runtime for font/text rendering; a stricter policy here blocked rendering.
- `connect-src 'self' https://tiny-detective-api-n7fn34d2jq-ew.a.run.app https://www.gstatic.com https://fonts.gstatic.com` — the real API origin, plus CanvasKit's own runtime `fetch()` of `canvaskit.wasm` from `gstatic.com`, plus Roboto webfont files fetched from `fonts.gstatic.com` (Flutter's default font, also not self-hosted in this build). All three found by watching real `securitypolicyviolation` events fire in an actual browser, not guessed.
- `font-src 'self' data: https://fonts.gstatic.com` — same Google Fonts origin.
- `img-src` allows `data:` for inline/data-URI assets; everything else defaults to `'self'`; `object-src 'none'` and `frame-ancestors 'self'` are hardening with no functional cost.

**A first version of this CSP shipped without the `gstatic.com` origins and broke the live site completely** — a blank page, `main.dart.js` throwing `Failed to fetch dynamically imported module` for `canvaskit.js`, caught by an actual headless-browser check against the live production URL (Playwright, listening for real `securitypolicyviolation` DOM events and console errors) run *after* the first deploy, not assumed safe because the deploy itself succeeded and the HTTP status was 200. The initial assumption — that CanvasKit was bundled locally into `build/web/canvaskit/` because `web/index.html`'s source template has no explicit CDN reference — was wrong: the actual asset loading is decided by Flutter's build tooling / `flutter_bootstrap.js` (generated at build time, not present in source), and in this Flutter version defaults to `gstatic.com`. Fixed by widening `script-src`/`connect-src`/`font-src` to the three real origins observed, then re-deploying and re-running the exact same live browser check: zero CSP violations, zero console errors, and (confirmed with an actual screenshot, since CanvasKit renders to `<canvas>` with no accessible DOM text to assert on) the real daily case — title, setting, clues, suspects, both buttons — rendering correctly before calling this task done.

## Secrets and IAM

- `ADMIN_API_TOKEN` and `OPENAI_API_KEY` live in Secret Manager, injected into Cloud Run via `--set-secrets` (never as plain env vars, never printed during setup).
- `github-actions-deployer` (deploy-time identity, WIF, no stored key) and `tiny-detective-api-runtime` (what Cloud Run actually runs as) are separate service accounts with separate, minimal roles — deploy-time permissions and runtime permissions are not the same blast radius.
- `firebase-hosting-deployer` is the one service account with a stored JSON key (as the `FIREBASE_SERVICE_ACCOUNT` GitHub secret) — scoped to `roles/firebasehosting.admin` only, nothing else.
- **`--set-secrets` references `:latest`, not a pinned numeric version — a deliberate choice, not an oversight.** Pinning would mean tracking each secret's current version number as a GitHub repo variable and updating it by hand on every rotation (a real, separate manual step from rotating the secret itself, on top of the already-manual `gcloud secrets versions add` step from the rotation procedure below) — real operational overhead this two-secret, infrequently-rotated demo doesn't get much from: a version pin protects against a *rotation landing mid-deploy in a way that breaks a specific release*, and at this project's real rotation cadence (manual, rare, and never done concurrently with a deploy) that risk is negligible next to the cost of a second thing to keep in sync. Revisit if rotation ever becomes automated/frequent enough for the two to actually race.
  - **Rotation procedure**: `gcloud secrets versions add ADMIN_API_TOKEN --data-file=- <<< "$NEW_TOKEN"` (or `OPENAI_API_KEY`) adds a new version; Secret Manager's `latest` alias moves to it immediately. The *running* Cloud Run revision does **not** pick up the new value until its next cold start or redeploy — for `ADMIN_API_TOKEN` specifically (checked per-request against `os.environ`, read once at container start), that means a rotation isn't actually live until something restarts the container; trigger `gcloud run services update tiny-detective-api --region=... --no-traffic --tag=rotate` or just re-run the deploy workflow (`workflow_dispatch`) to force one. Never print the new value to any command output or CI log — pipe it in via stdin/a file, as above, not as a literal argument.

## Error Tracking

**Cloud Error Reporting, not Sentry — chosen deliberately, backend-only.** Cloud Run forwards Cloud Logging entries to Error Reporting automatically whenever they carry a real `severity: "ERROR"` field plus a stack trace — no separate SDK, DSN, or third-party account. `JsonFormatter` (task 11) already produces exactly that shape for anything logged with `exc_info=True`, and `app/api/logging_middleware.py` now catches every unhandled route exception, logs it that way (correlated with the request's trace id), and re-raises so the client-facing 500 is unchanged. This was the deciding factor over Sentry: zero new dependencies, zero new external accounts, and it reuses infrastructure this task's sibling (task 11) already built and verified, rather than adding a second, separate error-tracking pipeline.

**Scope, stated plainly, not glossed over: this covers the backend only.** Cloud Error Reporting has no visibility into the Flutter web app's own client-side JS/Dart errors — a runtime exception in the browser (a bad response shape, a rendering bug) is invisible to it. Sentry (with `sentry_flutter`) is the real way to close that gap and was the audit's named alternative specifically because it *can* cover both sides — not pursued here because it's a second real integration (a Sentry project, DSN management, a new pubspec dependency) that couldn't be verified end-to-end in this environment without a real Sentry account. If frontend error visibility becomes a real need, that's the concrete next step, not a redesign of this decision.

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
