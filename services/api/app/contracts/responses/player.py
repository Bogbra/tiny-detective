from app.contracts.base import ApiModel


class PlayerResponse(ApiModel):
    player_id: str
    display_name: str | None
    streak: int
    total_score: int
