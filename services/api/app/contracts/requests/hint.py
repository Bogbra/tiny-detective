from app.contracts.base import ApiModel


class RequestHintRequest(ApiModel):
    player_id: str
