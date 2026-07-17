from dataclasses import dataclass

from app.domain.entities.detective_case import DetectiveCase
from app.domain.errors import UnknownSuspectError


def _normalize_suspect_id(suspect_id: str) -> str:
    return suspect_id.strip().lower()


@dataclass(frozen=True, slots=True)
class SolutionResult:
    correct: bool
    explanation: str


class SolutionPolicy:
    def evaluate(self, case: DetectiveCase, submitted_suspect_id: str) -> SolutionResult:
        normalized_submission = _normalize_suspect_id(submitted_suspect_id)
        known_suspect_ids = {_normalize_suspect_id(s.suspect_id) for s in case.suspects}

        if normalized_submission not in known_suspect_ids:
            raise UnknownSuspectError(
                f"'{submitted_suspect_id}' is not a suspect in case '{case.case_id.value}'"
            )

        culprit_id = _normalize_suspect_id(case.solution.culprit_suspect_id)
        correct = normalized_submission == culprit_id

        return SolutionResult(correct=correct, explanation=case.solution.explanation)
