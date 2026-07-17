from datetime import datetime, timezone

from app.domain.entities.attempt import Attempt
from app.infrastructure.firestore.firestore_attempt_repository import FirestoreAttemptRepository

from .conftest import requires_firestore_emulator


@requires_firestore_emulator
def test_record_persists_full_attempt(firestore_client):
    repo = FirestoreAttemptRepository(client=firestore_client)

    repo.record(
        Attempt(
            attempt_id="attempt-1",
            player_id="player-1",
            case_id="case_museum_001",
            selected_suspect_id="suspect_3",
            correct=True,
            score=100,
            hints_used=0,
            created_at=datetime.now(timezone.utc),
        )
    )

    raw = firestore_client.collection("case_attempts").document("attempt-1").get().to_dict()
    assert raw["playerId"] == "player-1"
    assert raw["caseId"] == "case_museum_001"
    assert raw["selectedSuspectId"] == "suspect_3"
    assert raw["correct"] is True
    assert raw["score"] == 100
    assert raw["hintsUsed"] == 0
