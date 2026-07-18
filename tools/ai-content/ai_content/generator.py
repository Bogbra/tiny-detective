import json
from pathlib import Path

from .models import TokenUsage
from .openai_client import get_openai_client
from .prompts import load_prompt

DEFAULT_MODEL = "gpt-4o-mini"


class GenerationError(Exception):
    pass


class OpenAICaseGenerator:
    """Generates raw case candidate JSON. Not responsible for validation,
    approval, or publishing — the pipeline (ai_content/pipeline.py) owns that.
    """

    PROMPT_FILE = "generate_case_v1.md"

    def __init__(self, model: str = DEFAULT_MODEL) -> None:
        self.model = model
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
