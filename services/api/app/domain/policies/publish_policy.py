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

    # A case that's already LIVE is eligible too, not just APPROVED — it has
    # already cleared this exact bar once (nothing about re-featuring it as
    # a later day's daily case makes it less vetted than it was the first
    # time). Without this, any case becomes permanently un-republishable
    # the moment it's first published, since publishing moves it out of
    # APPROVED — found in production, not in review: the demo's one
    # curated case couldn't be re-set as the next day's daily case at all,
    # and publish-daily's own error message was the only symptom.
    _PUBLISHABLE_STATUSES = (PublishStatus.APPROVED, PublishStatus.LIVE)

    def evaluate(self, case: DetectiveCase) -> PublishEligibility:
        violations = list(self._consistency_policy.check(case))

        if case.status not in self._PUBLISHABLE_STATUSES:
            allowed = "' or '".join(s.value for s in self._PUBLISHABLE_STATUSES)
            violations.append(f"case status must be '{allowed}' to publish, got '{case.status.value}'")

        return PublishEligibility(is_eligible=not violations, violations=tuple(violations))
