from datetime import UTC, datetime, timedelta

from app.domain.entities.hint_request import HintRequest
from app.infrastructure.firestore.hint_request_mapper import (
    document_to_hint_request,
    hint_request_to_document,
)


def test_round_trip_preserves_all_fields():
    hint_request = HintRequest(
        hint_request_id="hint-1",
        case_id="case_museum_001",
        player_id="player-1",
        level=2,
        text="Look closer at the wristband.",
        grounded_in_clue_ids=("clue_1",),
        passed_guardrails=True,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )

    document = hint_request_to_document(hint_request)
    restored = document_to_hint_request(hint_request.hint_request_id, document)

    assert restored == hint_request


def test_document_uses_camel_case_field_names():
    hint_request = HintRequest(hint_request_id="hint-1", case_id="c", player_id="p", level=1, text="t")

    document = hint_request_to_document(hint_request)

    assert set(document.keys()) == {
        "playerId",
        "caseId",
        "hintLevel",
        "hintText",
        "groundedInClueIds",
        "passedGuardrails",
        "createdAt",
        "expireAt",
    }


def test_expire_at_is_180_days_after_created_at():
    created_at = datetime(2026, 1, 1, tzinfo=UTC)
    hint_request = HintRequest(
        hint_request_id="hint-1", case_id="c", player_id="p", level=1, text="t", created_at=created_at
    )

    document = hint_request_to_document(hint_request)

    assert document["expireAt"] == created_at + timedelta(days=180)
