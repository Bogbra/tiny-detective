from app.domain.policies.hint_guardrail_policy import HintGuardrailPolicy


def test_passes_when_no_suspect_identifier_present(make_case):
    case = make_case()

    result = HintGuardrailPolicy().check("Take another look at the physical evidence.", case)

    assert result.passed is True
    assert result.violated_identifiers == ()


def test_fails_when_culprit_name_present(make_case):
    case = make_case()
    culprit_name = next(s.name for s in case.suspects if s.is_culprit)

    result = HintGuardrailPolicy().check(f"{culprit_name} seems suspicious.", case)

    assert result.passed is False
    assert culprit_name in result.violated_identifiers


def test_fails_when_innocent_suspect_name_present(make_case):
    case = make_case()
    innocent_name = next(s.name for s in case.suspects if not s.is_culprit)

    result = HintGuardrailPolicy().check(f"Reconsider {innocent_name}'s statement.", case)

    assert result.passed is False


def test_match_is_case_insensitive(make_case):
    case = make_case()
    culprit_name = next(s.name for s in case.suspects if s.is_culprit)

    result = HintGuardrailPolicy().check(f"i think {culprit_name.upper()} did it", case)

    assert result.passed is False


def test_fails_when_role_mention_is_not_grounded_in_the_referenced_clue(make_case):
    """A role not explained by the clue being pointed at is a referential
    identification, not a vocabulary coincidence — must be rejected. Regression
    test for the false negative introduced when role-checking was dropped
    entirely (see hint_guardrail_cases.json / the policy's module docstring)."""
    case = make_case()
    culprit_role = next(s.role for s in case.suspects if s.is_culprit)

    result = HintGuardrailPolicy().check(
        f"The {culprit_role}'s statement doesn't fit the sensor evidence.",
        case,
        referenced_clue_text="The archive motion sensor stayed inactive.",
    )

    assert result.passed is False
    assert culprit_role in result.violated_identifiers


def test_passes_when_role_mention_is_grounded_in_the_referenced_clue(make_case):
    """A role word that's part of the specific clue's own wording is the AI
    quoting already-public case content, not identifying anyone."""
    case = make_case()
    culprit_role = next(s.role for s in case.suspects if s.is_culprit)
    clue_text = f"A {culprit_role.lower()} wristband was found near the display case."

    result = HintGuardrailPolicy().check(
        f"Take another look at the {culprit_role.lower()} wristband found near the display case.",
        case,
        referenced_clue_text=clue_text,
    )

    assert result.passed is True


def test_role_grounded_in_a_different_clue_than_the_one_referenced_still_fails(make_case):
    """Grounding is scoped to the SPECIFIC clue this hint points at, not
    "any clue in the case" — a role appearing in some other clue's text
    doesn't excuse using it referentially against a different clue."""
    case = make_case()
    culprit_role = next(s.role for s in case.suspects if s.is_culprit)

    result = HintGuardrailPolicy().check(
        f"The {culprit_role.lower()} seems to be lying about the timeline.",
        case,
        referenced_clue_text="There were no signs of forced entry.",
    )

    assert result.passed is False
