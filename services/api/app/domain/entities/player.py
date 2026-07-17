from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Player:
    player_id: str
    display_name: str | None = None
    streak: int = 0
    total_score: int = 0
    created_at: datetime | None = None
    last_played_at: datetime | None = None
