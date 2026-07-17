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
    return OpenAI(api_key=api_key)
