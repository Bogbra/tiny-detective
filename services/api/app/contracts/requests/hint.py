from app.contracts.base import ApiModel
from app.contracts.requests._fields import IdField


class RequestHintRequest(ApiModel):
    player_id: IdField
