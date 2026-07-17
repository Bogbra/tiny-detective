from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Solution:
    culprit_suspect_id: str
    explanation: str
    required_clue_ids: tuple[str, ...] = ()
