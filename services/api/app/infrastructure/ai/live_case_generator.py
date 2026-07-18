"""Adapter wrapping the reused tools/ai-content pipeline stages (see
ADR-0007) behind CaseGenerationAdapter, at the per-step granularity the
live-generation SSE feature needs — one call per visible step, unlike
ai_content.pipeline.CaseGenerationPipeline's single all-or-nothing
process(). This is the ONLY place in services/api that imports ai_content.*
directly.

Any unexpected failure (network error, missing API key, malformed judge
response) is caught broadly and converted into a failed StageOutcome rather
than propagating — same "a system boundary degrades gracefully rather than
erroring the request" discipline as ai_hint_assistant.py. The retry loop in
GenerateCase (application layer) treats this identically to a genuine judge
rejection; after max attempts it reports "could not generate a valid case",
which is honest even if the underlying cause was an outage rather than
content quality.
"""

from ai_content.difficulty_evaluator import assign_difficulty as _assign_difficulty
from ai_content.generator import GenerationError, OpenAICaseGenerator
from ai_content.models import CaseCandidate
from ai_content.openai_client import MissingApiKeyError
from ai_content.openai_evaluators import OpenAILogicConsistencyEvaluator, OpenAISafetyEvaluator
from ai_content.rule_validator import validate_rules
from ai_content.schema_parser import SchemaValidationError, parse_case_candidate

from app.application.ports import StageOutcome

_EMPTY_USAGE = {"prompt_tokens": 0, "completion_tokens": 0}


class LiveCaseGenerator:
    def __init__(self) -> None:
        # Lazily constructed on first use — none of these do network I/O in
        # __init__ (confirmed in ai_content.generator/openai_evaluators),
        # but matching this project's construct-on-first-use discipline
        # throughout (see ADR-0005's addendum) costs nothing and stays
        # consistent with every other adapter.
        self._generator: OpenAICaseGenerator | None = None
        self._logic_evaluator: OpenAILogicConsistencyEvaluator | None = None
        self._safety_evaluator: OpenAISafetyEvaluator | None = None

    def _get_generator(self) -> OpenAICaseGenerator:
        if self._generator is None:
            self._generator = OpenAICaseGenerator()
        return self._generator

    def _get_logic_evaluator(self) -> OpenAILogicConsistencyEvaluator:
        if self._logic_evaluator is None:
            self._logic_evaluator = OpenAILogicConsistencyEvaluator()
        return self._logic_evaluator

    def _get_safety_evaluator(self) -> OpenAISafetyEvaluator:
        if self._safety_evaluator is None:
            self._safety_evaluator = OpenAISafetyEvaluator()
        return self._safety_evaluator

    def generate_raw_candidate(self) -> tuple[CaseCandidate | None, StageOutcome]:
        generator = self._get_generator()
        try:
            raw = generator.generate()
        except (GenerationError, MissingApiKeyError) as exc:
            return None, StageOutcome(passed=False, reasons=(str(exc),))
        except Exception:
            return None, StageOutcome(passed=False, reasons=("case generation service failed",))

        usage = generator.last_usage or _EMPTY_USAGE

        try:
            candidate = parse_case_candidate(raw)
        except SchemaValidationError as exc:
            return None, StageOutcome(
                passed=False,
                reasons=tuple(exc.reasons),
                prompt_tokens=usage["prompt_tokens"],
                completion_tokens=usage["completion_tokens"],
            )

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
