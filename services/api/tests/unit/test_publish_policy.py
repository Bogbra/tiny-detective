from app.domain.policies.publish_policy import PublishPolicy
from app.domain.value_objects.publish_status import PublishStatus


def test_approved_consistent_case_is_eligible(make_case):
    case = make_case(status=PublishStatus.APPROVED)

    eligibility = PublishPolicy().evaluate(case)

    assert eligibility.is_eligible is True
    assert eligibility.violations == ()


def test_draft_case_is_not_eligible(make_case):
    case = make_case(status=PublishStatus.DRAFT)

    eligibility = PublishPolicy().evaluate(case)

    assert eligibility.is_eligible is False
    assert any("status" in v for v in eligibility.violations)


def test_inconsistent_case_is_not_eligible(make_case):
    base = make_case()
    case = make_case(status=PublishStatus.APPROVED, clues=base.clues[:1])

    eligibility = PublishPolicy().evaluate(case)

    assert eligibility.is_eligible is False
