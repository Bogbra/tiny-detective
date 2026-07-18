import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# Loads tools/ai-content/.env if present; a no-op if it doesn't exist. Never
# commit the real .env — see .env.example for what it should contain.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

OPENAI_API_KEY_ENV_VAR = "OPENAI_API_KEY"

# Without an explicit timeout, a hung upstream call blocks indefinitely.
# This client is used both by the offline batch scripts (generate_cases.py,
# evaluate_cases.py — where a long hang is merely annoying) AND, via the
# services/api editable path dependency, by the live /cases/generate SSE
# endpoint (CaseProseRenderer, both judges) — where a hung call stalls a
# real player's request and, worse, the whole retry loop behind it. 30s is
# generous for one call but bounded either way. max_retries=1 (not the SDK
# default of 2): the live-generation retry loop already retries whole
# attempts at a higher level (see services/api's GenerateCase) — retrying
# individual calls twice on top of that just compounds latency.
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_MAX_RETRIES = 1
TIMEOUT_ENV_VAR = "OPENAI_TIMEOUT_SECONDS"
MAX_RETRIES_ENV_VAR = "OPENAI_MAX_RETRIES"


def _timeout_seconds() -> float:
    raw = os.environ.get(TIMEOUT_ENV_VAR)
    if raw is None:
        return DEFAULT_TIMEOUT_SECONDS
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_TIMEOUT_SECONDS
    return value if value > 0 else DEFAULT_TIMEOUT_SECONDS


def _max_retries() -> int:
    raw = os.environ.get(MAX_RETRIES_ENV_VAR)
    if raw is None:
        return DEFAULT_MAX_RETRIES
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_MAX_RETRIES
    return value if value >= 0 else DEFAULT_MAX_RETRIES


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
    return OpenAI(api_key=api_key, timeout=_timeout_seconds(), max_retries=_max_retries())
