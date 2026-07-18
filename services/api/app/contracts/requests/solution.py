from app.contracts.base import ApiModel
from app.contracts.requests._fields import IdField


class SubmitSolutionRequest(ApiModel):
    player_id: IdField
    suspect_id: IdField
