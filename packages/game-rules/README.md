# Game Rules

Shared, framework-independent game-rule logic that both `apps/game` and `services/api` may need to agree on (e.g. difficulty definitions, scoring constants), kept as a single source of truth instead of duplicated.

Populated as domain rules stabilize during Phase 2 (Core Domain Rules) — only if actual duplication between frontend and backend shows up. Not created preemptively.
