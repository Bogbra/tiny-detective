from dataclasses import dataclass
from datetime import datetime

from app.domain.entities.clue import Clue
from app.domain.entities.public_views import PublicDetectiveCase
from app.domain.entities.solution import Solution
from app.domain.entities.suspect import Suspect
from app.domain.value_objects.case_id import CaseId
from app.domain.value_objects.difficulty import Difficulty
from app.domain.value_objects.publish_status import PublishStatus


@dataclass(frozen=True, slots=True)
class DetectiveCase:
    case_id: CaseId
    title: str
    setting: str
    problem: str
    suspects: tuple[Suspect, ...]
    clues: tuple[Clue, ...]
    solution: Solution
    difficulty: Difficulty
    locale: str = "en"
    status: PublishStatus = PublishStatus.DRAFT
    created_at: datetime | None = None
    updated_at: datetime | None = None
    # "curated" (hand-authored or offline-generated-then-approved, the only
    # kind that existed before this field) vs "live_generated" (the Phase 8
    # on-demand generation feature — see ADR-0007). Exposed publicly so the
    # distinction is transparent to players, not just an internal audit
    # trail.
    source: str = "curated"

    def public_view(self) -> PublicDetectiveCase:
        return PublicDetectiveCase(
            case_id=self.case_id.value,
            title=self.title,
            setting=self.setting,
            problem=self.problem,
            suspects=tuple(suspect.public_view() for suspect in self.suspects),
            clues=tuple(clue.public_view() for clue in self.clues),
            difficulty=self.difficulty.value,
            source=self.source,
        )
