from app.domain.entities.detective_case import DetectiveCase
from app.domain.value_objects.case_id import CaseId


class InMemoryCaseRepository:
    """Process-local case store. Replaced by a Firestore-backed repository in Phase 7."""

    def __init__(self, initial_cases: list[DetectiveCase] | None = None) -> None:
        self._cases: dict[str, DetectiveCase] = {case.case_id.value: case for case in (initial_cases or [])}
        self._daily_case_id: str | None = None

    def get(self, case_id: CaseId) -> DetectiveCase | None:
        return self._cases.get(case_id.value)

    def get_daily(self) -> DetectiveCase | None:
        if self._daily_case_id is None:
            return None
        return self._cases.get(self._daily_case_id)

    def set_daily(self, case_id: CaseId) -> None:
        self._daily_case_id = case_id.value

    def save(self, case: DetectiveCase) -> None:
        self._cases[case.case_id.value] = case

    def list_all(self) -> list[DetectiveCase]:
        return list(self._cases.values())
