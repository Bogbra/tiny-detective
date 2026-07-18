import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from app.application.errors import CaseNotFoundError, HintLimitExceededError, PlayerNotFoundError
from app.application.ports import CaseRepository, HintAssistant, HintRequestRepository, PlayerRepository
from app.domain.entities.detective_case import DetectiveCase
from app.domain.entities.hint_request import HintRequest
from app.domain.policies.hint_guardrail_policy import HintGuardrailPolicy
from app.domain.policies.hint_policy import HintPolicy
from app.domain.value_objects.case_id import CaseId

FALLBACK_HINT_TEXT = (
    "Compare each suspect's statement with the physical clues. One statement fits less well than the others."
)


@dataclass(frozen=True, slots=True)
class HintResult:
    text: str
    hints_used: int
    hints_remaining: int


@dataclass(frozen=True, slots=True)
class _GeneratedHint:
    text: str
    grounded_in_clue_ids: tuple[str, ...]
    passed_guardrails: bool


class RequestHint:
    def __init__(
        self,
        case_repository: CaseRepository,
        hint_request_repository: HintRequestRepository,
        hint_assistant: HintAssistant,
        player_repository: PlayerRepository,
        hint_policy: HintPolicy | None = None,
        guardrail_policy: HintGuardrailPolicy | None = None,
    ) -> None:
        self._case_repository = case_repository
        self._hint_request_repository = hint_request_repository
        self._hint_assistant = hint_assistant
        self._player_repository = player_repository
        self._hint_policy = hint_policy or HintPolicy()
        self._guardrail_policy = guardrail_policy or HintGuardrailPolicy()

    def execute(self, case_id: CaseId, player_id: str) -> HintResult:
        case = self._case_repository.get(case_id)
        if case is None:
            raise CaseNotFoundError(f"case '{case_id.value}' not found")

        # Without this check, any caller-supplied player_id (a fresh random
        # UUID they never registered via POST /players) gets its own brand
        # new hint-count budget — the per-case hint limit is trivially
        # bypassable by minting a new id per request. See task 2 of the
        # security/ops audit.
        if self._player_repository.get(player_id) is None:
            raise PlayerNotFoundError(f"player '{player_id}' not found")

        hints_used = self._hint_request_repository.count_for_case(case_id, player_id)
        if not self._hint_policy.can_request_hint(hints_used):
            raise HintLimitExceededError(f"hint limit of {self._hint_policy.max_hints} reached for this case")

        new_hints_used = hints_used + 1
        generated = self._generate_hint_content(case, new_hints_used)

        self._hint_request_repository.record(
            HintRequest(
                hint_request_id=str(uuid.uuid4()),
                case_id=case_id.value,
                player_id=player_id,
                level=new_hints_used,
                text=generated.text,
                grounded_in_clue_ids=generated.grounded_in_clue_ids,
                passed_guardrails=generated.passed_guardrails,
                created_at=datetime.now(UTC),
            )
        )

        return HintResult(
            text=generated.text,
            hints_used=new_hints_used,
            hints_remaining=self._hint_policy.remaining_hints(new_hints_used),
        )

    def _generate_hint_content(self, case: DetectiveCase, hint_level: int) -> _GeneratedHint:
        """AI Hint Flow, per the project spec: generate -> evaluate against guardrails
        -> return safe hint, or fall back. The AI only ever sees
        case.public_view() — it structurally cannot leak the solution or
        private suspect data because it was never given it.
        """
        public_case = case.public_view()
        assistant_hint = self._hint_assistant.generate_hint(public_case, hint_level)
        if assistant_hint is None:
            return _GeneratedHint(FALLBACK_HINT_TEXT, (), False)

        matching_clue = next((c for c in public_case.clues if c.clue_id == assistant_hint.clue_id), None)
        if matching_clue is None:
            # The assistant referenced a clue that doesn't exist in this case —
            # can't ground the hint in real case data, so don't trust it.
            return _GeneratedHint(FALLBACK_HINT_TEXT, (), False)

        # Guardrail the AI-generated commentary, passing along the specific
        # clue this hint is about — a role mention that's grounded in that
        # clue's own wording (e.g. "the visitor wristband") is quoting
        # already-public case content, not identifying anyone; a role
        # mention that isn't grounded there (e.g. "the curator's statement")
        # has no such excuse. See HintGuardrailPolicy's module docstring.
        guardrail_result = self._guardrail_policy.check(
            assistant_hint.commentary, case, referenced_clue_text=matching_clue.text
        )
        if not guardrail_result.passed:
            return _GeneratedHint(FALLBACK_HINT_TEXT, (), False)

        text = f'{assistant_hint.commentary} Take another look at: "{matching_clue.text}"'
        return _GeneratedHint(text, (matching_clue.clue_id,), True)
