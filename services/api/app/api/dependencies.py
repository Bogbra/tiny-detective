"""Process-wide dependency providers for FastAPI's Depends().

Repositories are Firestore-backed when configured (FIRESTORE_EMULATOR_HOST or
GOOGLE_CLOUD_PROJECT set), in-memory otherwise — same graceful-degradation
pattern as OPENAI_API_KEY for the hint assistant.

Each provider is `@lru_cache`d (FastAPI's standard pattern for a
process-wide singleton dependency) rather than constructed at module-import
time: nothing that talks to a network — Firestore client, OpenAI client —
gets built until a route actually requests it via Depends(). This matters
beyond just "faster imports": a module-level `_repo = FirestoreCaseRepository()`
would attempt a real connection the moment this module is imported, which
happens transitively during pytest's *collection* phase (before any test
runs, before `is_firestore_configured()`'s pytest guard would even help) —
lazy construction removes that whole class of import-time-network-call bugs,
not just the one instance that was actually hit (a ~45s hang against a
stopped emulator — see ADR-0005's addendum). Tests override these providers
via app.dependency_overrides — which replaces the function itself, so the
cached body underneath never runs when overridden.
"""

import os
import secrets
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Header, HTTPException, status

from app.application.ports import (
    AttemptRepository,
    CaseRepository,
    HintRequestRepository,
    PlayerRepository,
)
from app.infrastructure.ai.ai_hint_assistant import OpenAIHintAssistant
from app.infrastructure.firestore.firestore_attempt_repository import FirestoreAttemptRepository
from app.infrastructure.firestore.firestore_case_repository import FirestoreCaseRepository
from app.infrastructure.firestore.firestore_client import is_firestore_configured
from app.infrastructure.firestore.firestore_hint_request_repository import (
    FirestoreHintRequestRepository,
)
from app.infrastructure.firestore.firestore_player_repository import FirestorePlayerRepository
from app.infrastructure.repositories.in_memory_attempt_repository import InMemoryAttemptRepository
from app.infrastructure.repositories.in_memory_case_repository import InMemoryCaseRepository
from app.infrastructure.repositories.in_memory_hint_request_repository import (
    InMemoryHintRequestRepository,
)
from app.infrastructure.repositories.in_memory_player_repository import InMemoryPlayerRepository
from app.infrastructure.seed_data import seed_cases

# Loads services/api/.env if present; a no-op if it doesn't exist (e.g. in
# deployment, where env vars come from the platform instead). Never commit
# the real .env — see .env.example for what it should contain.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

ADMIN_TOKEN_ENV_VAR = "ADMIN_API_TOKEN"


@lru_cache
def get_case_repository() -> CaseRepository:
    if not is_firestore_configured():
        return InMemoryCaseRepository(initial_cases=seed_cases())

    repository = FirestoreCaseRepository()
    if not repository.list_all():
        # Empty Firestore (e.g. a freshly started emulator) — seed the same
        # two demo cases the in-memory repository ships with, so local dev
        # against the emulator has something to play immediately.
        for case in seed_cases():
            repository.save(case)
    return repository


@lru_cache
def get_player_repository() -> PlayerRepository:
    if is_firestore_configured():
        return FirestorePlayerRepository()
    return InMemoryPlayerRepository()


@lru_cache
def get_hint_request_repository() -> HintRequestRepository:
    if is_firestore_configured():
        return FirestoreHintRequestRepository()
    return InMemoryHintRequestRepository()


@lru_cache
def get_attempt_repository() -> AttemptRepository:
    if is_firestore_configured():
        return FirestoreAttemptRepository()
    return InMemoryAttemptRepository()


@lru_cache
def get_hint_assistant() -> OpenAIHintAssistant:
    # Safe to construct without OPENAI_API_KEY set even though this is no
    # longer eager either — the key is read lazily, per request, inside
    # generate_hint(). See ai_hint_assistant.py.
    return OpenAIHintAssistant()


def require_admin(x_admin_token: str = Header(default="")) -> None:
    """Protects admin routes with a shared-secret header.

    Disabled by default: if ADMIN_API_TOKEN isn't set, every admin request is
    rejected regardless of the header sent. This is a deliberately minimal
    MVP mechanism — real auth is out of scope until it's actually needed.

    Comparison uses secrets.compare_digest to avoid a timing side-channel on
    the token. Never log x_admin_token or the expected token value.
    """
    expected = os.environ.get(ADMIN_TOKEN_ENV_VAR)
    if not expected or not secrets.compare_digest(x_admin_token, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="admin authentication required"
        )
