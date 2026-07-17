from app.contracts.base import ApiModel


class AdminActionResponse(ApiModel):
    case_id: str
    status: str
