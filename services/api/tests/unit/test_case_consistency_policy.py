import dataclasses

from app.domain.entities.solution import Solution
from app.domain.policies.case_consistency_policy import CaseConsistencyPolicy


def test_valid_case_has_no_violations(make_case):
    case = make_case()

    assert CaseConsistencyPolicy().check(case) == []


def test_too_few_suspects_is_a_violation(make_case):
    case = make_case()
    case = dataclasses.replace(case, suspects=case.suspects[:2])

    violations = CaseConsistencyPolicy().check(case)

    assert any("suspects" in v for v in violations)


def test_too_few_clues_is_a_violation(make_case):
    case = make_case()
    case = dataclasses.replace(case, clues=case.clues[:2])

    violations = CaseConsistencyPolicy().check(case)

    assert any("clues" in v for v in violations)


def test_no_culprit_is_a_violation(make_case):
    case = make_case()
    suspects = tuple(dataclasses.replace(s, is_culprit=False) for s in case.suspects)
    case = dataclasses.replace(case, suspects=suspects)

    violations = CaseConsistencyPolicy().check(case)

    assert any("culprit" in v for v in violations)


def test_multiple_culprits_is_a_violation(make_case):
    case = make_case()
    suspects = tuple(dataclasses.replace(s, is_culprit=True) for s in case.suspects)
    case = dataclasses.replace(case, suspects=suspects)

    violations = CaseConsistencyPolicy().check(case)

    assert any("culprit" in v for v in violations)


def test_solution_culprit_must_match_marked_suspect(make_case):
    case = make_case()
    case = dataclasses.replace(case, solution=Solution(culprit_suspect_id="suspect_1", explanation="wrong"))

    violations = CaseConsistencyPolicy().check(case)

    assert any("culprit_suspect_id" in v for v in violations)


def test_duplicate_suspect_ids_is_a_violation(make_case):
    case = make_case()
    duplicated = dataclasses.replace(case.suspects[1], suspect_id=case.suspects[0].suspect_id)
    suspects = (case.suspects[0], duplicated, case.suspects[2])
    case = dataclasses.replace(case, suspects=suspects)

    violations = CaseConsistencyPolicy().check(case)

    assert any("duplicate suspect ids" in v for v in violations)
