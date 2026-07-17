# ADR-0001: Monorepo Layout

## Status

Accepted

## Context

The project has a Flutter app, a FastAPI backend, offline AI content tooling, and shared contracts. These pieces are developed and versioned together for the lifetime of this portfolio project, and changes frequently span more than one of them (e.g. an API contract change touches both `services/api` and `apps/game`).

## Decision

Use a single repository with `apps/`, `services/`, `tools/`, `packages/`, and `docs/` at the top level, as defined in the project spec's "Non-Negotiable Architecture Rules". Each app/service/tool keeps its own dependency manifest (`pubspec.yaml`, `pyproject.toml`) and is independently buildable; CI (`.github/workflows/ci.yml`) runs each one's checks in its own job.

## Consequences

- One place to review cross-cutting changes (e.g. API contract + frontend DTO in the same PR).
- No cross-repo dependency version drift to manage.
- CI must be scoped per-directory so an unrelated change doesn't block on unrelated checks — acceptable at this project's size; would need path filtering or a build-graph tool (e.g. Nx, Turborepo/Melos) if the repo grew significantly.
- Deployment remains per-service (Firebase Hosting for the app, Cloud Run for the API), not monolithic — the monorepo is a source-control choice, not a deployment one.
