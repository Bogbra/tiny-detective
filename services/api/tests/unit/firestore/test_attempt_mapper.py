from datetime import datetime, timedelta, timezone

from app.domain.entities.attempt import Attempt
from app.infrastructure.firestore.attempt_mapper import attempt_to_document, document_to_attempt


def test_round_trip_preserves_all_fields():
    attempt = Attempt(
        attempt_id="attempt-1",
        player_id="player-1",
        case_id="case_museum_001",
        selected_suspect_id="suspect_3",
        correct=True,
        score=85,
        hints_used=1,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    document = attempt_to_document(attempt)
    restored = document_to_attempt(attempt.attempt_id, document)

    assert restored == attempt


def test_document_uses_camel_case_field_names():
    attempt = Attempt(
        attempt_id="a",
        player_id="p",
        case_id="c",
        selected_suspect_id="s",
        correct=False,
        score=0,
        hints_used=0,
    )

    document = attempt_to_document(attempt)

    assert set(document.keys()) == {
        "playerId",
        "caseId",
        "selectedSuspectId",
        "correct",
        "score",
        "hintsUsed",
        "createdAt",
        "expireAt",
    }


def test_expire_at_is_180_days_after_created_at():
    created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    attempt = Attempt(
        attempt_id="a",
        player_id="p",
        case_id="c",
        selected_suspect_id="s",
        correct=True,
        score=100,
        hints_used=0,
        created_at=created_at,
    )

    document = attempt_to_document(attempt)

    assert document["expireAt"] == created_at + timedelta(days=180)


def test_expire_at_is_none_when_created_at_is_none():
    attempt = Attempt(
        attempt_id="a",
        player_id="p",
        case_id="c",
        selected_suspect_id="s",
        correct=True,
        score=100,
        hints_used=0,
        created_at=None,
    )

    document = attempt_to_document(attempt)

    assert document["expireAt"] is None
