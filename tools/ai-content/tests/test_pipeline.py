import json

from ai_content.draft_store import DraftStore
from ai_content.pipeline import CaseGenerationPipeline

from .fakes import FakeLogicConsistencyEvaluator, FakeSafetyEvaluator


def _pipeline(tmp_path, *, logic_passed=True, safety_passed=True):
    logic = FakeLogicConsistencyEvaluator(
        passed=logic_passed, reasons=() if logic_passed else ("not consistent",)
    )
    safety = FakeSafetyEvaluator(passed=safety_passed, reasons=() if safety_passed else ("not safe",))
    pipeline = CaseGenerationPipeline(
        safety_evaluator=safety,
        logic_evaluator=logic,
        draft_store=DraftStore(tmp_path / "drafts"),
    )
    return pipeline, logic, safety


def test_valid_candidate_is_accepted_and_stored_as_draft(tmp_path, valid_raw_candidate):
    pipeline, logic, safety = _pipeline(tmp_path)

    result = pipeline.process(
        valid_raw_candidate, model="gpt-4o-mini", generator_prompt_version="generate_case_v1"
    )

    assert result.accepted is True
    assert result.stage_failed is None
    assert result.draft_path is not None
    assert result.draft_path.exists()

    record = json.loads(result.draft_path.read_text())
    assert record["status"] == "draft"
    assert record["title"] == "The Missing Museum Key"
    assert record["model"] == "gpt-4o-mini"
    assert logic.calls == 1
    assert safety.calls == 1


def test_draft_records_which_prompt_version_judged_it(tmp_path, valid_raw_candidate):
    """Each evaluator's own prompt_version is recorded automatically —
    the caller doesn't have to (and can't accidentally mis-)report it."""
    pipeline, logic, safety = _pipeline(tmp_path)

    result = pipeline.process(
        valid_raw_candidate, model="gpt-4o-mini", generator_prompt_version="generate_case_v1"
    )

    record = json.loads(result.draft_path.read_text())
    assert record["promptVersions"] == {
        "generator": "generate_case_v1",
        "logic": logic.prompt_version,
        "safety": safety.prompt_version,
    }


def test_malformed_candidate_is_rejected_at_schema_stage_without_calling_evaluators(
    tmp_path, valid_raw_candidate
):
    broken = dict(valid_raw_candidate)
    del broken["solution"]
    pipeline, logic, safety = _pipeline(tmp_path)

    result = pipeline.process(broken)

    assert result.accepted is False
    assert result.stage_failed == "schema"
    assert result.draft_path is None
    assert logic.calls == 0
    assert safety.calls == 0
    assert not (tmp_path / "drafts").exists() or list((tmp_path / "drafts").glob("*.json")) == []


def test_unsafe_keyword_is_rejected_at_rules_stage_without_calling_evaluators(tmp_path, valid_raw_candidate):
    raw = dict(valid_raw_candidate)
    raw["problem"] = "A chef's knife went missing from the display case."
    pipeline, logic, safety = _pipeline(tmp_path)

    result = pipeline.process(raw)

    assert result.accepted is False
    assert result.stage_failed == "rules"
    assert result.draft_path is None
    assert logic.calls == 0
    assert safety.calls == 0


def test_ambiguous_case_is_rejected_at_logic_stage(tmp_path, valid_raw_candidate):
    pipeline, logic, safety = _pipeline(tmp_path, logic_passed=False)

    result = pipeline.process(valid_raw_candidate)

    assert result.accepted is False
    assert result.stage_failed == "logic"
    assert result.reasons == ("not consistent",)
    assert result.draft_path is None
    assert logic.calls == 1
    assert safety.calls == 0, "safety evaluator must not run once logic evaluation fails"


def test_hidden_only_solution_is_rejected_at_logic_stage(tmp_path, invalid_candidates):
    hidden_solution_case = next(
        c["candidate"] for c in invalid_candidates if c["name"] == "hidden_only_solution"
    )
    pipeline, logic, safety = _pipeline(tmp_path, logic_passed=False)

    result = pipeline.process(hidden_solution_case)

    assert result.accepted is False
    assert result.stage_failed == "logic"
    assert result.draft_path is None


def test_unsafe_case_is_rejected_at_safety_stage(tmp_path, valid_raw_candidate):
    pipeline, logic, safety = _pipeline(tmp_path, safety_passed=False)

    result = pipeline.process(valid_raw_candidate)

    assert result.accepted is False
    assert result.stage_failed == "safety"
    assert result.reasons == ("not safe",)
    assert result.draft_path is None
    assert logic.calls == 1
    assert safety.calls == 1


def test_no_draft_is_ever_saved_for_rejected_candidates(tmp_path, invalid_candidates):
    pipeline, _, _ = _pipeline(tmp_path, logic_passed=False, safety_passed=False)

    for case in invalid_candidates:
        pipeline.process(case["candidate"])

    drafts_dir = tmp_path / "drafts"
    stored = list(drafts_dir.glob("*.json")) if drafts_dir.exists() else []
    assert stored == [], "no invalid candidate should ever reach draft storage"
