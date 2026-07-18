import dataclasses

from app.application.errors import CaseNotFoundError, CaseNotPublishableError
from app.application.ports import CaseRepository
from app.domain.policies.publish_policy import PublishPolicy
from app.domain.value_objects.case_id import CaseId
from app.domain.value_objects.publish_status import PublishStatus


class PublishDailyCase:
    def __init__(self, case_repository: CaseRepository, publish_policy: PublishPolicy | None = None) -> None:
        self._case_repository = case_repository
        self._publish_policy = publish_policy or PublishPolicy()

    def execute(self, case_id: CaseId) -> None:
        case = self._case_repository.get(case_id)
        if case is None:
            raise CaseNotFoundError(f"case '{case_id.value}' not found")

        eligibility = self._publish_policy.evaluate(case)
        if not eligibility.is_eligible:
            raise CaseNotPublishableError(eligibility.violations)

        published_case = dataclasses.replace(case, status=PublishStatus.LIVE)
        self._case_repository.save(published_case)
        self._case_repository.set_daily(case_id)
