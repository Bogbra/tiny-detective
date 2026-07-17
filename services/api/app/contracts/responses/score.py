from app.contracts.base import ApiModel


class ScoreResponse(ApiModel):
    player_id: str
    total_score: int
    streak: int
