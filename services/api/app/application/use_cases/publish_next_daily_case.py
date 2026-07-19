from datetime import UTC, datetime

from app.application.errors import NoPublishableCaseError
from app.application.ports import CaseRepository
from app.application.use_cases.publish_daily_case import PublishDailyCase
from app.domain.entities.detective_case import DetectiveCase
from app.domain.policies.publish_policy import PublishPolicy
from app.domain.value_objects.case_id import CaseId

_EPOCH = datetime.min.replace(tzinfo=UTC)


def _created_at(case: DetectiveCase) -> datetime:
    return case.created_at or _EPOCH


class PublishNextDailyCase:
    """Picks a case for the recurring scheduled publish (see ADR-0006's
    Cloud Scheduler addendum) so the daily case doesn't depend on a human
    remembering to call publish-daily manually — the actual root cause
    behind two real production outages, not just a documentation gap.

    Selection reuses PublishPolicy.evaluate() rather than a separate
    "approved" filter: that policy already treats APPROVED and LIVE as
    both publishable (a LIVE case has already cleared the bar once), which
    matches this project's real content catalog today — one curated case,
    republished every day. "No publishable case" therefore means the
    catalog is genuinely empty (every case draft/rejected/archived), the
    real failure worth alerting on — not "ran out of fresh content" for a
    single-case catalog that was never going to have daily variety yet.
    """

    def __init__(self, case_repository: CaseRepository, publish_policy: PublishPolicy | None = None) -> None:
        self._case_repository = case_repository
        self._publish_policy = publish_policy or PublishPolicy()
        self._publish_daily_case = PublishDailyCase(case_repository, self._publish_policy)

    def execute(self) -> CaseId:
        all_cases = self._case_repository.list_all()
        eligible = [case for case in all_cases if self._publish_policy.evaluate(case).is_eligible]
        if not eligible:
            raise NoPublishableCaseError("no case is currently eligible to be published as the daily case")

        eligible.sort(key=_created_at)

        current_daily = self._case_repository.get_daily()
        current_daily_id = current_daily.case_id.value if current_daily is not None else None

        # Rotate away from today's case once there's an alternative; fall
        # back to republishing it when it's the only eligible case (today's
        # real catalog) rather than raising an error for a non-problem.
        candidates = [case for case in eligible if case.case_id.value != current_daily_id]
        chosen = candidates[0] if candidates else eligible[0]

        self._publish_daily_case.execute(chosen.case_id)
        return chosen.case_id
