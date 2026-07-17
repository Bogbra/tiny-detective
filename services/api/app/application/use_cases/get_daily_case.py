from app.application.errors import CaseNotFoundError
from app.application.ports import CaseRepository
from app.domain.entities.public_views import PublicDetectiveCase


class GetDailyCase:
    def __init__(self, case_repository: CaseRepository) -> None:
        self._case_repository = case_repository

    def execute(self) -> PublicDetectiveCase:
        case = self._case_repository.get_daily()
        if case is None:
            raise CaseNotFoundError("no daily case is currently published")
        return case.public_view()
