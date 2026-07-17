"""Pure Attempt <-> Firestore document mapping. Field names match the project spec's
`case_attempts/{attemptId}` schema.
"""

from app.domain.entities.attempt import Attempt


def attempt_to_document(attempt: Attempt) -> dict:
    return {
        "playerId": attempt.player_id,
        "caseId": attempt.case_id,
        "selectedSuspectId": attempt.selected_suspect_id,
        "correct": attempt.correct,
        "score": attempt.score,
        "hintsUsed": attempt.hints_used,
        "createdAt": attempt.created_at,
    }


def document_to_attempt(attempt_id: str, data: dict) -> Attempt:
    return Attempt(
        attempt_id=attempt_id,
        player_id=data["playerId"],
        case_id=data["caseId"],
        selected_suspect_id=data["selectedSuspectId"],
        correct=data["correct"],
        score=data["score"],
        hints_used=data["hintsUsed"],
        created_at=data.get("createdAt"),
    )
