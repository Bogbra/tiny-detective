import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# Loads services/api/.env if present; a no-op if it doesn't exist (e.g. in
# deployment, where env vars come from the platform). Also loaded by
# app/api/dependencies.py — calling it again here is redundant but harmless,
# and keeps this module independently usable (e.g. in isolation, in tests).
load_dotenv(Path(__file__).resolve().parents[3] / ".env")

OPENAI_API_KEY_ENV_VAR = "OPENAI_API_KEY"

# Without an explicit timeout, the SDK's own default effectively lets a
# hung upstream call block indefinitely (well past what any caller of this
# code can tolerate) — for the hint endpoint specifically, that pins a
# worker thread on a single synchronous request for however long OpenAI's
# connection stays open, degrading the whole service for everyone else on
# that instance, not just the one slow request. 30s is generous for a
# single chat completion call but still bounded. max_retries=1 (not the
# SDK default of 2): a hint request already has its own deterministic
# fallback on any failure (see ai_hint_assistant.py) — retrying twice
# before giving up just adds latency to a path that degrades gracefully
# anyway, for no real benefit.
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
    """A test tried to construct a real OpenAI client instead of injecting
    a fake. Contract tests silently making real network calls once a real
    .env happened to exist on the machine is exactly the failure mode this
    exists to make structurally impossible, not just documented against —
    see tests/contract/conftest.py and tests/fakes.py."""


def get_openai_client() -> OpenAI:
    """Never log the key itself — only ever pass it straight to the SDK."""
    if "pytest" in sys.modules:
        # Checks sys.modules, not PYTEST_CURRENT_TEST — the latter is only
        # set while an individual test executes, not during collection.
        # See firestore_client.py's is_firestore_configured() for a case
        # where that distinction actually mattered (a ~45s collection-time
        # hang, measured, not assumed); kept consistent here too.
        raise RealApiClientInTestsError(
            "Refusing to construct a real OpenAI client during a pytest run. "
            "Inject a fake (tests/fakes.py) instead of relying on a missing "
            "OPENAI_API_KEY to keep tests offline."
        )

    api_key = os.environ.get(OPENAI_API_KEY_ENV_VAR)
    if not api_key:
        raise MissingApiKeyError(f"{OPENAI_API_KEY_ENV_VAR} is not set.")
    return OpenAI(api_key=api_key, timeout=_timeout_seconds(), max_retries=_max_retries())
