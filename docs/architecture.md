# Architecture

## App / Service / Tool Separation

```text
apps/       user-facing applications      apps/game (Flutter)
services/   deployed runtime services      services/api (FastAPI)
tools/      local/admin/offline tools      tools/ai-content
packages/   shared reusable libraries      packages/contracts, packages/game-rules
docs/       documentation and ADRs
```

The Flutter app never calls AI provider APIs or Firestore directly. It talks to `services/api` over HTTPS only.

## Dependency Rules

- `apps/game` UI (presentation) depends on application → domain → data, never the other way around.
- `services/api` follows `api → application → domain`, with `infrastructure` implementing interfaces the application layer depends on. `domain` imports nothing from FastAPI, Firestore, or AI SDKs.
- Neither app is allowed to import from the other's internals; anything shared crosses through `packages/contracts`.

## Backend Layering

```text
api/            FastAPI routes, HTTP parsing/response mapping, thin
application/    use cases, orchestration
domain/         entities, value objects, policies — framework-independent
infrastructure/ Firestore, AI SDKs, logging, config — implements interfaces
```

## Frontend Layering

Each feature (added from Phase 2 onward) follows:

```text
presentation/  screens, widgets, navigation
application/   use cases, state orchestration
domain/        feature entities, value objects, local policies
data/          DTOs, API clients, repository implementations
```

`core/` and `shared/` (scaffolded in Phase 1) hold cross-cutting concerns — app config, routing, theming, error handling, telemetry, and reusable design-system widgets — used by every feature.

## API Flow

```text
Flutter app --HTTPS--> FastAPI (api/) --> application use case --> domain policy
                                              |
                                              v
                                        infrastructure (Firestore / AI SDKs)
```

Public endpoints never return `isCulprit`, `privateReasoning`, or the solution. See the project spec's "Public Case Response Example" for the exact contract.

## AI Case Generation Pipeline

```text
generation -> schema validation -> rule-based validation -> logic consistency
  -> safety evaluation -> difficulty evaluation -> draft storage -> approval -> publishing
```

Implemented in Phase 5. No raw AI-generated case reaches players without passing every stage.

## AI Hint Assistant Flow

```text
Player requests hint -> backend loads approved case -> checks hint limit
  -> sends only public case facts to AI -> AI generates hint
  -> backend evaluates hint against guardrails -> safe hint or deterministic fallback
```

Implemented in Phase 6. The assistant is grounded in approved case data only; it must never reveal the culprit or invent facts.

## Persistence

Implemented in Phase 7. `CaseRepository`/`PlayerRepository`/`HintRequestRepository`/`AttemptRepository` (`app/application/ports.py`) are Firestore-backed (`app/infrastructure/firestore/`) when `FIRESTORE_EMULATOR_HOST` or `GOOGLE_CLOUD_PROJECT` is set, in-memory otherwise — no use case or route needed to change for the swap. Collections: `cases/{caseId}`, `daily_cases/{yyyy-mm-dd}`, `players/{playerId}`, `hint_requests/{hintRequestId}`, `case_attempts/{attemptId}`, per the project spec's Firestore Data Model. Each entity's Firestore document mapping is a pure function (`*_mapper.py`, no network call) tested independently of the actual database calls. See [ADR-0005](architecture-decisions/ADR-0005-firestore-data-model.md).

## Deployment Topology

```text
Firebase Hosting  -> Flutter Web App (apps/game)
Cloud Run         -> FastAPI Backend (services/api)
Firestore         -> cases, players, attempts, hints
GitHub Actions    -> CI/CD (.github/workflows/ci.yml)
```

Locally: a Firestore emulator (Docker) stands in for real Firestore — see `README.md`'s backend setup section.

Optional later: Cloud Scheduler → Cloud Run Job for generating/evaluating new cases.

## Scalability Notes

See `docs/scalability.md`.
