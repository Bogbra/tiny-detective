from app.domain.entities.hint_request import HintRequest
from app.domain.value_objects.case_id import CaseId


class InMemoryHintRequestRepository:
    """Process-local hint-request store. Used when Firestore isn't configured."""

    def __init__(self) -> None:
        self._records: list[HintRequest] = []

    def count_for_case(self, case_id: CaseId, player_id: str) -> int:
        return sum(1 for r in self._records if r.case_id == case_id.value and r.player_id == player_id)

    def record(self, hint_request: HintRequest) -> None:
        self._records.append(hint_request)
