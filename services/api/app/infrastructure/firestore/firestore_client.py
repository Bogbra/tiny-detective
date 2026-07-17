"""Firestore client setup.

The official google-cloud-firestore client automatically connects to the
local emulator instead of real GCP if FIRESTORE_EMULATOR_HOST is set — no
special-casing needed here beyond reading that env var to decide whether
Firestore-backed repositories should be wired up at all (see
app/api/dependencies.py, same graceful-degradation pattern as OPENAI_API_KEY:
unconfigured means "use the in-memory fallback", not an error).
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google.cloud import firestore

# Loads services/api/.env if present; a no-op otherwise.
load_dotenv(Path(__file__).resolve().parents[3] / ".env")

DEFAULT_PROJECT = "tiny-detective-dev"


def is_firestore_configured() -> bool:
    """False whenever running under pytest, regardless of .env — app-level
    dependency wiring (app/api/dependencies.py) must never silently pick
    Firestore over the in-memory fallback just because a real .env happens
    to exist on the machine running the tests. Same class of bug the OpenAI
    client's pytest guard exists for (see openai_client.py in both this
    package and tools/ai-content), adapted for the fact that repositories
    are constructed eagerly at import time here.

    Checks `"pytest" in sys.modules`, NOT `PYTEST_CURRENT_TEST` — the latter
    is only set while an individual test is executing, not during pytest's
    collection phase, when this module already gets imported transitively
    (via app.main -> routes -> dependencies). Using PYTEST_CURRENT_TEST here
    first caused dependencies.py to attempt a real connection to a stopped
    emulator during collection, which hung the whole suite for ~45s instead
    of failing fast or falling back — measured, not assumed. `sys.modules`
    is populated the moment pytest itself starts, before collection.

    Deliberate real-Firestore integration tests (tests/integration/) are
    unaffected: they construct FirestoreCaseRepository etc. directly with
    their own client, they don't go through this function or the app's
    dependency-injection singletons at all.
    """
    if "pytest" in sys.modules:
        return False
    return bool(
        os.environ.get("FIRESTORE_EMULATOR_HOST") or os.environ.get("GOOGLE_CLOUD_PROJECT")
    )


def get_firestore_client() -> firestore.Client:
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", DEFAULT_PROJECT)
    return firestore.Client(project=project)
