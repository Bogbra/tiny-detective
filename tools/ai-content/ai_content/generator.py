import json
from pathlib import Path

from .models import TokenUsage
from .openai_client import get_openai_client
from .prompts import load_prompt

DEFAULT_MODEL = "gpt-4o-mini"

# Unset previously meant the API default (~1.0) — high creative variance,
# which turned out to be a real cost, not a neutral choice: the live
# case-generation feature (services/api) measured a live production
# rejection rate far higher than a small pre-deployment sample suggested,
# and the SAME two logic-consistency failures every time ("solution depends
# on information not present in any clue", "two suspects equally
# supported"). Inspecting real generated candidates confirmed a genuine
# generator problem, not judge over-strictness: clues describing vague,
# unattributed sensory details ("a faint smell of vanilla") that
# solution.explanation then silently "matches" to the culprit — a fact
# introduced in the explanation, never actually in a clue. Lower
# temperature (less wandering) plus v2's explicit clue-authoring guidance
# are the fix — see ADR-0007's addendum and prompts/generate_case_v2.md.
DEFAULT_TEMPERATURE = 0.6


class GenerationError(Exception):
    pass


class OpenAICaseGenerator:
    """Generates raw case candidate JSON. Not responsible for validation,
    approval, or publishing — the pipeline (ai_content/pipeline.py) owns that.
    """

    # v2: v1's clue-authoring guidance was too easy to satisfy without
    # actually grounding the solution in the clues themselves — see
    # DEFAULT_TEMPERATURE's comment above for the full diagnosis.
    PROMPT_FILE = "generate_case_v2.md"

    def __init__(self, model: str = DEFAULT_MODEL, temperature: float = DEFAULT_TEMPERATURE) -> None:
        self.model = model
        self.temperature = temperature
        self.prompt_version = Path(self.PROMPT_FILE).stem
        # Populated after each generate() call — previously only the two
        # evaluators tracked this; the live case-generation feature
        # (services/api) needs real, measured per-request cost across the
        # WHOLE pipeline including the generator call, not just the judges.
        # See evaluate_cases.py for the established read-.last_usage-after
        # pattern this mirrors.
        self.last_usage: TokenUsage | None = None

    def generate(self, *, difficulty_hint: str | None = None) -> dict:
        client = get_openai_client()
        user_prompt = "Generate one new detective case." + (
            f" Target difficulty: {difficulty_hint}." if difficulty_hint else ""
        )
        response = client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": load_prompt(self.PROMPT_FILE)},
                {"role": "user", "content": user_prompt},
            ],
        )
        self.last_usage = None
        if response.usage is not None:
            self.last_usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        content = response.choices[0].message.content
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise GenerationError(f"model did not return valid JSON: {exc}") from exc
