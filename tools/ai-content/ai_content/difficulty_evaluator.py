"""Difficulty Evaluator: heuristic based on clue count and suspect count —
The project spec's own criteria ("clue clarity, number of suspects, directness of
evidence, amount of deduction required") are structural/countable enough for
a rule-based assignment; no AI call needed.
"""

from .models import CaseCandidate


def assign_difficulty(candidate: CaseCandidate) -> str:
    clue_count = len(candidate.clues)
    suspect_count = len(candidate.suspects)

    if clue_count <= 3 and suspect_count <= 3:
        return "easy"
    if clue_count >= 5 or suspect_count >= 5:
        return "hard"
    return "medium"
