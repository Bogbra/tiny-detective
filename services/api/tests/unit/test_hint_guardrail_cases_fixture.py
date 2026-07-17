"""Runs tests/fixtures/hint_guardrail_cases.json through HintGuardrailPolicy —
the project-spec-named guardrail eval fixture, deterministic (no AI needed,
since the policy itself is pure Python). Kept as a standalone fixture file
rather than inline test parameters so the specific commentary/clue pairs
that motivated each guardrail refinement stay documented in one place.
"""

import json
from pathlib import Path

import pytest

from app.domain.policies.hint_guardrail_policy import HintGuardrailPolicy

FIXTURE_PATH = Path(__file__).resolve().parent.parent / "fixtures" / "hint_guardrail_cases.json"
CASES = json.loads(FIXTURE_PATH.read_text())


@pytest.mark.parametrize("case_data", CASES, ids=[c["name"] for c in CASES])
def test_hint_guardrail_case(case_data, make_case):
    case = make_case()

    result = HintGuardrailPolicy().check(
        case_data["commentary"], case, referenced_clue_text=case_data["referencedClueText"]
    )

    expected_passed = case_data["expected"] == "accept"
    assert result.passed is expected_passed, (
        f"{case_data['name']}: expected {'accept' if expected_passed else 'reject'}, "
        f"got {'accept' if result.passed else 'reject'} "
        f"(violated: {result.violated_identifiers})"
    )
