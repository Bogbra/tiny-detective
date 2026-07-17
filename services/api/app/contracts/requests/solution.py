from app.contracts.base import ApiModel


class SubmitSolutionRequest(ApiModel):
    player_id: str
    suspect_id: str
