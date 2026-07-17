from ai_content.evaluators import EvaluationResult


class FakeSafetyEvaluator:
    """Hand-rolled test double — avoids a mocking package for one small interface."""

    def __init__(self, passed: bool = True, reasons: tuple[str, ...] = ()) -> None:
        self.passed = passed
        self.reasons = reasons
        self.calls = 0
        self.prompt_version = "fake-safety-v1"

    def evaluate(self, candidate) -> EvaluationResult:
        self.calls += 1
        return EvaluationResult(passed=self.passed, reasons=self.reasons)


class FakeLogicConsistencyEvaluator:
    def __init__(self, passed: bool = True, reasons: tuple[str, ...] = ()) -> None:
        self.passed = passed
        self.reasons = reasons
        self.calls = 0
        self.prompt_version = "fake-logic-v1"

    def evaluate(self, candidate) -> EvaluationResult:
        self.calls += 1
        return EvaluationResult(passed=self.passed, reasons=self.reasons)
