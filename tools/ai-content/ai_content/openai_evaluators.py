import json
from pathlib import Path

from .evaluators import EvaluationResult
from .models import CaseCandidate, TokenUsage
from .openai_client import get_openai_client
from .prompts import load_prompt

DEFAULT_MODEL = "gpt-4o-mini"

# temperature=0.0 by default: these are gates, not creative writing. A judge
# that flips its verdict between runs on the same input isn't a reliable
# gate — see tools/ai-content/evaluate_cases.py, which measures exactly this
# (run each fixture multiple times and check for disagreement) rather than
# assuming temperature=0 alone guarantees determinism.
DEFAULT_TEMPERATURE = 0.0


def _candidate_to_json(candidate: CaseCandidate) -> dict:
    return {
        "title": candidate.title,
        "setting": candidate.setting,
        "problem": candidate.problem,
        "suspects": [
            {
                "name": s.name,
                "role": s.role,
                "publicStatement": s.public_statement,
                "privateReasoning": s.private_reasoning,
                "isCulprit": s.is_culprit,
            }
            for s in candidate.suspects
        ],
        "clues": [c.text for c in candidate.clues],
        "solutionExplanation": candidate.solution_explanation,
    }


def _judge(
    model: str, temperature: float, prompt_file: str, candidate: CaseCandidate, key: str
) -> tuple[EvaluationResult, TokenUsage | None]:
    client = get_openai_client()
    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": load_prompt(prompt_file)},
            {"role": "user", "content": json.dumps(_candidate_to_json(candidate))},
        ],
    )
    result_json = json.loads(response.choices[0].message.content)
    result = EvaluationResult(
        passed=bool(result_json.get(key, False)), reasons=tuple(result_json.get("reasons", []))
    )
    usage: TokenUsage | None = None
    if response.usage is not None:
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }
    return result, usage


class OpenAISafetyEvaluator:
    # v2: v1 rejected several golden cases for "implies theft of a harmless
    # object" / "suspect has a motive" — exactly what every case's solution
    # requires. v2 adds explicit accept/reject examples. See
    # docs/phase-reviews.md's Phase 5 entry for the before/after baseline.
    PROMPT_FILE = "evaluate_case_safety_v2.md"

    def __init__(self, model: str = DEFAULT_MODEL, temperature: float = DEFAULT_TEMPERATURE) -> None:
        self.model = model
        self.temperature = temperature
        self.prompt_version = Path(self.PROMPT_FILE).stem
        self.last_usage: TokenUsage | None = None

    def evaluate(self, candidate: CaseCandidate) -> EvaluationResult:
        result, usage = _judge(self.model, self.temperature, self.PROMPT_FILE, candidate, "safe")
        self.last_usage = usage
        return result


class OpenAILogicConsistencyEvaluator:
    # v2: v1's own example reason strings ("solution depends on information
    # not present in any clue or statement", "two suspects are equally
    # supported by the clues") were appearing verbatim, identically, across
    # completely unrelated case candidates — the judge was echoing the
    # prompt's illustrative examples instead of describing what it actually
    # found. v2 asks for candidate-specific reasons and shows what that
    # looks like. Found live in production: real rejection reasons were
    # checked across multiple different generated cases and were
    # character-for-character identical, which a genuinely case-specific
    # judgment would not produce.
    PROMPT_FILE = "evaluate_case_logic_v2.md"

    def __init__(self, model: str = DEFAULT_MODEL, temperature: float = DEFAULT_TEMPERATURE) -> None:
        self.model = model
        self.temperature = temperature
        self.prompt_version = Path(self.PROMPT_FILE).stem
        self.last_usage: TokenUsage | None = None

    def evaluate(self, candidate: CaseCandidate) -> EvaluationResult:
        result, usage = _judge(self.model, self.temperature, self.PROMPT_FILE, candidate, "consistent")
        self.last_usage = usage
        return result
