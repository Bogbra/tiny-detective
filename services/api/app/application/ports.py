"""Repository and AI-assistant interfaces the application layer depends on.

Repositories are backed by Firestore when configured (Phase 7,
app/infrastructure/firestore), in-memory otherwise (app/infrastructure/repositories)
— see app/api/dependencies.py for the selection. HintAssistant is implemented
against OpenAI (app/infrastructure/ai); tests use hand-rolled fakes — same
port/adapter pattern throughout this project.
"""

from dataclasses import dataclass
from typing import Protocol

from app.domain.entities.attempt import Attempt
from app.domain.entities.detective_case import DetectiveCase
from app.domain.entities.hint_request import HintRequest
from app.domain.entities.player import Player
from app.domain.entities.public_views import PublicDetectiveCase
from app.domain.value_objects.case_id import CaseId


class CaseRepository(Protocol):
    def get(self, case_id: CaseId) -> DetectiveCase | None: ...
    def get_daily(self) -> DetectiveCase | None: ...
    def set_daily(self, case_id: CaseId) -> None: ...
    def save(self, case: DetectiveCase) -> None: ...
    def list_all(self) -> list[DetectiveCase]: ...


class PlayerRepository(Protocol):
    def get(self, player_id: str) -> Player | None: ...
    def save(self, player: Player) -> None: ...


class HintRequestRepository(Protocol):
    def count_for_case(self, case_id: CaseId, player_id: str) -> int: ...
    def record(self, hint_request: HintRequest) -> None: ...


class AttemptRepository(Protocol):
    def record(self, attempt: Attempt) -> None: ...


@dataclass(frozen=True, slots=True)
class AssistantHint:
    clue_id: str
    commentary: str


class HintAssistant(Protocol):
    def generate_hint(
        self, public_case: PublicDetectiveCase, hint_level: int
    ) -> AssistantHint | None:
        """Returns None on any failure (no key, network error, malformed
        response) — the caller falls back to a deterministic hint rather
        than erroring the request. public_case never contains the solution
        or private suspect fields (see PublicDetectiveCase); the assistant
        physically cannot leak what it was never told."""
        ...
