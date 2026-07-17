import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# Loads tools/ai-content/.env if present; a no-op if it doesn't exist. Never
# commit the real .env — see .env.example for what it should contain.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

OPENAI_API_KEY_ENV_VAR = "OPENAI_API_KEY"


class MissingApiKeyError(RuntimeError):
    pass


class RealApiClientInTestsError(RuntimeError):
    """A test tried to construct a real OpenAI client instead of injecting a
    fake. Doesn't affect generate_cases.py/evaluate_cases.py — those run as
    plain Python scripts that never import pytest, so sys.modules never
    contains it there."""


def get_openai_client() -> OpenAI:
    """Never log the key itself — only ever pass it straight to the SDK."""
    if "pytest" in sys.modules:
        raise RealApiClientInTestsError(
            "Refusing to construct a real OpenAI client during a pytest run. "
            "Inject a fake (tests/fakes.py) instead."
        )

    api_key = os.environ.get(OPENAI_API_KEY_ENV_VAR)
    if not api_key:
        raise MissingApiKeyError(
            f"{OPENAI_API_KEY_ENV_VAR} is not set. Put it in tools/ai-content/.env "
            "(copy .env.example) or export it before running the real generator "
            "or AI-based evaluators."
        )
    return OpenAI(api_key=api_key)
