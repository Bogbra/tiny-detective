from datetime import datetime, timezone

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
    }
