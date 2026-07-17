from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class HintRequest:
    hint_request_id: str
    case_id: str
    player_id: str
    level: int
    text: str
    grounded_in_clue_ids: tuple[str, ...] = ()
    passed_guardrails: bool = False
    created_at: datetime | None = None
