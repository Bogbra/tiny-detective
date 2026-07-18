"""Deterministic case-logic construction — the root-cause fix for the live
case-generation feature's low pass rate (see services/api's ADR-0007
redesign addendum).

The old pipeline asked an LLM to invent a whodunit AND verify its own
deduction in one generative pass; it reliably wrote a satisfying-sounding
solution.explanation that didn't actually follow from the clues it also
invented. This module removes that failure mode structurally: who's guilty,
which suspect has an alibi, and which concrete detail identifies the culprit
are all decided here, in plain Python, with zero LLM involvement and zero
I/O. The LLM's job (generator.render_case_prose) is reduced to writing
prose around an already-solved structure — it cannot get the logic wrong
because it is never asked to invent or verify it.

solve() is the actual verification step: it re-derives the culprit from the
same facts a careful player would have (who was really at the incident
location, who has a corroborating alibi clue) and asserts the result
matches the label build_case_logic() assigned — a real check, not a
trust-the-constructor assumption. See tests/test_logic_builder.py for the
property test that runs this across hundreds of random seeds.
"""

import random
from dataclasses import dataclass

from .scenario_templates import SCENARIO_TEMPLATES, ScenarioTemplate

SUSPECT_TOKENS: tuple[str, str, str] = ("SUSPECT_1", "SUSPECT_2", "SUSPECT_3")


class LogicBuildError(Exception):
    """A constructed CaseLogic failed its own solve() check. Should never
    happen given the construction in build_case_logic() — raised rather
    than silently trusted, so a real construction bug fails loudly instead
    of quietly shipping an unsolvable case downstream."""


@dataclass(frozen=True, slots=True)
class SuspectLogic:
    token: str
    role: str
    signature_item: str
    is_culprit: bool
    real_location: str
    claimed_location: str  # what they publicly say; equals real_location unless is_culprit


@dataclass(frozen=True, slots=True)
class ClueLogic:
    clue_id: str
    kind: str  # "identifying" | "alibi" | "neutral"
    subject_token: str | None
    required_phrases: tuple[str, ...]  # exact phrases the rendered clue text MUST contain verbatim


@dataclass(frozen=True, slots=True)
class CaseLogic:
    template: ScenarioTemplate
    suspects: tuple[SuspectLogic, SuspectLogic, SuspectLogic]
    clues: tuple[ClueLogic, ...]
    culprit_token: str


def build_case_logic(rng: random.Random) -> CaseLogic:
    template = rng.choice(SCENARIO_TEMPLATES)

    role_indices = [0, 1, 2]
    rng.shuffle(role_indices)
    culprit_token = rng.choice(SUSPECT_TOKENS)

    alibi_locations = list(template.alibi_locations)
    rng.shuffle(alibi_locations)
    alibi_iter = iter(alibi_locations)
    # The culprit's false alibi claim — need not differ from an innocent
    # suspect's real location; the contradiction that matters is the
    # culprit's own claim vs. their own real (incident) location.
    culprit_claim = rng.choice(template.alibi_locations)

    suspects: list[SuspectLogic] = []
    for token, role_idx in zip(SUSPECT_TOKENS, role_indices, strict=True):
        role = template.roles[role_idx]
        signature_item = template.signature_items[role_idx]
        is_culprit = token == culprit_token
        if is_culprit:
            real_location = template.incident_location
            claimed_location = culprit_claim
        else:
            real_location = next(alibi_iter)
            claimed_location = real_location
        suspects.append(
            SuspectLogic(
                token=token,
                role=role,
                signature_item=signature_item,
                is_culprit=is_culprit,
                real_location=real_location,
                claimed_location=claimed_location,
            )
        )

    culprit = next(s for s in suspects if s.is_culprit)

    clues: list[ClueLogic] = [
        ClueLogic(
            clue_id="clue_identifying",
            kind="identifying",
            subject_token=culprit.token,
            required_phrases=(culprit.signature_item, template.incident_location),
        )
    ]
    for s in suspects:
        if not s.is_culprit:
            clues.append(
                ClueLogic(
                    clue_id=f"clue_alibi_{s.token}",
                    kind="alibi",
                    subject_token=s.token,
                    required_phrases=(s.signature_item, s.real_location),
                )
            )
    clues.append(ClueLogic(clue_id="clue_neutral", kind="neutral", subject_token=None, required_phrases=()))

    case_logic = CaseLogic(
        template=template,
        suspects=(suspects[0], suspects[1], suspects[2]),
        clues=tuple(clues),
        culprit_token=culprit_token,
    )

    solved_token = solve(case_logic)
    if solved_token != culprit_token:
        raise LogicBuildError(
            f"constructed case did not solve to its own culprit: "
            f"solved={solved_token!r} expected={culprit_token!r}"
        )

    return case_logic


def solve(case_logic: CaseLogic) -> str:
    """Independently re-derives the culprit from real_location/alibi facts
    (never reads case_logic.culprit_token) and returns the single surviving
    suspect's token. Raises LogicBuildError if zero or more than one
    suspect survives elimination — this is the real solvability guarantee,
    computed the same way a careful player would: who was actually at the
    incident location, with no corroborating alibi clue.
    """
    alibied_tokens = {c.subject_token for c in case_logic.clues if c.kind == "alibi"}
    candidates = [
        s.token
        for s in case_logic.suspects
        if s.real_location == case_logic.template.incident_location and s.token not in alibied_tokens
    ]
    if len(candidates) != 1:
        raise LogicBuildError(
            f"expected exactly one suspect at the incident location without an alibi, found {candidates!r}"
        )
    return candidates[0]
