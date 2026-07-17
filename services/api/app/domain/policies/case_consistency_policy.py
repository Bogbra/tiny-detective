from collections import Counter

from app.domain.entities.detective_case import DetectiveCase


class CaseConsistencyPolicy:
    def __init__(self, min_suspects: int = 3, min_clues: int = 3) -> None:
        self.min_suspects = min_suspects
        self.min_clues = min_clues

    def check(self, case: DetectiveCase) -> list[str]:
        violations: list[str] = []

        if len(case.suspects) < self.min_suspects:
            violations.append(f"at least {self.min_suspects} suspects are required")

        if len(case.clues) < self.min_clues:
            violations.append(f"at least {self.min_clues} clues are required")

        suspect_id_counts = Counter(s.suspect_id for s in case.suspects)
        duplicate_suspect_ids = sorted(sid for sid, count in suspect_id_counts.items() if count > 1)
        if duplicate_suspect_ids:
            violations.append(f"duplicate suspect ids: {duplicate_suspect_ids}")

        clue_id_counts = Counter(c.clue_id for c in case.clues)
        duplicate_clue_ids = sorted(cid for cid, count in clue_id_counts.items() if count > 1)
        if duplicate_clue_ids:
            violations.append(f"duplicate clue ids: {duplicate_clue_ids}")

        culprits = [s for s in case.suspects if s.is_culprit]
        if len(culprits) != 1:
            violations.append(
                f"exactly one suspect must be marked as the culprit, found {len(culprits)}"
            )
        elif culprits[0].suspect_id != case.solution.culprit_suspect_id:
            violations.append("solution.culprit_suspect_id must match the suspect marked as culprit")

        return violations
