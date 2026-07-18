from dataclasses import dataclass

from ai_content.models import CandidateClue, CandidateSuspect, CaseCandidate

from app.application.ports import AssistantHint, StageOutcome


def make_candidate(
    *, culprit_name: str = "Suspect A", num_suspects: int = 3, num_clues: int = 3
) -> CaseCandidate:
    """A synthetic but structurally valid CaseCandidate — passes
    CaseConsistencyPolicy once converted to a DetectiveCase (unique ids,
    exactly one culprit, enough suspects/clues)."""
    suspects = tuple(
        CandidateSuspect(
            suspect_id=f"suspect_{i}",
            name=f"Suspect {chr(65 + i)}",
            role=f"Role {i}",
            public_statement=f"Statement {i} that is definitely long enough to pass validation.",
            private_reasoning="",
            is_culprit=(f"Suspect {chr(65 + i)}" == culprit_name),
        )
        for i in range(num_suspects)
    )
    clues = tuple(CandidateClue(clue_id=f"clue_{i}", text=f"Clue text number {i}.") for i in range(num_clues))
    return CaseCandidate(
        title="Test Case Title",
        setting="A test setting.",
        problem="A test problem.",
        suspects=suspects,
        clues=clues,
        solution_explanation="A sufficiently detailed test explanation.",
        difficulty="easy",
    )


@dataclass
class AttemptScript:
    """One attempt's scripted outcome for FakeCaseGenerationAdapter."""

    generation_passes: bool = True
    logic_passes: bool = True
    safety_passes: bool = True
    candidate: CaseCandidate | None = None
    prompt_tokens: int = 10
    completion_tokens: int = 5


class FakeCaseGenerationAdapter:
    """Hand-rolled test double, matching FakeHintAssistant's style below —
    no mocking package. Scriptable per-attempt: a list of AttemptScript
    drives what generate_raw_candidate/check_logic_consistency/check_safety
    return on the Nth attempt, so a test can construct exact scenarios
    (e.g. "attempt 1 fails logic, attempt 2 fails safety, attempt 3
    passes") without any real OpenAI call."""

    def __init__(self, scripts: list[AttemptScript] | None = None) -> None:
        self.scripts = scripts or [AttemptScript()]
        self.generate_calls = 0
        self.logic_calls = 0
        self.safety_calls = 0
        self._current_script: AttemptScript | None = None

    def generate_raw_candidate(self) -> tuple[CaseCandidate | None, StageOutcome]:
        script = self.scripts[min(self.generate_calls, len(self.scripts) - 1)]
        self.generate_calls += 1
        self._current_script = script
        if not script.generation_passes:
            return None, StageOutcome(
                passed=False,
                reasons=("scripted generation failure",),
                prompt_tokens=script.prompt_tokens,
                completion_tokens=script.completion_tokens,
            )
        candidate = script.candidate or make_candidate()
        return candidate, StageOutcome(
            passed=True,
            reasons=(),
            prompt_tokens=script.prompt_tokens,
            completion_tokens=script.completion_tokens,
        )

    def check_logic_consistency(self, candidate: CaseCandidate) -> StageOutcome:
        self.logic_calls += 1
        script = self._current_script
        if script is None or not script.logic_passes:
            return StageOutcome(passed=False, reasons=("scripted logic rejection",))
        return StageOutcome(passed=True, reasons=())

    def check_safety(self, candidate: CaseCandidate) -> StageOutcome:
        self.safety_calls += 1
        script = self._current_script
        if script is None or not script.safety_passes:
            return StageOutcome(passed=False, reasons=("scripted safety rejection",))
        return StageOutcome(passed=True, reasons=())

    def assign_difficulty(self, candidate: CaseCandidate) -> str:
        return candidate.difficulty or "medium"


class FakeHintAssistant:
    """Hand-rolled test double — avoids a mocking package for one small interface.

    Shared between tests/unit (use-case orchestration tests) and
    tests/contract (so contract tests never hit the real OpenAI API, even
    if a real OPENAI_API_KEY happens to be present in the environment
    running the tests — test behavior and cost must not depend on that).
    """

    def __init__(self, hint: AssistantHint | None = None) -> None:
        self.hint = hint
        self.calls = 0
        self.last_public_case = None
        self.last_hint_level: int | None = None

    def generate_hint(self, public_case, hint_level):
        self.calls += 1
        self.last_public_case = public_case
        self.last_hint_level = hint_level
        return self.hint
