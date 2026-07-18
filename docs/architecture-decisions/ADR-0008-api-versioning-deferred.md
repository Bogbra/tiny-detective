# ADR-0008: API Versioning — Deliberately Deferred

## Status

Accepted

## Context

A security/ops audit flagged that the public API (`GET /cases/daily`, `POST /cases/{id}/solution`, `POST /cases/{id}/hint`, `POST /cases/generate`, `POST /players`, etc.) has no version prefix — every route hangs directly off the root, e.g. `/cases/daily` rather than `/v1/cases/daily`. The audit asked for an explicit decision: either add `/v1` now (with the corresponding Flutter client and contract-test updates) or record why versioning is deliberately deferred and what the real migration path would be, rather than leaving the question unaddressed.

## Decision

**Deferred, not adopted — no `/v1` prefix added.**

The real reason versioning exists at all is to let a breaking API change ship without instantly breaking every existing client that hasn't upgraded yet — that problem only exists once there's more than one client, or clients that can't all be redeployed in lockstep with the backend. Neither is true here: `apps/game` is the *only* consumer of this API, and `deploy.yml`'s own topology (`deploy-web` declaring `needs: deploy-api`, both built from the same commit, the frontend build baking in `API_BASE_URL` from that same deploy's Cloud Run URL) means backend and frontend are deployed together, from the same source, every time. There is no version skew window for `/v1` to protect against yet — adding the prefix now would be paying a real mechanical cost (every route file, every Flutter API client's base-path construction, every one of the ~30+ contract tests referencing a URL string) for a guarantee this project's actual deployment model already provides for free.

This is the same "appropriate efficiency for the current product stage" principle applied elsewhere in this project (no staging environment yet either — see ADR-0006's amendment; no shared distributed rate-limiter — see ADR-0006's amendment) — premature versioning infrastructure isn't free, and the thing it protects against isn't a live risk yet.

## Migration Path (when this actually becomes needed)

The trigger condition, stated concretely so this isn't an open-ended deferral: **the day a second real consumer of this API exists** — a native mobile client that can't be forced to redeploy in lockstep with the backend, a public/partner integration, or a deliberate multi-environment setup where an older frontend build might still be live against a newer backend (e.g. a slow-rolling Firebase Hosting release next to an already-updated Cloud Run revision).

At that point:

1. Add an `APIRouter(prefix="/v1")` wrapping the existing routers in `app/main.py` — a small, mechanical, low-risk change given FastAPI's router composition (no change to any route handler, contract model, or business logic).
2. Keep the *unversioned* routes mounted too, for one deprecation window, returning the same responses — so the transition itself doesn't have a hard cutover.
3. Update `apps/game`'s API clients (`case_api_client.dart`, `case_generation_api_client.dart`, hint/solution calls) to target `/v1/...`, and update this project's contract tests to match — the same set of files the audit named, done at the point versioning actually matters rather than speculatively now.
4. Announce and later remove the unversioned routes once nothing is calling them (checkable via the structured access logs from task 11 — `logging_middleware` already logs every request path, so "is anything still hitting the unversioned routes" is a real, answerable question by then, not a guess).

## Consequences

- No `/v1` prefix exists today; this is a known, deliberate gap, not an oversight — referenced from here if it comes up again rather than re-litigated.
- The migration path above is real and specific enough to execute without re-deriving the design from scratch when the trigger condition is actually met.
- If a second consumer or environment need shows up sooner than expected, this ADR is the place to revisit — update it in place with an addendum (this project's established pattern, see ADR-0006 and ADR-0007's addenda) rather than silently reversing the decision elsewhere.
