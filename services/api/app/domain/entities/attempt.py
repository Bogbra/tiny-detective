from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Attempt:
    attempt_id: str
    player_id: str
    case_id: str
    selected_suspect_id: str
    correct: bool
    score: int
    hints_used: int
    created_at: datetime | None = None
