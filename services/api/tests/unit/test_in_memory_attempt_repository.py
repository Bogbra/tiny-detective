from datetime import datetime, timezone

from app.domain.entities.attempt import Attempt
from app.infrastructure.repositories.in_memory_attempt_repository import InMemoryAttemptRepository


def _attempt(player_id="player-1", case_id="case_museum_001", **overrides) -> Attempt:
    defaults = dict(
        attempt_id="attempt-1",
        player_id=player_id,
        case_id=case_id,
        selected_suspect_id="suspect_3",
        correct=True,
        score=100,
        hints_used=0,
        created_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return Attempt(**defaults)


def test_exists_for_is_false_before_any_attempt():
    repo = InMemoryAttemptRepository()
    assert repo.exists_for("player-1", "case_museum_001") is False


def test_exists_for_is_true_after_recording_an_attempt():
    repo = InMemoryAttemptRepository()
    repo.record(_attempt())
    assert repo.exists_for("player-1", "case_museum_001") is True


def test_exists_for_is_true_even_after_an_incorrect_attempt():
    # Existence, not correctness — a wrong first guess still spends the
    # player's one scored shot.
    repo = InMemoryAttemptRepository()
    repo.record(_attempt(correct=False, selected_suspect_id="suspect_1"))
    assert repo.exists_for("player-1", "case_museum_001") is True


def test_exists_for_is_scoped_to_the_specific_player_and_case():
    repo = InMemoryAttemptRepository()
    repo.record(_attempt(player_id="player-1", case_id="case_museum_001"))

    assert repo.exists_for("player-2", "case_museum_001") is False
    assert repo.exists_for("player-1", "case_other") is False
