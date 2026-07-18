import random

from ai_content.fidelity_checker import check_fidelity
from ai_content.logic_builder import build_case_logic


def _case_logic():
    return build_case_logic(random.Random(7))


def _well_rendered(case_logic):
    """A rendered dict that satisfies every fidelity requirement — the
    baseline every corruption test below mutates away from."""
    culprit = next(s for s in case_logic.suspects if s.is_culprit)
    suspects = [
        {
            "token": s.token,
            "name": f"Name-{s.token}",
            "publicStatement": (
                f"I was near {s.claimed_location} the whole time, and that's my {s.signature_item}."
                if s.is_culprit
                else f"I was near {s.claimed_location} the whole time."
            ),
            "privateReasoning": "Nothing unusual to report.",
        }
        for s in case_logic.suspects
    ]
    clues = [
        {"clueId": c.clue_id, "text": "Found: " + " and ".join(c.required_phrases) + "."}
        for c in case_logic.clues
    ]
    return {
        "title": "A Small Mystery",
        "setting": case_logic.template.setting_sentence,
        "problem": case_logic.template.problem_sentence,
        "suspects": suspects,
        "clues": clues,
        "solutionExplanation": (
            f"The {culprit.signature_item} found at {case_logic.template.incident_location} gives it away."
        ),
    }


def test_well_formed_render_passes():
    case_logic = _case_logic()
    result = check_fidelity(case_logic, _well_rendered(case_logic))
    assert result.passed is True
    assert result.reasons == ()


def test_culprit_statement_missing_signature_item_ownership_fails():
    case_logic = _case_logic()
    rendered = _well_rendered(case_logic)
    culprit = next(s for s in case_logic.suspects if s.is_culprit)
    for s in rendered["suspects"]:
        if s["token"] == culprit.token:
            s["publicStatement"] = f"I was near {culprit.claimed_location} the whole time."
    result = check_fidelity(case_logic, rendered)
    assert result.passed is False
    assert any("does not establish ownership" in r for r in result.reasons)


def test_innocent_statement_without_signature_item_still_passes():
    # Only the culprit needs to establish ownership of their signature item
    # in their own statement — innocents don't (their alibi clue does that
    # corroboration work instead).
    case_logic = _case_logic()
    rendered = _well_rendered(case_logic)
    result = check_fidelity(case_logic, rendered)
    assert result.passed is True


def test_missing_claimed_location_in_statement_fails():
    case_logic = _case_logic()
    rendered = _well_rendered(case_logic)
    rendered["suspects"][0]["publicStatement"] = "I was somewhere else entirely."
    result = check_fidelity(case_logic, rendered)
    assert result.passed is False
    assert any("claimed location" in r for r in result.reasons)


def test_paraphrased_required_phrase_in_clue_fails():
    case_logic = _case_logic()
    rendered = _well_rendered(case_logic)
    # Replace the identifying clue's text with something that paraphrases
    # away the required phrases instead of stating them verbatim.
    rendered["clues"] = [{"clueId": "clue_identifying", "text": "Something suspicious was found nearby."}] + [
        c for c in rendered["clues"] if c["clueId"] != "clue_identifying"
    ]
    result = check_fidelity(case_logic, rendered)
    assert result.passed is False
    assert any("clue_identifying" in r for r in result.reasons)


def test_solution_explanation_missing_identifying_detail_fails():
    case_logic = _case_logic()
    rendered = _well_rendered(case_logic)
    rendered["solutionExplanation"] = "It's obvious who did it, trust me."
    result = check_fidelity(case_logic, rendered)
    assert result.passed is False
    assert any("identifying detail" in r or "incident location" in r for r in result.reasons)


def test_missing_suspect_entirely_fails():
    case_logic = _case_logic()
    rendered = _well_rendered(case_logic)
    rendered["suspects"] = rendered["suspects"][:-1]
    result = check_fidelity(case_logic, rendered)
    assert result.passed is False
    assert any("missing publicStatement" in r for r in result.reasons)


def test_missing_clue_entirely_fails():
    case_logic = _case_logic()
    rendered = _well_rendered(case_logic)
    rendered["clues"] = rendered["clues"][:-1]
    result = check_fidelity(case_logic, rendered)
    assert result.passed is False
    assert any("missing text" in r for r in result.reasons)


def test_case_insensitive_matching_still_passes():
    case_logic = _case_logic()
    rendered = _well_rendered(case_logic)
    rendered["solutionExplanation"] = rendered["solutionExplanation"].upper()
    for c in rendered["clues"]:
        c["text"] = c["text"].upper()
    for s in rendered["suspects"]:
        s["publicStatement"] = s["publicStatement"].upper()
    result = check_fidelity(case_logic, rendered)
    assert result.passed is True
