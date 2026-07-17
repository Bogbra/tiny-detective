# ADR-0002: Clean Architecture (Layered Domain/Application/Infrastructure)

## Status

Accepted

## Context

The project spec requires that game rules (scoring, hint limits, solution validation, publish eligibility) be testable without Flutter, FastAPI, Firestore, or AI APIs, and that AI-generated content never bypass evaluation before reaching players. This is also a portfolio project: a reviewer should be able to see clear separation of concerns at a glance.

## Decision

Both `apps/game` and `services/api` follow a layered architecture:

- **domain** — entities, value objects, policies. Pure, framework-independent, no imports from UI/HTTP/Firestore/AI SDKs.
- **application** — use cases that orchestrate domain policies and infrastructure through interfaces.
- **infrastructure** (backend) / **data** (frontend) — concrete implementations (Firestore repositories, AI SDK adapters, API clients), behind interfaces the application layer depends on.
- **presentation** (frontend) / **api** (backend) — the outermost layer; thin, no business logic.

## Consequences

- Domain logic (e.g. `ScoringPolicy`, `HintPolicy`) can be unit-tested in isolation, without spinning up FastAPI or Firestore.
- Swapping infrastructure (e.g. a different AI provider, or an in-memory repository for tests) doesn't touch domain or application code.
- More files/indirection than a flat structure — accepted because the project explicitly wants to demonstrate this discipline, and the domain (detective cases, scoring, hints, AI guardrails) is complex enough to benefit from it.
- This layering is introduced feature-by-feature starting in Phase 2 (Core Domain Rules) and Phase 3 (Backend API) — Phase 1 only scaffolds the top-level `apps/`/`services/`/`tools/`/`packages/` separation, not the full per-feature layer trees, to avoid empty directories with no content.
