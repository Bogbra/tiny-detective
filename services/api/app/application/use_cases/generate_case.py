"""Live, on-demand case generation — a deliberate, scoped exception to "no
unvetted AI case reaches players" (see ADR-0007). Opt-in (a player clicks a
button), still gated by both real AI judges plus a domain-level consistency
check, capped by a global daily budget, and every result is stored with
source="live_generated" so it's distinguishable from curated content. The
actual daily case (GetDailyCase) is never touched by this.
"""

import asyncio
import logging
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import date, datetime, timezone

from app.application.ports import CaseGenerationAdapter, CaseRepository, DailyGenerationQuotaRepository
from app.domain.entities.clue import Clue
from app.domain.entities.detective_case import DetectiveCase
from app.domain.entities.public_views import PublicDetectiveCase
from app.domain.entities.solution import Solution
from app.domain.entities.suspect import Suspect
from app.domain.policies.case_consistency_policy import CaseConsistencyPolicy
from app.domain.value_objects.case_id import CaseId
from app.domain.value_objects.difficulty import Difficulty
from app.domain.value_objects.publish_status import PublishStatus

logger = logging.getLogger(__name__)

# Revised again after the redesign in ADR-0007's second addendum: the
# original single-shot LLM pipeline topped out at a real ~5-10% first-attempt
# pass rate (root cause: the model inventing a solution it didn't actually
# verify against its own clues), which is why this used to be 10. That
# pipeline has been replaced for this feature by a deterministic-logic +
# LLM-prose-rendering pipeline (ai_content.logic_builder +
# generator.CaseProseRenderer) — the deduction itself is now guaranteed
# correct by a Python constraint solver before any LLM call happens, so the
# LLM's only remaining job is prose, and its only remaining failure modes are
# rendering compliance (dropping a required phrase — caught by a cheap local
# fidelity check with no extra API call) and narrative fairness (an innocent
# suspect's flavor text implying a second motive — caught by a narrowed AI
# judge, evaluate_case_logic_v3.md). Real measured pass rate: 32.5% across
# two independent 20-run batches (7/20, 6/20) against the real OpenAI API —
# roughly 6.5x the old rate, at essentially the same per-attempt cost
# (~$0.0007-0.0015). At this rate 5 attempts already clears ~86% eventual
# success (1 - 0.675^5) with a much tighter worst-case wait than the old
# 10-attempt budget needed — lowered accordingly, not left high out of
# habit now that the underlying quality problem is actually fixed.
MAX_ATTEMPTS_PER_REQUEST = 5

QUOTA_EXCEEDED_DETAIL = "daily generation quota reached"


@dataclass(frozen=True, slots=True)
class GenerationEvent:
    step: str  # "quota_check" | "generating" | "logic_check" | "safety_check" | "saving" | "failed"
    status: str  # "running" | "passed" | "rejected" | "done"
    detail: str | None = None
    attempt: int | None = None
    case: PublicDetectiveCase | None = None


class GenerateCase:
    def __init__(
        self,
        case_generation_adapter: CaseGenerationAdapter,
        case_repository: CaseRepository,
        quota_repository: DailyGenerationQuotaRepository,
        max_attempts: int = MAX_ATTEMPTS_PER_REQUEST,
        consistency_policy: CaseConsistencyPolicy | None = None,
    ) -> None:
        self._adapter = case_generation_adapter
        self._case_repository = case_repository
        self._quota_repository = quota_repository
        self._max_attempts = max_attempts
        self._consistency_policy = consistency_policy or CaseConsistencyPolicy()

    async def execute(self, today: date) -> AsyncIterator[GenerationEvent]:
        # Pre-check: fail fast with zero LLM calls if the day's budget is
        # already gone — no point opening a 15-30s stream just to reject it
        # at the end. `today` is always caller-supplied (see module
        # docstring) — never computed here.
        if self._quota_repository.get_status(today).exhausted:
            yield GenerationEvent(step="quota_check", status="rejected", detail=QUOTA_EXCEEDED_DETAIL)
            return

        prompt_tokens = 0
        completion_tokens = 0

        for attempt in range(1, self._max_attempts + 1):
            reserved = await asyncio.to_thread(self._quota_repository.try_reserve_attempt, today)
            if not reserved:
                # The cost-backstop cap (not the product-facing success
                # cap) was hit mid-loop — same user-facing message either
                # way, see ADR-0007 on why that detail isn't exposed.
                yield GenerationEvent(
                    step="quota_check", status="rejected", detail=QUOTA_EXCEEDED_DETAIL, attempt=attempt
                )
                return

            yield GenerationEvent(step="generating", status="running", attempt=attempt)
            candidate, gen_outcome = await asyncio.to_thread(self._adapter.generate_raw_candidate)
            prompt_tokens += gen_outcome.prompt_tokens
            completion_tokens += gen_outcome.completion_tokens
            if candidate is None:
                yield GenerationEvent(
                    step="generating",
                    status="rejected",
                    detail="; ".join(gen_outcome.reasons) or "generation failed",
                    attempt=attempt,
                )
                continue
            yield GenerationEvent(step="generating", status="passed", attempt=attempt)

            yield GenerationEvent(step="logic_check", status="running", attempt=attempt)
            logic_outcome = await asyncio.to_thread(self._adapter.check_logic_consistency, candidate)
            prompt_tokens += logic_outcome.prompt_tokens
            completion_tokens += logic_outcome.completion_tokens
            if not logic_outcome.passed:
                yield GenerationEvent(
                    step="logic_check", status="rejected", detail="; ".join(logic_outcome.reasons), attempt=attempt
                )
                continue

            # The domain-level CaseConsistencyPolicy rides along inside this
            # same visible step — pure, no I/O, effectively free — as
            # defense-in-depth on top of the AI judge rather than a fourth
            # visible SSE step the user didn't ask for. See ADR-0007.
            detective_case = self._to_detective_case(candidate)
            violations = self._consistency_policy.check(detective_case)
            if violations:
                yield GenerationEvent(
                    step="logic_check", status="rejected", detail="; ".join(violations), attempt=attempt
                )
                continue
            yield GenerationEvent(step="logic_check", status="passed", attempt=attempt)

            yield GenerationEvent(step="safety_check", status="running", attempt=attempt)
            safety_outcome = await asyncio.to_thread(self._adapter.check_safety, candidate)
            prompt_tokens += safety_outcome.prompt_tokens
            completion_tokens += safety_outcome.completion_tokens
            if not safety_outcome.passed:
                yield GenerationEvent(
                    step="safety_check", status="rejected", detail="; ".join(safety_outcome.reasons), attempt=attempt
                )
                continue
            yield GenerationEvent(step="safety_check", status="passed", attempt=attempt)

            yield GenerationEvent(step="saving", status="running", attempt=attempt)
            consumed = await asyncio.to_thread(self._quota_repository.try_consume_success, today)
            if not consumed:
                # Lost a race for the last slot even though this candidate
                # passed everything — the atomic check, not the earlier
                # pre-check, is the real gate. Rare; not saved either way.
                self._log_usage(prompt_tokens, completion_tokens, outcome="quota_lost_at_save")
                yield GenerationEvent(
                    step="saving", status="rejected", detail=QUOTA_EXCEEDED_DETAIL, attempt=attempt
                )
                return

            await asyncio.to_thread(self._case_repository.save, detective_case)
            self._log_usage(prompt_tokens, completion_tokens, outcome="saved", case_id=detective_case.case_id.value)
            yield GenerationEvent(
                step="saving", status="done", attempt=attempt, case=detective_case.public_view()
            )
            return

        self._log_usage(prompt_tokens, completion_tokens, outcome="exhausted")
        yield GenerationEvent(
            step="failed",
            status="done",
            detail=f"could not generate a valid case after {self._max_attempts} attempts",
        )

    def _to_detective_case(self, candidate) -> DetectiveCase:
        culprit = next(s for s in candidate.suspects if s.is_culprit)
        difficulty_value = candidate.difficulty or self._adapter.assign_difficulty(candidate)
        suspects = tuple(
            Suspect(
                suspect_id=s.suspect_id,
                name=s.name,
                role=s.role,
                public_statement=s.public_statement,
                is_culprit=s.is_culprit,
                private_reasoning=s.private_reasoning or None,
            )
            for s in candidate.suspects
        )
        clues = tuple(Clue(clue_id=c.clue_id, text=c.text) for c in candidate.clues)
        solution = Solution(culprit_suspect_id=culprit.suspect_id, explanation=candidate.solution_explanation)
        now = datetime.now(timezone.utc)
        return DetectiveCase(
            case_id=CaseId(f"case_live_{uuid.uuid4().hex[:12]}"),
            title=candidate.title,
            setting=candidate.setting,
            problem=candidate.problem,
            suspects=suspects,
            clues=clues,
            solution=solution,
            difficulty=Difficulty(difficulty_value),
            status=PublishStatus.LIVE,
            source="live_generated",
            created_at=now,
            updated_at=now,
        )

    def _log_usage(
        self, prompt_tokens: int, completion_tokens: int, *, outcome: str, case_id: str | None = None
    ) -> None:
        # gpt-4o-mini list pricing, same constants as evaluate_cases.py —
        # verify against https://openai.com/api/pricing/ before trusting.
        cost_usd = prompt_tokens / 1_000_000 * 0.15 + completion_tokens / 1_000_000 * 0.60
        logger.info(
            "case_generation outcome=%s prompt_tokens=%d completion_tokens=%d cost_usd=%.5f case_id=%s",
            outcome,
            prompt_tokens,
            completion_tokens,
            cost_usd,
            case_id,
        )
