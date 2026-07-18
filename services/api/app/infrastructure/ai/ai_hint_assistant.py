import json
from pathlib import Path

from app.application.ports import AssistantHint
from app.domain.entities.public_views import PublicDetectiveCase
from app.infrastructure.ai.openai_client import MissingApiKeyError, get_openai_client
from app.infrastructure.ai.prompt_loader import load_prompt

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TEMPERATURE = 0.0


class OpenAIHintAssistant:
    # v2: v1's blanket "never use a suspect's role" instruction, combined
    # with the guardrail also scanning roles, rejected a correctly-grounded
    # hint whose commentary used "visitor" — the clue's own wording ("a
    # visitor wristband"), not an accusation. v2 clarifies that using a
    # clue's own vocabulary is fine; only naming a role TO IDENTIFY a
    # suspect isn't. See docs/phase-reviews.md's Phase 6 entry.
    PROMPT_FILE = "generate_hint_v2.md"

    def __init__(self, model: str = DEFAULT_MODEL, temperature: float = DEFAULT_TEMPERATURE) -> None:
        self.model = model
        self.temperature = temperature
        self.prompt_version = Path(self.PROMPT_FILE).stem

    def generate_hint(self, public_case: PublicDetectiveCase, hint_level: int) -> AssistantHint | None:
        try:
            client = get_openai_client()
        except MissingApiKeyError:
            return None

        payload = {
            "title": public_case.title,
            "setting": public_case.setting,
            "problem": public_case.problem,
            "suspectStatements": [s.public_statement for s in public_case.suspects],
            "clues": [{"clueId": c.clue_id, "text": c.text} for c in public_case.clues],
            "hintLevel": hint_level,
        }

        # Any failure here — network, rate limit, malformed JSON, a response
        # missing the expected keys — degrades to the deterministic fallback
        # (see request_hint.py) rather than erroring the player's request.
        # This is a system boundary; broad exception handling is deliberate.
        try:
            response = client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": load_prompt(self.PROMPT_FILE)},
                    {"role": "user", "content": json.dumps(payload)},
                ],
            )
            parsed = json.loads(response.choices[0].message.content)
            clue_id = parsed["clueId"]
            commentary = parsed["commentary"]
        except Exception:
            return None

        if not isinstance(clue_id, str) or not isinstance(commentary, str):
            return None

        return AssistantHint(clue_id=clue_id, commentary=commentary)
