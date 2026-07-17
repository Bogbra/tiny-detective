"""Orchestrates the full pipeline in the exact order from the project spec's
"AI Case Generation Pipeline":

    generation -> schema validation -> rule-based validation
    -> logic consistency evaluation -> safety evaluation
    -> difficulty evaluation -> draft storage -> approval -> publishing

Generation happens before process() is called (see generate_cases.py) — this
class starts at schema validation. Approval/publishing are Phase 7 concerns
(they need a real backend repository to operate on).
"""

from dataclasses import dataclass
from pathlib import Path

from .difficulty_evaluator import assign_difficulty
from .draft_store import DraftStore
from .evaluators import LogicConsistencyEvaluator, SafetyEvaluator
from .rule_validator import validate_rules
from .schema_parser import SchemaValidationError, parse_case_candidate


@dataclass(frozen=True, slots=True)
class PipelineResult:
    accepted: bool
    stage_failed: str | None
    reasons: tuple[str, ...]
    draft_path: Path | None = None


class CaseGenerationPipeline:
    def __init__(
        self,
        *,
        safety_evaluator: SafetyEvaluator,
        logic_evaluator: LogicConsistencyEvaluator,
        draft_store: DraftStore | None = None,
    ) -> None:
        self._safety_evaluator = safety_evaluator
        self._logic_evaluator = logic_evaluator
        self._draft_store = draft_store or DraftStore()

    def process(
        self,
        raw_candidate: object,
        *,
        model: str | None = None,
        generator_prompt_version: str | None = None,
    ) -> PipelineResult:
        try:
            candidate = parse_case_candidate(raw_candidate)
        except SchemaValidationError as exc:
            return PipelineResult(accepted=False, stage_failed="schema", reasons=tuple(exc.reasons))

        rule_result = validate_rules(candidate)
        if not rule_result.passed:
            return PipelineResult(accepted=False, stage_failed="rules", reasons=rule_result.reasons)

        logic_result = self._logic_evaluator.evaluate(candidate)
        if not logic_result.passed:
            return PipelineResult(accepted=False, stage_failed="logic", reasons=logic_result.reasons)

        safety_result = self._safety_evaluator.evaluate(candidate)
        if not safety_result.passed:
            return PipelineResult(accepted=False, stage_failed="safety", reasons=safety_result.reasons)

        difficulty = candidate.difficulty or assign_difficulty(candidate)
        draft_path = self._draft_store.save(
            candidate,
            difficulty=difficulty,
            model=model,
            generator_prompt_version=generator_prompt_version,
            # Read directly off the evaluator instances actually used to judge
            # this candidate, rather than trusting the caller to pass the
            # right version string — the evaluator is the source of truth for
            # which prompt it used. Fakes without a `prompt_version` attribute
            # (e.g. in tests) just record None.
            logic_prompt_version=getattr(self._logic_evaluator, "prompt_version", None),
            safety_prompt_version=getattr(self._safety_evaluator, "prompt_version", None),
        )
        return PipelineResult(accepted=True, stage_failed=None, reasons=(), draft_path=draft_path)
