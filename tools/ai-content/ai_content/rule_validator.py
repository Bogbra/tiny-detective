"""Rule-Based Validator stage: no empty fields, answer exists among suspects
(guaranteed by the schema parser), no duplicate suspects/clues, clue count
range, title/statement length, family-friendly categories only.

IMPORTANT — what the keyword denylist below is and isn't: it is a coarse,
cheap, deterministic pre-filter that catches only the obvious cases (a
literal banned word appearing in the text) for free, before spending an API
call. It is NOT the safety mechanism for this project. The AI Safety
Evaluator (ai_content/openai_evaluators.py:OpenAISafetyEvaluator) does the
actual nuanced judgment — tone, implication, context a keyword list can't
see. Treat a "rules" stage rejection as "obviously bad", and treat passing
this stage as "not yet judged safe", not as "safe".
"""

from dataclasses import dataclass

from .models import CaseCandidate

MIN_TITLE_LENGTH = 4
MAX_TITLE_LENGTH = 80
MIN_STATEMENT_LENGTH = 10
MAX_STATEMENT_LENGTH = 300
MIN_CLUES = 3
MAX_CLUES = 6

UNSAFE_KEYWORDS = (
    "murder",
    "kill",
    "blood",
    "gun",
    "knife",
    "weapon",
    "corpse",
    "dead body",
    "suicide",
    "self-harm",
    "drugs",
    "sexual",
    "naked",
    "rape",
    "terroris",
    "bomb",
    "nazi",
    "hitler",
)


@dataclass(frozen=True, slots=True)
class RuleValidationResult:
    passed: bool
    reasons: tuple[str, ...] = ()


def validate_rules(candidate: CaseCandidate) -> RuleValidationResult:
    reasons: list[str] = []

    if not (MIN_TITLE_LENGTH <= len(candidate.title) <= MAX_TITLE_LENGTH):
        reasons.append(f"title length must be between {MIN_TITLE_LENGTH} and {MAX_TITLE_LENGTH} characters")

    if not (MIN_CLUES <= len(candidate.clues) <= MAX_CLUES):
        reasons.append(f"clue count must be between {MIN_CLUES} and {MAX_CLUES}")

    for suspect in candidate.suspects:
        if not (MIN_STATEMENT_LENGTH <= len(suspect.public_statement) <= MAX_STATEMENT_LENGTH):
            reasons.append(f"suspect '{suspect.name}' statement length out of range")

    names = [s.name for s in candidate.suspects]
    if len(names) != len(set(names)):
        reasons.append("duplicate suspect names")

    clue_texts = [c.text for c in candidate.clues]
    if len(clue_texts) != len(set(clue_texts)):
        reasons.append("duplicate clue text")

    culprits = [s for s in candidate.suspects if s.is_culprit]
    if len(culprits) != 1:
        reasons.append(f"exactly one culprit is required, found {len(culprits)}")

    full_text = " ".join(
        [candidate.title, candidate.setting, candidate.problem, candidate.solution_explanation]
        + [s.public_statement for s in candidate.suspects]
        + clue_texts
    ).lower()
    hit_keywords = [kw for kw in UNSAFE_KEYWORDS if kw in full_text]
    if hit_keywords:
        reasons.append(f"contains disallowed keywords for a family-friendly case: {hit_keywords}")

    return RuleValidationResult(passed=not reasons, reasons=tuple(reasons))
