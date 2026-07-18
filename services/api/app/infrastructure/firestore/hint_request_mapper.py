"""Pure HintRequest <-> Firestore document mapping. Field names match
the project spec's `hint_requests/{hintRequestId}` schema.
"""

from app.domain.entities.hint_request import HintRequest

from .ttl import ATTEMPT_AND_HINT_RETENTION, expire_at


def hint_request_to_document(hint_request: HintRequest) -> dict:
    return {
        "playerId": hint_request.player_id,
        "caseId": hint_request.case_id,
        "hintLevel": hint_request.level,
        "hintText": hint_request.text,
        "groundedInClueIds": list(hint_request.grounded_in_clue_ids),
        "passedGuardrails": hint_request.passed_guardrails,
        "createdAt": hint_request.created_at,
        # See ttl.py + docs/operations.md — inert without the matching
        # `gcloud firestore fields ttls update` policy also being applied.
        "expireAt": expire_at(hint_request.created_at, ATTEMPT_AND_HINT_RETENTION),
    }


def document_to_hint_request(hint_request_id: str, data: dict) -> HintRequest:
    return HintRequest(
        hint_request_id=hint_request_id,
        case_id=data["caseId"],
        player_id=data["playerId"],
        level=data["hintLevel"],
        text=data["hintText"],
        grounded_in_clue_ids=tuple(data.get("groundedInClueIds") or ()),
        passed_guardrails=data.get("passedGuardrails", False),
        created_at=data.get("createdAt"),
    )
