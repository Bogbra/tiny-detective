"""Interfaces for the AI-based evaluation stages (Logic Consistency, Safety).

The project spec's strategic goal names "AI and rule-based evaluators" — these two
are the AI-judged ones (semantic checks: solvability, plausibility, safety
nuance), unlike the purely structural schema/rule checks. Kept behind
Protocols so tests can inject fakes instead of calling the real API — same
pattern as the backend's repository ports (services/api/app/application/ports.py).
"""

from dataclasses import dataclass
from typing import Protocol

from .models import CaseCandidate


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    passed: bool
    reasons: tuple[str, ...] = ()


class SafetyEvaluator(Protocol):
    def evaluate(self, candidate: CaseCandidate) -> EvaluationResult: ...


class LogicConsistencyEvaluator(Protocol):
    def evaluate(self, candidate: CaseCandidate) -> EvaluationResult: ...
