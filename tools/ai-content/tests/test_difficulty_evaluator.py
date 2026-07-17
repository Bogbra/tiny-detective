import dataclasses

from ai_content.difficulty_evaluator import assign_difficulty
from ai_content.schema_parser import parse_case_candidate


def test_few_clues_and_suspects_is_easy(valid_raw_candidate):
    candidate = parse_case_candidate(valid_raw_candidate)
    assert len(candidate.clues) == 3 and len(candidate.suspects) == 3

    assert assign_difficulty(candidate) == "easy"


def test_many_clues_is_hard(valid_raw_candidate):
    candidate = parse_case_candidate(valid_raw_candidate)
    extra_clues = candidate.clues + tuple(
        dataclasses.replace(candidate.clues[0], clue_id=f"clue_extra_{i}") for i in range(3)
    )
    candidate = dataclasses.replace(candidate, clues=extra_clues)

    assert assign_difficulty(candidate) == "hard"


def test_moderate_clue_count_is_medium(valid_raw_candidate):
    candidate = parse_case_candidate(valid_raw_candidate)
    extra_clue = dataclasses.replace(candidate.clues[0], clue_id="clue_extra")
    candidate = dataclasses.replace(candidate, clues=candidate.clues + (extra_clue,))

    assert assign_difficulty(candidate) == "medium"
