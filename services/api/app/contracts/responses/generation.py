from app.contracts.base import ApiModel
from app.contracts.responses.case import CaseResponse


class GenerationEventResponse(ApiModel):
    step: str
    status: str
    detail: str | None = None
    attempt: int | None = None
    case: CaseResponse | None = None
