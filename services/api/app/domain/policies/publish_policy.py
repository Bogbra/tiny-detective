from dataclasses import dataclass

from app.domain.entities.detective_case import DetectiveCase
from app.domain.policies.case_consistency_policy import CaseConsistencyPolicy
from app.domain.value_objects.publish_status import PublishStatus


@dataclass(frozen=True, slots=True)
class PublishEligibility:
    is_eligible: bool
    violations: tuple[str, ...] = ()


class PublishPolicy:
    def __init__(self, consistency_policy: CaseConsistencyPolicy | None = None) -> None:
        self._consistency_policy = consistency_policy or CaseConsistencyPolicy()

    def evaluate(self, case: DetectiveCase) -> PublishEligibility:
        violations = list(self._consistency_policy.check(case))

        if case.status != PublishStatus.APPROVED:
            violations.append(
                f"case status must be '{PublishStatus.APPROVED.value}' to publish, "
                f"got '{case.status.value}'"
            )

        return PublishEligibility(is_eligible=not violations, violations=tuple(violations))
