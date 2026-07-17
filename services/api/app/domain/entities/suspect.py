from dataclasses import dataclass

from app.domain.entities.public_views import PublicSuspect


@dataclass(frozen=True, slots=True)
class Suspect:
    suspect_id: str
    name: str
    role: str
    public_statement: str
    is_culprit: bool
    private_reasoning: str | None = None
    personality: str | None = None

    def public_view(self) -> PublicSuspect:
        return PublicSuspect(
            suspect_id=self.suspect_id,
            name=self.name,
            role=self.role,
            public_statement=self.public_statement,
        )
