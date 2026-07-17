from app.application.errors import CaseNotFoundError
from app.application.ports import CaseRepository
from app.domain.entities.public_views import PublicDetectiveCase
from app.domain.value_objects.case_id import CaseId
from app.domain.value_objects.publish_status import PublishStatus

_PUBLICLY_VISIBLE_STATUSES = (PublishStatus.APPROVED, PublishStatus.LIVE)


class GetCase:
    def __init__(self, case_repository: CaseRepository) -> None:
        self._case_repository = case_repository

    def execute(self, case_id: CaseId) -> PublicDetectiveCase:
        case = self._case_repository.get(case_id)
        if case is None or case.status not in _PUBLICLY_VISIBLE_STATUSES:
            raise CaseNotFoundError(f"case '{case_id.value}' not found")
        return case.public_view()
