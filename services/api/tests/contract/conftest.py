import pytest
from fastapi.testclient import TestClient

from app.api import dependencies
from app.infrastructure.repositories.in_memory_attempt_repository import InMemoryAttemptRepository
from app.infrastructure.repositories.in_memory_case_repository import InMemoryCaseRepository
from app.infrastructure.repositories.in_memory_hint_request_repository import (
    InMemoryHintRequestRepository,
)
from app.infrastructure.repositories.in_memory_player_repository import InMemoryPlayerRepository
from app.infrastructure.seed_data import seed_cases
from app.main import app
from tests.fakes import FakeHintAssistant


@pytest.fixture(autouse=True)
def _isolated_repositories():
    """Resets in-memory repository state before every test in this package.

    The app's real dependency providers (app/api/dependencies.py) are
    process-wide singletons — state persists across requests while a server
    runs. autouse=True makes isolation the default for every contract test,
    not something a test author has to remember to opt into by using the
    `client` fixture specifically; a test that builds its own TestClient(app)
    still gets isolated repositories.

    Also overrides the hint assistant with a fake that always returns None
    (triggering the deterministic fallback) — contract tests must never call
    the real OpenAI API, regardless of whether a real OPENAI_API_KEY happens
    to be present in the environment running them. Test cost and behavior
    must not depend on that; test_request_hint_use_case.py in tests/unit/
    is where the AI-hint-specific behavior (grounding, guardrails) is
    actually exercised, with a controllable fake.
    """
    case_repository = InMemoryCaseRepository(initial_cases=seed_cases())
    player_repository = InMemoryPlayerRepository()
    hint_request_repository = InMemoryHintRequestRepository()
    attempt_repository = InMemoryAttemptRepository()
    hint_assistant = FakeHintAssistant(None)

    app.dependency_overrides[dependencies.get_case_repository] = lambda: case_repository
    app.dependency_overrides[dependencies.get_player_repository] = lambda: player_repository
    app.dependency_overrides[dependencies.get_hint_request_repository] = (
        lambda: hint_request_repository
    )
    app.dependency_overrides[dependencies.get_attempt_repository] = lambda: attempt_repository
    app.dependency_overrides[dependencies.get_hint_assistant] = lambda: hint_assistant

    yield

    app.dependency_overrides.clear()


@pytest.fixture
def client(_isolated_repositories: None):
    with TestClient(app) as test_client:
        yield test_client
