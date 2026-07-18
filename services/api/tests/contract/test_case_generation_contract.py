import json

from app.api import dependencies
from app.infrastructure.repositories.in_memory_generation_quota_repository import (
    InMemoryDailyGenerationQuotaRepository,
)
from app.main import app
from tests.fakes import AttemptScript, FakeCaseGenerationAdapter


def _parse_sse_events(body: str) -> list[dict]:
    events = []
    for line in body.splitlines():
        if line.startswith("data: "):
            events.append(json.loads(line[len("data: ") :]))
    return events


def test_successful_generation_returns_saved_case(client):
    response = client.post("/cases/generate")

    assert response.status_code == 200
    events = _parse_sse_events(response.text)
    assert [e["step"] for e in events] == [
        "generating",
        "generating",
        "logic_check",
        "logic_check",
        "safety_check",
        "safety_check",
        "saving",
        "saving",
    ]
    final = events[-1]
    assert final["status"] == "done"
    assert final["case"]["source"] == "live_generated"


def test_global_quota_exhausted_returns_429_without_opening_a_stream(client):
    """Pre-fills the quota to its cap via dependency override, rather than
    making 50 real HTTP round-trips (which would also collide with the
    per-IP rate limit) -- two requests are enough to observe the real
    pre-check short-circuit."""
    quota = InMemoryDailyGenerationQuotaRepository(success_cap=1, attempt_cap=300)
    app.dependency_overrides[dependencies.get_generation_quota_repository] = lambda: quota

    first = client.post("/cases/generate")
    assert first.status_code == 200
    assert "saving" in first.text

    second = client.post("/cases/generate")
    assert second.status_code == 429
    assert second.json()["detail"] == "daily generation quota reached"


def test_per_ip_rate_limit_returns_429_before_quota_is_consulted(client):
    for _ in range(3):
        response = client.post("/cases/generate")
        assert response.status_code == 200

    fourth = client.post("/cases/generate")
    assert fourth.status_code == 429


def test_rejection_then_success_shows_a_visible_restart(client):
    adapter = FakeCaseGenerationAdapter(
        [AttemptScript(logic_passes=False), AttemptScript(logic_passes=True)]
    )
    app.dependency_overrides[dependencies.get_case_generation_adapter] = lambda: adapter

    response = client.post("/cases/generate")

    assert response.status_code == 200
    events = _parse_sse_events(response.text)
    steps_statuses = [(e["step"], e["status"], e.get("attempt")) for e in events]
    assert ("logic_check", "rejected", 1) in steps_statuses
    # The restart: a fresh "generating: running" for attempt 2, not a
    # synthetic/time-based placeholder.
    assert ("generating", "running", 2) in steps_statuses
    assert events[-1]["status"] == "done"


def test_pipeline_exhaustion_reports_a_clean_failed_event_not_a_hang(client):
    adapter = FakeCaseGenerationAdapter([AttemptScript(logic_passes=False)])
    app.dependency_overrides[dependencies.get_case_generation_adapter] = lambda: adapter

    response = client.post("/cases/generate")

    assert response.status_code == 200
    events = _parse_sse_events(response.text)
    assert events[-1]["step"] == "failed"
    assert events[-1]["status"] == "done"
    assert "10 attempts" in events[-1]["detail"]
