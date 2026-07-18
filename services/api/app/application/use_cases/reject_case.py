import dataclasses

from app.application.errors import CaseNotFoundError, CaseNotInDraftError
from app.application.ports import CaseRepository
from app.domain.value_objects.case_id import CaseId
from app.domain.value_objects.publish_status import PublishStatus


class RejectCase:
    def __init__(self, case_repository: CaseRepository) -> None:
        self._case_repository = case_repository

    def execute(self, case_id: CaseId) -> None:
        case = self._case_repository.get(case_id)
        if case is None:
            raise CaseNotFoundError(f"case '{case_id.value}' not found")
        if case.status != PublishStatus.DRAFT:
            raise CaseNotInDraftError(f"case '{case_id.value}' is '{case.status.value}', not draft")

        self._case_repository.save(dataclasses.replace(case, status=PublishStatus.REJECTED))
