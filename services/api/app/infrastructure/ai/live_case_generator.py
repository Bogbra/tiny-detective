"""Adapter wrapping the reused tools/ai-content pipeline stages (see
ADR-0007) behind CaseGenerationAdapter, at the per-step granularity the
live-generation SSE feature needs — one call per visible step, unlike
ai_content.pipeline.CaseGenerationPipeline's single all-or-nothing
process(). This is the ONLY place in services/api that imports ai_content.*
directly.

generate_raw_candidate() uses the deterministic-logic pipeline
(ai_content.logic_builder + ai_content.generator.CaseProseRenderer), not the
original single-shot OpenAICaseGenerator — a real, measured pass-rate fix
(32.5% across two real 20-run batches, up from ~5%), not a reimplementation
of the old approach. See ADR-0007's redesign addendum. The original
generator is untouched and still used by the offline/curated content tool
(tools/ai-content/generate_cases.py) — this adapter is the only thing that
changed.

check_logic_consistency() uses evaluate_case_logic_v3.md, not the default
v2 — v3 is calibrated for this pipeline's guaranteed-by-construction
deduction pattern (a narrower "narrative fairness" check, not a from-scratch
re-derivation of solvability that real testing showed the model couldn't
reliably perform even with an explicit worked example). check_safety() is
unchanged — prose safety is an orthogonal concern from logic and still needs
real judgment either way.

Any unexpected failure (network error, missing API key, malformed judge
response) is caught broadly and converted into a failed StageOutcome rather
than propagating — same "a system boundary degrades gracefully rather than
erroring the request" discipline as ai_hint_assistant.py. The retry loop in
GenerateCase (application layer) treats this identically to a genuine judge
rejection; after max attempts it reports "could not generate a valid case",
which is honest even if the underlying cause was an outage rather than
content quality.
"""

import random

from ai_content.difficulty_evaluator import assign_difficulty as _assign_difficulty
from ai_content.generator import CaseProseRenderer, GenerationError, PromptFidelityError
from ai_content.logic_builder import build_case_logic
from ai_content.models import CaseCandidate
from ai_content.openai_client import MissingApiKeyError
from ai_content.openai_evaluators import OpenAILogicConsistencyEvaluator, OpenAISafetyEvaluator
from ai_content.rule_validator import validate_rules

from app.application.ports import StageOutcome

_EMPTY_USAGE = {"prompt_tokens": 0, "completion_tokens": 0}
_LOGIC_JUDGE_PROMPT_FILE = "evaluate_case_logic_v3.md"


class LiveCaseGenerator:
    def __init__(self) -> None:
        # Lazily constructed on first use — none of these do network I/O in
        # __init__ (confirmed in ai_content.generator/openai_evaluators),
        # but matching this project's construct-on-first-use discipline
        # throughout (see ADR-0005's addendum) costs nothing and stays
        # consistent with every other adapter.
        self._renderer: CaseProseRenderer | None = None
        self._logic_evaluator: OpenAILogicConsistencyEvaluator | None = None
        self._safety_evaluator: OpenAISafetyEvaluator | None = None

    def _get_renderer(self) -> CaseProseRenderer:
        if self._renderer is None:
            self._renderer = CaseProseRenderer()
        return self._renderer

    def _get_logic_evaluator(self) -> OpenAILogicConsistencyEvaluator:
        if self._logic_evaluator is None:
            self._logic_evaluator = OpenAILogicConsistencyEvaluator(prompt_file=_LOGIC_JUDGE_PROMPT_FILE)
        return self._logic_evaluator

    def _get_safety_evaluator(self) -> OpenAISafetyEvaluator:
        if self._safety_evaluator is None:
            self._safety_evaluator = OpenAISafetyEvaluator()
        return self._safety_evaluator

    def generate_raw_candidate(self) -> tuple[CaseCandidate | None, StageOutcome]:
        renderer = self._get_renderer()
        # build_case_logic never fails (verified offline across 1000 random
        # seeds — see tests/test_logic_builder.py's fuzz test) — the only
        # thing that can go wrong from here on is the LLM rendering step.
        case_logic = build_case_logic(random)

        try:
            candidate = renderer.render(case_logic)
        except PromptFidelityError as exc:
            usage = renderer.last_usage or _EMPTY_USAGE
            return None, StageOutcome(
                passed=False,
                reasons=exc.reasons,
                prompt_tokens=usage["prompt_tokens"],
                completion_tokens=usage["completion_tokens"],
            )
        except (GenerationError, MissingApiKeyError) as exc:
            return None, StageOutcome(passed=False, reasons=(str(exc),))
        except Exception:
            return None, StageOutcome(passed=False, reasons=("case generation service failed",))

        usage = renderer.last_usage or _EMPTY_USAGE

        rule_result = validate_rules(candidate)
        if not rule_result.passed:
            return None, StageOutcome(
                passed=False,
                reasons=rule_result.reasons,
                prompt_tokens=usage["prompt_tokens"],
                completion_tokens=usage["completion_tokens"],
            )

        return candidate, StageOutcome(
            passed=True,
            reasons=(),
            prompt_tokens=usage["prompt_tokens"],
            completion_tokens=usage["completion_tokens"],
        )

    def check_logic_consistency(self, candidate: CaseCandidate) -> StageOutcome:
        evaluator = self._get_logic_evaluator()
        try:
            result = evaluator.evaluate(candidate)
        except Exception:
            return StageOutcome(passed=False, reasons=("logic evaluation service failed",))
        usage = evaluator.last_usage or _EMPTY_USAGE
        return StageOutcome(
            passed=result.passed,
            reasons=result.reasons,
            prompt_tokens=usage["prompt_tokens"],
            completion_tokens=usage["completion_tokens"],
        )

    def check_safety(self, candidate: CaseCandidate) -> StageOutcome:
        evaluator = self._get_safety_evaluator()
        try:
            result = evaluator.evaluate(candidate)
        except Exception:
            return StageOutcome(passed=False, reasons=("safety evaluation service failed",))
        usage = evaluator.last_usage or _EMPTY_USAGE
        return StageOutcome(
            passed=result.passed,
            reasons=result.reasons,
            prompt_tokens=usage["prompt_tokens"],
            completion_tokens=usage["completion_tokens"],
        )

    def assign_difficulty(self, candidate: CaseCandidate) -> str:
        return _assign_difficulty(candidate)
