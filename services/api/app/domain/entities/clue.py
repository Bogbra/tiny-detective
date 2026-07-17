from dataclasses import dataclass

from app.domain.entities.public_views import PublicClue


@dataclass(frozen=True, slots=True)
class Clue:
    clue_id: str
    text: str
    relevance: str | None = None
    related_suspect_ids: tuple[str, ...] = ()
    unlock_order: int = 0

    def public_view(self) -> PublicClue:
        return PublicClue(clue_id=self.clue_id, text=self.text)
