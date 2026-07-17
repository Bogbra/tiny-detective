import dataclasses

from ai_content.rule_validator import validate_rules
from ai_content.schema_parser import parse_case_candidate


def test_valid_candidate_passes(valid_raw_candidate):
    candidate = parse_case_candidate(valid_raw_candidate)

    result = validate_rules(candidate)

    assert result.passed is True
    assert result.reasons == ()


def test_unsafe_keyword_is_rejected(valid_raw_candidate):
    raw = valid_raw_candidate.copy()
    raw["problem"] = "A chef's knife went missing from the display case."
    candidate = parse_case_candidate(raw)

    result = validate_rules(candidate)

    assert result.passed is False
    assert any("disallowed keywords" in reason for reason in result.reasons)


def test_duplicate_suspect_names_is_rejected(valid_raw_candidate):
    candidate = parse_case_candidate(valid_raw_candidate)
    duplicated = dataclasses.replace(candidate.suspects[1], name=candidate.suspects[0].name)
    candidate = dataclasses.replace(
        candidate, suspects=(candidate.suspects[0], duplicated, candidate.suspects[2])
    )

    result = validate_rules(candidate)

    assert result.passed is False
    assert any("duplicate suspect names" in reason for reason in result.reasons)


def test_title_too_short_is_rejected(valid_raw_candidate):
    candidate = parse_case_candidate(valid_raw_candidate)
    candidate = dataclasses.replace(candidate, title="Hi")

    result = validate_rules(candidate)

    assert result.passed is False
    assert any("title length" in reason for reason in result.reasons)


def test_wrong_culprit_count_is_rejected(valid_raw_candidate):
    candidate = parse_case_candidate(valid_raw_candidate)
    no_culprit = tuple(dataclasses.replace(s, is_culprit=False) for s in candidate.suspects)
    candidate = dataclasses.replace(candidate, suspects=no_culprit)

    result = validate_rules(candidate)

    assert result.passed is False
    assert any("exactly one culprit" in reason for reason in result.reasons)
