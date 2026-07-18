from datetime import UTC, datetime

from app.domain.entities.hint_request import HintRequest
from app.domain.value_objects.case_id import CaseId
from app.infrastructure.firestore.firestore_hint_request_repository import (
    FirestoreHintRequestRepository,
)

from .conftest import requires_firestore_emulator


def _hint_request(**overrides) -> HintRequest:
    defaults = dict(
        hint_request_id="hint-1",
        case_id="case_museum_001",
        player_id="player-1",
        level=1,
        text="Look closer.",
        grounded_in_clue_ids=("clue_1",),
        passed_guardrails=True,
        created_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    return HintRequest(**defaults)


@requires_firestore_emulator
def test_record_and_count_for_case(firestore_client):
    repo = FirestoreHintRequestRepository(client=firestore_client)
    case_id = CaseId("case_museum_001")

    assert repo.count_for_case(case_id, "player-1") == 0

    repo.record(_hint_request())

    assert repo.count_for_case(case_id, "player-1") == 1


@requires_firestore_emulator
def test_count_is_scoped_per_player(firestore_client):
    repo = FirestoreHintRequestRepository(client=firestore_client)
    case_id = CaseId("case_museum_001")

    repo.record(_hint_request(hint_request_id="h1", player_id="player-1"))
    repo.record(_hint_request(hint_request_id="h2", player_id="player-2"))

    assert repo.count_for_case(case_id, "player-1") == 1
    assert repo.count_for_case(case_id, "player-2") == 1


@requires_firestore_emulator
def test_full_record_is_persisted(firestore_client):
    """Hint request persistence — verifies the FULL record (level, text,
    grounded clue ids, guardrail outcome), not just a bare counter, matching
    the project spec's hint_requests schema."""
    repo = FirestoreHintRequestRepository(client=firestore_client)

    repo.record(
        _hint_request(
            hint_request_id="hint-full",
            level=2,
            text="Look at the wristband.",
            grounded_in_clue_ids=("clue_1",),
            passed_guardrails=True,
        )
    )

    raw = firestore_client.collection("hint_requests").document("hint-full").get().to_dict()
    assert raw["hintLevel"] == 2
    assert raw["hintText"] == "Look at the wristband."
    assert raw["groundedInClueIds"] == ["clue_1"]
    assert raw["passedGuardrails"] is True
