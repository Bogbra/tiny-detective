from app.contracts.base import ApiModel


class HintResponse(ApiModel):
    text: str
    hints_used: int
    hints_remaining: int
