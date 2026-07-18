"""Verifies an LLM-rendered prose response didn't drift from the fixed
CaseLogic it was given to decorate (see logic_builder.py,
generator.CaseProseRenderer). Pure, no I/O.

This is the load-bearing correctness gate for the redesigned pipeline: since
the LLM's job is now narrow (write natural sentences around fixed facts, not
invent or verify a deduction), "did it keep the given facts" is a plain
verbatim-substring check, not a probabilistic judgment call — unlike the old
pipeline's logic judge, which had to evaluate deductive validity itself. See
ADR-0007's redesign addendum.
"""

import re
from dataclasses import dataclass

from .logic_builder import CaseLogic


@dataclass(frozen=True, slots=True)
class FidelityResult:
    passed: bool
    reasons: tuple[str, ...] = ()


_LEADING_ARTICLE = re.compile(r"^(a|an)\s+", re.IGNORECASE)


def _core(phrase: str) -> str:
    """Strips a leading indefinite article before matching. Real observed
    LLM behavior (see ADR-0007's redesign addendum): a signature item
    authored as "a paint-stained sketchbook" gets naturally reworded as
    "Tommy's paint-stained sketchbook" or "the paint-stained sketchbook"
    when a specific person's item is being described — grammatically
    correct prose that a naive full-phrase substring check would wrongly
    reject. The noun phrase after the article is the actually-identifying
    part; the article itself was never load-bearing."""
    return _LEADING_ARTICLE.sub("", phrase).strip().lower()


def _contains_phrase(haystack: str, phrase: str) -> bool:
    return _core(phrase) in haystack.lower()


def check_fidelity(case_logic: CaseLogic, rendered: dict) -> FidelityResult:
    reasons: list[str] = []

    suspects_raw = rendered.get("suspects")
    statements_by_token = (
        {s.get("token"): s.get("publicStatement", "") for s in suspects_raw}
        if isinstance(suspects_raw, list)
        else {}
    )
    for suspect in case_logic.suspects:
        statement = statements_by_token.get(suspect.token)
        if statement is None:
            reasons.append(f"missing publicStatement for {suspect.token}")
            continue
        if not _contains_phrase(statement, suspect.claimed_location):
            reasons.append(
                f"{suspect.token}'s public statement does not mention their claimed "
                f"location ({suspect.claimed_location!r} verbatim)"
            )
        if suspect.is_culprit and not _contains_phrase(statement, suspect.signature_item):
            # The identifying clue never says WHOSE item was found — that
            # ownership link has to come from somewhere textual, or a judge
            # (correctly) has no basis to connect the item to this suspect.
            # See ADR-0007's redesign addendum: this was a real gap found
            # via the logic judge rejecting every candidate for exactly
            # this reason, not a hypothetical one.
            reasons.append(
                f"{suspect.token} (the culprit) does not establish ownership of their "
                f"own signature item ({suspect.signature_item!r}) in their own statement"
            )

    clues_raw = rendered.get("clues")
    clue_text_by_id = (
        {c.get("clueId"): c.get("text", "") for c in clues_raw} if isinstance(clues_raw, list) else {}
    )
    for clue in case_logic.clues:
        text = clue_text_by_id.get(clue.clue_id)
        if text is None:
            reasons.append(f"missing text for {clue.clue_id}")
            continue
        for phrase in clue.required_phrases:
            if not _contains_phrase(text, phrase):
                reasons.append(f"{clue.clue_id} does not contain required phrase {phrase!r} verbatim")

    culprit = next(s for s in case_logic.suspects if s.is_culprit)
    explanation = rendered.get("solutionExplanation", "")
    if not isinstance(explanation, str):
        explanation = ""
    if not _contains_phrase(explanation, culprit.signature_item):
        reasons.append("solutionExplanation does not reference the culprit's identifying detail verbatim")
    if not _contains_phrase(explanation, case_logic.template.incident_location):
        reasons.append("solutionExplanation does not reference the incident location verbatim")

    return FidelityResult(passed=not reasons, reasons=tuple(reasons))
