import random

from ai_content.generator import build_case_candidate_from_rendered, case_logic_to_prompt_json
from ai_content.logic_builder import build_case_logic
from ai_content.rule_validator import validate_rules

from .test_fidelity_checker import _well_rendered


def _case_logic():
    return build_case_logic(random.Random(7))


def test_prompt_json_never_includes_culprit_identity_beyond_the_given_flag():
    # The prompt payload legitimately tells the LLM which token is the
    # culprit (it needs that to write private reasoning), but must never
    # leak anything the deterministic layer decided beyond the fixed facts
    # — no "solved" hint, no explanation text.
    case_logic = _case_logic()
    payload = case_logic_to_prompt_json(case_logic)
    assert set(payload.keys()) == {
        "settingSentence",
        "problemSentence",
        "missingItem",
        "incidentLocation",
        "suspects",
        "clues",
    }
    culprit_flags = [s["isCulprit"] for s in payload["suspects"]]
    assert culprit_flags.count(True) == 1


def test_build_case_candidate_preserves_culprit_from_case_logic_not_rendered():
    case_logic = _case_logic()
    rendered = _well_rendered(case_logic)
    candidate = build_case_candidate_from_rendered(case_logic, rendered)

    culprits = [s for s in candidate.suspects if s.is_culprit]
    assert len(culprits) == 1
    expected_culprit = next(s for s in case_logic.suspects if s.is_culprit)
    culprit_index = case_logic.suspects.index(expected_culprit)
    assert culprits[0].suspect_id == f"suspect_{culprit_index + 1}"


def test_build_case_candidate_ignores_a_rendered_iscupritflag_if_present():
    # Defense in depth: even if a rendered payload somehow included an
    # isCulprit-like field per suspect, build_case_candidate_from_rendered
    # must not read it — identity comes only from case_logic.
    case_logic = _case_logic()
    rendered = _well_rendered(case_logic)
    for s in rendered["suspects"]:
        s["isCulprit"] = True  # deliberately wrong/bogus, must be ignored
    candidate = build_case_candidate_from_rendered(case_logic, rendered)
    assert sum(1 for s in candidate.suspects if s.is_culprit) == 1


def test_well_rendered_candidate_passes_the_unchanged_rule_validator():
    # The downstream rule_validator (title/statement length, clue count,
    # keyword denylist) is untouched by this redesign — a well-formed
    # render must still satisfy it.
    case_logic = _case_logic()
    rendered = _well_rendered(case_logic)
    candidate = build_case_candidate_from_rendered(case_logic, rendered)
    result = validate_rules(candidate)
    assert result.passed is True, result.reasons


def test_build_case_candidate_maps_clue_text_by_id_not_position():
    case_logic = _case_logic()
    rendered = _well_rendered(case_logic)
    # Shuffle the rendered clues array — order must not matter, only clueId.
    rendered["clues"] = list(reversed(rendered["clues"]))
    candidate = build_case_candidate_from_rendered(case_logic, rendered)

    identifying_index = next(i for i, c in enumerate(case_logic.clues) if c.kind == "identifying")
    culprit = next(s for s in case_logic.suspects if s.is_culprit)
    assert culprit.signature_item in candidate.clues[identifying_index].text
