import json
from pathlib import Path

import pytest

EVALS_DIR = Path(__file__).resolve().parent.parent / "evals"


@pytest.fixture
def valid_raw_candidate() -> dict:
    """The museum-key golden case, in raw generator-output shape."""
    golden = json.loads((EVALS_DIR / "golden_cases.json").read_text())
    return next(c["candidate"] for c in golden if c["name"] == "museum_key")


@pytest.fixture
def golden_candidates() -> list[dict]:
    return json.loads((EVALS_DIR / "golden_cases.json").read_text())


@pytest.fixture
def invalid_candidates() -> list[dict]:
    return json.loads((EVALS_DIR / "invalid_cases.json").read_text())
