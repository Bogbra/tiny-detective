from datetime import date

from app.infrastructure.repositories.in_memory_generation_quota_repository import (
    InMemoryDailyGenerationQuotaRepository,
)

TODAY = date(2026, 1, 15)
TOMORROW = date(2026, 1, 16)


def test_try_consume_success_allowed_under_cap():
    repo = InMemoryDailyGenerationQuotaRepository(success_cap=2, attempt_cap=10)

    assert repo.try_consume_success(TODAY) is True
    assert repo.try_consume_success(TODAY) is True
    assert repo.get_status(TODAY).success_count == 2


def test_try_consume_success_rejected_at_cap():
    repo = InMemoryDailyGenerationQuotaRepository(success_cap=2, attempt_cap=10)
    repo.try_consume_success(TODAY)
    repo.try_consume_success(TODAY)

    assert repo.try_consume_success(TODAY) is False
    # A rejected consume must not have incremented past the cap.
    assert repo.get_status(TODAY).success_count == 2


def test_try_reserve_attempt_independent_from_success_cap():
    """The attempt cap is a separate counter from the success cap — a
    request that never succeeds should still be able to keep attempting
    (up to the attempt cap) even if, hypothetically, the success cap were
    already exhausted by other requests."""
    repo = InMemoryDailyGenerationQuotaRepository(success_cap=1, attempt_cap=5)
    repo.try_consume_success(TODAY)
    assert repo.try_consume_success(TODAY) is False  # success cap exhausted

    assert repo.try_reserve_attempt(TODAY) is True  # attempts still allowed
    assert repo.get_status(TODAY).attempt_count == 1


def test_try_reserve_attempt_rejected_at_cap():
    repo = InMemoryDailyGenerationQuotaRepository(success_cap=50, attempt_cap=2)
    repo.try_reserve_attempt(TODAY)
    repo.try_reserve_attempt(TODAY)

    assert repo.try_reserve_attempt(TODAY) is False
    assert repo.get_status(TODAY).attempt_count == 2


def test_counters_are_independent_per_day():
    """A new calendar day resets both counters — proven here by injecting
    two distinct dates rather than depending on wall-clock time."""
    repo = InMemoryDailyGenerationQuotaRepository(success_cap=1, attempt_cap=1)
    assert repo.try_consume_success(TODAY) is True
    assert repo.try_consume_success(TODAY) is False

    assert repo.try_consume_success(TOMORROW) is True
    assert repo.get_status(TODAY).success_count == 1
    assert repo.get_status(TOMORROW).success_count == 1


def test_get_status_reports_exhausted_flag():
    repo = InMemoryDailyGenerationQuotaRepository(success_cap=1, attempt_cap=10)
    assert repo.get_status(TODAY).exhausted is False

    repo.try_consume_success(TODAY)
    assert repo.get_status(TODAY).exhausted is True
