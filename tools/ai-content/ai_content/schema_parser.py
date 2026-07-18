"""Schema Parser stage: valid JSON, required fields, correct types, exactly
one solution, at least three suspects, at least three clues (per the project
spec's "Schema Parser" section). Assigns suspect_id/clue_id slugs while parsing.
"""

from .models import CandidateClue, CandidateSuspect, CaseCandidate

MIN_SUSPECTS = 3
MIN_CLUES = 3


class SchemaValidationError(Exception):
    def __init__(self, reasons: list[str]) -> None:
        self.reasons = reasons
        super().__init__("; ".join(reasons))


def parse_case_candidate(raw: object) -> CaseCandidate:
    if not isinstance(raw, dict):
        raise SchemaValidationError(["top-level JSON must be an object"])

    reasons: list[str] = []
    for field in ("title", "setting", "problem", "suspects", "clues", "solution"):
        if field not in raw:
            reasons.append(f"missing required field '{field}'")
    if reasons:
        raise SchemaValidationError(reasons)

    for field in ("title", "setting", "problem"):
        if not isinstance(raw[field], str) or not raw[field].strip():
            reasons.append(f"'{field}' must be a non-empty string")

    suspects_raw = raw["suspects"]
    if not isinstance(suspects_raw, list) or len(suspects_raw) < MIN_SUSPECTS:
        reasons.append(f"at least {MIN_SUSPECTS} suspects are required")

    clues_raw = raw["clues"]
    if not isinstance(clues_raw, list) or len(clues_raw) < MIN_CLUES:
        reasons.append(f"at least {MIN_CLUES} clues are required")

    solution_raw = raw["solution"]
    if (
        not isinstance(solution_raw, dict)
        or "culpritName" not in solution_raw
        or "explanation" not in solution_raw
    ):
        reasons.append("solution must be an object with 'culpritName' and 'explanation'")

    if reasons:
        raise SchemaValidationError(reasons)

    suspects: list[CandidateSuspect] = []
    culprit_names: set[str] = set()
    for i, s in enumerate(suspects_raw, start=1):
        if not isinstance(s, dict) or not all(
            isinstance(s.get(k), str) and s.get(k, "").strip() for k in ("name", "role", "publicStatement")
        ):
            reasons.append(f"suspect #{i} is missing a required string field")
            continue
        culprit_names.add(s["name"])
        suspects.append(
            CandidateSuspect(
                suspect_id=f"suspect_{i}",
                name=s["name"],
                role=s["role"],
                public_statement=s["publicStatement"],
                private_reasoning=s.get("privateReasoning", ""),
                is_culprit=s["name"] == solution_raw.get("culpritName"),
            )
        )

    clues: list[CandidateClue] = []
    for i, c in enumerate(clues_raw, start=1):
        if not isinstance(c, str) or not c.strip():
            reasons.append(f"clue #{i} must be a non-empty string")
            continue
        clues.append(CandidateClue(clue_id=f"clue_{i}", text=c))

    if not isinstance(solution_raw["explanation"], str) or not solution_raw["explanation"].strip():
        reasons.append("solution.explanation must be a non-empty string")

    if solution_raw.get("culpritName") not in culprit_names:
        reasons.append("solution.culpritName does not match any suspect name")

    if reasons:
        raise SchemaValidationError(reasons)

    return CaseCandidate(
        title=raw["title"],
        setting=raw["setting"],
        problem=raw["problem"],
        suspects=tuple(suspects),
        clues=tuple(clues),
        solution_explanation=solution_raw["explanation"],
        difficulty=raw.get("difficulty"),
        tone=raw.get("tone"),
    )
