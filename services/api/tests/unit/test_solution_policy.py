import pytest

from app.domain.errors import UnknownSuspectError
from app.domain.policies.solution_policy import SolutionPolicy


def test_correct_suspect_is_marked_correct(make_case):
    case = make_case()

    result = SolutionPolicy().evaluate(case, "suspect_3")

    assert result.correct is True
    assert result.explanation == case.solution.explanation


def test_incorrect_suspect_is_marked_incorrect(make_case):
    case = make_case()

    result = SolutionPolicy().evaluate(case, "suspect_1")

    assert result.correct is False


def test_answer_is_normalized_before_comparison(make_case):
    case = make_case()

    result = SolutionPolicy().evaluate(case, "  Suspect_3  ")

    assert result.correct is True


def test_unknown_suspect_raises(make_case):
    case = make_case()

    with pytest.raises(UnknownSuspectError):
        SolutionPolicy().evaluate(case, "suspect_99")
