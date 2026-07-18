"""Repository and AI-assistant interfaces the application layer depends on.

Repositories are backed by Firestore when configured (Phase 7,
app/infrastructure/firestore), in-memory otherwise (app/infrastructure/repositories)
— see app/api/dependencies.py for the selection. HintAssistant is implemented
against OpenAI (app/infrastructure/ai); tests use hand-rolled fakes — same
port/adapter pattern throughout this project.
"""

from dataclasses import dataclass
from datetime import date
from typing import Protocol

from ai_content.models import CaseCandidate

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

    def exists_for(self, player_id: str, case_id: str) -> bool:
        """Whether this player has already submitted any attempt for this
        case — the real gate against score/streak farming via unlimited
        resubmission (see SubmitSolution). Existence, not correctness: even
        a wrong first attempt already spends the player's one scored shot,
        matching the "first attempt only" rule regardless of outcome."""
        ...


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


@dataclass(frozen=True, slots=True)
class StageOutcome:
    """One pipeline stage's verdict (generation+schema+rules, logic-judge,
    or safety-judge) — see live_case_generator.py. Token counts are zero for
    stages that made no OpenAI call (schema/rule failures on an
    already-generated candidate still report the generator's own tokens,
    since that call already happened regardless of the rejection)."""

    passed: bool
    reasons: tuple[str, ...]
    prompt_tokens: int = 0
    completion_tokens: int = 0


class CaseGenerationAdapter(Protocol):
    """Wraps the reused tools/ai-content pipeline stages (see ADR-0007) at
    the granularity the live-generation SSE feature needs — one call per
    visible step, unlike ai_content.pipeline.CaseGenerationPipeline's single
    all-or-nothing process(). Returns CaseCandidate (from ai_content.models,
    a pure dataclass with zero I/O of its own) rather than a duplicate
    services/api-local type — the whole point of the path dependency is not
    maintaining two shapes of the same thing.
    """

    def generate_raw_candidate(self) -> tuple[CaseCandidate | None, StageOutcome]:
        """Generates one candidate and runs it through schema + rule
        validation (both pure, non-AI — folded in here since neither is a
        separately visible SSE step). None candidate means any of the three
        failed; StageOutcome.reasons explains which."""
        ...

    def check_logic_consistency(self, candidate: CaseCandidate) -> StageOutcome: ...

    def check_safety(self, candidate: CaseCandidate) -> StageOutcome: ...

    def assign_difficulty(self, candidate: CaseCandidate) -> str:
        """Pure heuristic, no AI call, cannot fail — see
        ai_content.difficulty_evaluator.assign_difficulty."""
        ...


# successCount cap: the user-visible product budget (50 live-generated
# cases/day, globally, across all players — see ADR-0007). attemptCount cap:
# a separate, higher, non-user-facing cost backstop, so bounding only
# successes doesn't leave rejected-attempt spend structurally unbounded.
# Revised upward after live production data showed the real per-attempt
# pass rate is closer to 5-10% than the original 29% estimate (see
# generate_case.py's MAX_ATTEMPTS_PER_REQUEST comment and ADR-0007's
# addendum) — at that rate, 50 successes/day can realistically need
# several hundred to ~1000 attempts, and real measured per-attempt cost
# (~$0.0006) makes that trivial regardless (worst case ~$1.20/day at this
# cap, still well under the €10 budget alert). The cap exists to catch a
# genuine runaway, not to be the everyday bottleneck a too-low value would
# have made it.
DEFAULT_DAILY_SUCCESS_CAP = 50
DEFAULT_DAILY_ATTEMPT_CAP = 2000


@dataclass(frozen=True, slots=True)
class QuotaStatus:
    success_count: int
    success_cap: int
    attempt_count: int
    attempt_cap: int

    @property
    def exhausted(self) -> bool:
        return self.success_count >= self.success_cap or self.attempt_count >= self.attempt_cap


class DailyGenerationQuotaRepository(Protocol):
    """Backs the live case-generation feature's global daily budget (see
    ADR-0007) — two independent atomic counters per UTC calendar day, not
    one: successCount is the user-visible product quota (only cases that
    pass both AI judges count), attemptCount is a separate, higher,
    non-user-facing cap that's the real cost backstop (rejected candidates
    still cost tokens and would otherwise be unbounded). `today` is always
    caller-supplied, never computed inside an implementation — tests inject
    arbitrary dates instead of depending on wall-clock time.
    """

    def get_status(self, today: date) -> QuotaStatus: ...

    def try_reserve_attempt(self, today: date) -> bool:
        """Atomically increments attemptCount and returns True if under
        attempt_cap, else returns False without incrementing. Called once
        per pipeline attempt, before generation, as the cost backstop."""
        ...

    def try_consume_success(self, today: date) -> bool:
        """Atomically increments successCount and returns True if under
        success_cap, else returns False without incrementing. Called once,
        only after a candidate has passed every gate — the real race-safe
        check that decides whether the case actually gets saved."""
        ...
