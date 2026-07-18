from datetime import date

import pytest

from app.application.use_cases.generate_case import GenerateCase
from app.domain.value_objects.case_id import CaseId
from app.infrastructure.repositories.in_memory_case_repository import InMemoryCaseRepository
from app.infrastructure.repositories.in_memory_generation_quota_repository import (
    InMemoryDailyGenerationQuotaRepository,
)
from tests.fakes import AttemptScript, FakeCaseGenerationAdapter, make_candidate

TODAY = date(2026, 1, 15)


async def _collect(async_gen):
    return [event async for event in async_gen]


@pytest.mark.anyio
async def test_success_on_first_attempt():
    adapter = FakeCaseGenerationAdapter([AttemptScript()])
    case_repository = InMemoryCaseRepository(initial_cases=[])
    quota = InMemoryDailyGenerationQuotaRepository(success_cap=50, attempt_cap=300)
    use_case = GenerateCase(adapter, case_repository, quota)

    events = await _collect(use_case.execute(TODAY))

    steps = [(e.step, e.status) for e in events]
    assert steps == [
        ("generating", "running"),
        ("generating", "passed"),
        ("logic_check", "running"),
        ("logic_check", "passed"),
        ("safety_check", "running"),
        ("safety_check", "passed"),
        ("saving", "running"),
        ("saving", "done"),
    ]
    final = events[-1]
    assert final.case is not None
    assert final.case.source == "live_generated"
    assert quota.get_status(TODAY).success_count == 1
    assert quota.get_status(TODAY).attempt_count == 1
    assert case_repository.get(CaseId(final.case.case_id)).status.value == "live"


@pytest.mark.anyio
async def test_visible_restart_after_a_rejection():
    """A logic-judge rejection on attempt 1, success on attempt 2 — the
    stream must show the real restart (a fresh 'generating: running' for
    attempt 2), not just the final outcome."""
    adapter = FakeCaseGenerationAdapter(
        [AttemptScript(logic_passes=False), AttemptScript(logic_passes=True)]
    )
    quota = InMemoryDailyGenerationQuotaRepository(success_cap=50, attempt_cap=300)
    use_case = GenerateCase(adapter, InMemoryCaseRepository(initial_cases=[]), quota)

    events = await _collect(use_case.execute(TODAY))

    steps = [(e.step, e.status, e.attempt) for e in events]
    assert steps == [
        ("generating", "running", 1),
        ("generating", "passed", 1),
        ("logic_check", "running", 1),
        ("logic_check", "rejected", 1),
        ("generating", "running", 2),  # the visible restart
        ("generating", "passed", 2),
        ("logic_check", "running", 2),
        ("logic_check", "passed", 2),
        ("safety_check", "running", 2),
        ("safety_check", "passed", 2),
        ("saving", "running", 2),
        ("saving", "done", 2),
    ]
    assert quota.get_status(TODAY).attempt_count == 2
    assert quota.get_status(TODAY).success_count == 1


@pytest.mark.anyio
async def test_safety_rejection_is_reported():
    adapter = FakeCaseGenerationAdapter([AttemptScript(safety_passes=False)])
    quota = InMemoryDailyGenerationQuotaRepository(success_cap=50, attempt_cap=300)
    use_case = GenerateCase(adapter, InMemoryCaseRepository(initial_cases=[]), quota, max_attempts=1)

    events = await _collect(use_case.execute(TODAY))

    safety_events = [e for e in events if e.step == "safety_check"]
    assert safety_events[-1].status == "rejected"
    assert events[-1].step == "failed"


@pytest.mark.anyio
async def test_max_attempts_exhausted_without_success():
    adapter = FakeCaseGenerationAdapter([AttemptScript(logic_passes=False)])
    quota = InMemoryDailyGenerationQuotaRepository(success_cap=50, attempt_cap=300)
    use_case = GenerateCase(adapter, InMemoryCaseRepository(initial_cases=[]), quota, max_attempts=3)

    events = await _collect(use_case.execute(TODAY))

    assert adapter.generate_calls == 3
    final = events[-1]
    assert final.step == "failed"
    assert final.status == "done"
    assert "3 attempts" in final.detail
    assert quota.get_status(TODAY).success_count == 0
    assert quota.get_status(TODAY).attempt_count == 3


@pytest.mark.anyio
async def test_rejected_attempts_never_count_against_success_quota():
    adapter = FakeCaseGenerationAdapter([AttemptScript(safety_passes=False)])
    quota = InMemoryDailyGenerationQuotaRepository(success_cap=1, attempt_cap=300)
    use_case = GenerateCase(adapter, InMemoryCaseRepository(initial_cases=[]), quota, max_attempts=5)

    await _collect(use_case.execute(TODAY))

    # 5 rejected attempts, all costing an attempt slot, none costing a
    # success slot -- the whole point of the two-counter design (ADR-0007).
    assert quota.get_status(TODAY).attempt_count == 5
    assert quota.get_status(TODAY).success_count == 0


@pytest.mark.anyio
async def test_quota_pre_check_short_circuits_with_zero_adapter_calls():
    adapter = FakeCaseGenerationAdapter([AttemptScript()])
    quota = InMemoryDailyGenerationQuotaRepository(success_cap=0, attempt_cap=300)
    use_case = GenerateCase(adapter, InMemoryCaseRepository(initial_cases=[]), quota)

    events = await _collect(use_case.execute(TODAY))

    assert adapter.generate_calls == 0
    assert len(events) == 1
    assert events[0].step == "quota_check"
    assert events[0].status == "rejected"
    assert events[0].detail == "daily generation quota reached"


@pytest.mark.anyio
async def test_domain_consistency_policy_rejects_a_two_culprit_candidate():
    """The AI judges can pass a candidate the deterministic domain policy
    would still reject (e.g. two suspects flagged as culprit) -- proves the
    policy actually rides along and isn't a no-op."""
    bad_candidate = make_candidate()
    import dataclasses

    suspects = list(bad_candidate.suspects)
    suspects[1] = dataclasses.replace(suspects[1], is_culprit=True)  # now two culprits
    bad_candidate = dataclasses.replace(bad_candidate, suspects=tuple(suspects))

    adapter = FakeCaseGenerationAdapter([AttemptScript(candidate=bad_candidate)])
    quota = InMemoryDailyGenerationQuotaRepository(success_cap=50, attempt_cap=300)
    use_case = GenerateCase(adapter, InMemoryCaseRepository(initial_cases=[]), quota, max_attempts=1)

    events = await _collect(use_case.execute(TODAY))

    logic_events = [e for e in events if e.step == "logic_check"]
    assert logic_events[-1].status == "rejected"
    assert "culprit" in logic_events[-1].detail
    assert events[-1].step == "failed"


@pytest.mark.anyio
async def test_quota_race_lost_at_final_save_is_reported_and_not_saved():
    class _AlwaysLoseFinalConsume(InMemoryDailyGenerationQuotaRepository):
        def try_consume_success(self, today: date) -> bool:
            return False

    adapter = FakeCaseGenerationAdapter([AttemptScript()])
    quota = _AlwaysLoseFinalConsume(success_cap=50, attempt_cap=300)
    case_repository = InMemoryCaseRepository(initial_cases=[])
    use_case = GenerateCase(adapter, case_repository, quota)

    events = await _collect(use_case.execute(TODAY))

    assert events[-1].step == "saving"
    assert events[-1].status == "rejected"
    assert events[-1].detail == "daily generation quota reached"
    assert case_repository.list_all() == []


@pytest.mark.anyio
async def test_injected_date_gives_independent_quota_per_day():
    adapter = FakeCaseGenerationAdapter([AttemptScript()])
    quota = InMemoryDailyGenerationQuotaRepository(success_cap=1, attempt_cap=300)
    use_case = GenerateCase(adapter, InMemoryCaseRepository(initial_cases=[]), quota)

    await _collect(use_case.execute(date(2026, 1, 15)))
    assert quota.get_status(date(2026, 1, 15)).success_count == 1
    assert quota.get_status(date(2026, 1, 16)).success_count == 0

    # A different injected date is a fresh quota -- generation succeeds
    # again even though "today" (2026-01-15) is already at its cap.
    events = await _collect(use_case.execute(date(2026, 1, 16)))
    assert events[-1].step == "saving" and events[-1].status == "done"
