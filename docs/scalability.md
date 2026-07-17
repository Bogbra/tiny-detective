# Scalability Notes

## Verification Scope

Everything below was verified against the **Firestore emulator** (Docker, `gcr.io/google.com/cloudsdktool/cloud-sdk:emulators`), not a real Firestore project — no real GCP project was available in this environment. This matters for two specific reasons, not just as a general caveat:

- **The emulator does not enforce composite indexes.** A query that needs a composite index runs fine locally and can fail against real Firestore with a `FAILED_PRECONDITION` until the matching index is created. None of the current queries (all single-field, e.g. "cases where status == approved") need one, but that's a property of today's query shapes, not something the emulator actually checked.
- **The emulator does not enforce Security Rules.** Locally, every read/write the backend issues succeeds regardless of what `firestore.rules` says (there is no deployed rules file yet — the backend's own `ADMIN_API_TOKEN` check is the only access control that actually runs today). Rules-based access control would need its own verification against a real project or the emulator's rules-testing mode, neither of which has happened.

Correct summary: **locally verified, index/rules behavior unverified.** Nothing here should be read as "production-ready at scale" — it's "the data model and query patterns are reasoned through and cheap to run against; the parts only a real project enforces haven't been exercised."

## Data Model Choices Made for Read Efficiency

- **`daily_cases/{yyyy-mm-dd}` is a separate, date-keyed collection** rather than a query like "cases where publishedDate == today" against the larger `cases` collection. `GET /cases/daily` is a single document read by a known key, not a query — cheapest possible read shape, and immune to the composite-index question above since it's not a query at all.
- **Public case responses never include `isCulprit`/`privateReasoning`/the solution** (enforced at the API-response-mapping layer, not by separate documents) — keeps the hot path (a player loading a case) to one document read rather than joining across a "public case" and "private solution" collection.
- **Hint requests and attempts are separate collections keyed by their own IDs** (`hint_requests/{hintRequestId}`, `case_attempts/{attemptId}`), not subcollections nested under `players/{playerId}` — avoids Firestore's subcollection fan-out cost when e.g. an admin view needs "all attempts for a case" rather than "all attempts by a player."

## Known Limitations (Deferred, Not Solved)

- **Repository singletons are lazily constructed and cached per-process (`@lru_cache` in `app/api/dependencies.py`)** — one Firestore client per running backend process, not per-request. This is standard for a stateless Cloud Run-style deployment (the client is safe to reuse across requests, and Cloud Run itself handles horizontal scaling by running more instances, each with its own cached client) but hasn't been load-tested. See [ADR-0005](architecture-decisions/ADR-0005-firestore-data-model.md)'s addendum for why this used to be an eager module-level singleton and was changed.
- **No caching layer in front of Firestore** (e.g. Redis for `GET /cases/daily`, which is read far more often than it changes). Not needed at MVP traffic; would be the first thing to add if this were seeing real load.
- **No rate-limiting on hint requests beyond the per-case hint-count limit already enforced in the domain layer.** Controls repeated-request cost within a single playthrough, not request-rate abuse across playthroughs.
- **AI cost control is scope-limited, not spend-limited** — the hint assistant makes at most one OpenAI call per hint request (itself capped by the domain-level hint limit), and case generation is an offline/admin-triggered batch process, not player-triggered. There's no budget cap or circuit breaker if either were to run away; acceptable for an MVP with no real traffic, not something to carry into a real deployment unexamined.
- **No BigQuery/analytics pipeline** — not needed until there's usage data worth aggregating beyond what Firestore itself can answer directly.
