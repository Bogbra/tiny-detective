import copy

import pytest

from ai_content.schema_parser import SchemaValidationError, parse_case_candidate


def test_valid_candidate_parses(valid_raw_candidate):
    candidate = parse_case_candidate(valid_raw_candidate)

    assert candidate.title == "The Missing Museum Key"
    assert len(candidate.suspects) == 3
    assert len(candidate.clues) == 3
    assert sum(s.is_culprit for s in candidate.suspects) == 1


def test_non_object_json_is_rejected():
    with pytest.raises(SchemaValidationError):
        parse_case_candidate(["not", "an", "object"])


def test_missing_required_field_is_rejected(valid_raw_candidate):
    broken = copy.deepcopy(valid_raw_candidate)
    del broken["solution"]

    with pytest.raises(SchemaValidationError) as exc_info:
        parse_case_candidate(broken)

    assert any("solution" in reason for reason in exc_info.value.reasons)


def test_too_few_suspects_is_rejected(valid_raw_candidate):
    broken = copy.deepcopy(valid_raw_candidate)
    broken["suspects"] = broken["suspects"][:2]

    with pytest.raises(SchemaValidationError) as exc_info:
        parse_case_candidate(broken)

    assert any("suspects" in reason for reason in exc_info.value.reasons)


def test_too_few_clues_is_rejected(valid_raw_candidate):
    broken = copy.deepcopy(valid_raw_candidate)
    broken["clues"] = broken["clues"][:2]

    with pytest.raises(SchemaValidationError) as exc_info:
        parse_case_candidate(broken)

    assert any("clues" in reason for reason in exc_info.value.reasons)


def test_culprit_name_mismatch_is_rejected(valid_raw_candidate):
    broken = copy.deepcopy(valid_raw_candidate)
    broken["solution"]["culpritName"] = "Nobody Here"

    with pytest.raises(SchemaValidationError) as exc_info:
        parse_case_candidate(broken)

    assert any("culpritName" in reason for reason in exc_info.value.reasons)


def test_assigns_stable_suspect_and_clue_ids(valid_raw_candidate):
    candidate = parse_case_candidate(valid_raw_candidate)

    assert [s.suspect_id for s in candidate.suspects] == ["suspect_1", "suspect_2", "suspect_3"]
    assert [c.clue_id for c in candidate.clues] == ["clue_1", "clue_2", "clue_3"]
