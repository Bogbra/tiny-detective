from app.domain.policies.scoring_policy import ScoringPolicy


def test_incorrect_answer_scores_zero():
    assert ScoringPolicy().calculate_score(correct=False, hints_used=0) == 0


def test_correct_answer_with_no_hints_scores_max():
    assert ScoringPolicy().calculate_score(correct=True, hints_used=0) == 100


def test_each_hint_reduces_score():
    policy = ScoringPolicy()

    assert policy.calculate_score(correct=True, hints_used=1) == 85
    assert policy.calculate_score(correct=True, hints_used=2) == 70


def test_score_never_drops_below_minimum():
    policy = ScoringPolicy()

    assert policy.calculate_score(correct=True, hints_used=50) == policy.min_score
