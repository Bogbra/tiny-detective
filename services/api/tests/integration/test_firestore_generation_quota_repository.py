"""Real-emulator tests for the atomic daily generation quota counters.

Atomicity here means: verified against the Firestore emulator's real
transaction/conflict-retry behavior. The emulator does not serialize
concurrent transactions identically to real GCP Firestore under genuine
concurrent production load, and no production load test is planned for
this — see the repository's own module docstring and ADR-0007. This test
proves the transaction logic is correct under *some* real concurrency, not
that it holds at production scale.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, time, timedelta

from app.infrastructure.firestore.firestore_generation_quota_repository import (
    RATE_LIMITS_COLLECTION,
    FirestoreDailyGenerationQuotaRepository,
    _document_id,
)

from .conftest import requires_firestore_emulator

TODAY = date(2026, 1, 15)
TOMORROW = date(2026, 1, 16)


@requires_firestore_emulator
def test_expire_at_is_written_for_ttl_and_scoped_to_the_specific_day(firestore_client):
    """See task 13 of the security/ops audit — this field is what a
    `gcloud firestore fields ttls update` policy would attach to."""
    repo = FirestoreDailyGenerationQuotaRepository(client=firestore_client, success_cap=5, attempt_cap=10)

    repo.try_reserve_attempt(TODAY)

    raw = firestore_client.collection(RATE_LIMITS_COLLECTION).document(_document_id(TODAY)).get().to_dict()
    expected = datetime.combine(TODAY, time.min, tzinfo=UTC) + timedelta(days=7)
    assert raw["expireAt"] == expected


@requires_firestore_emulator
def test_try_consume_success_allowed_under_cap(firestore_client):
    repo = FirestoreDailyGenerationQuotaRepository(client=firestore_client, success_cap=2, attempt_cap=10)

    assert repo.try_consume_success(TODAY) is True
    assert repo.try_consume_success(TODAY) is True
    assert repo.get_status(TODAY).success_count == 2


@requires_firestore_emulator
def test_try_consume_success_rejected_at_cap(firestore_client):
    repo = FirestoreDailyGenerationQuotaRepository(client=firestore_client, success_cap=2, attempt_cap=10)
    repo.try_consume_success(TODAY)
    repo.try_consume_success(TODAY)

    assert repo.try_consume_success(TODAY) is False
    assert repo.get_status(TODAY).success_count == 2


@requires_firestore_emulator
def test_try_reserve_attempt_independent_counter(firestore_client):
    repo = FirestoreDailyGenerationQuotaRepository(client=firestore_client, success_cap=1, attempt_cap=5)
    repo.try_consume_success(TODAY)

    assert repo.try_reserve_attempt(TODAY) is True
    status = repo.get_status(TODAY)
    assert status.attempt_count == 1
    assert status.success_count == 1


@requires_firestore_emulator
def test_counters_reset_on_a_new_utc_calendar_day(firestore_client):
    repo = FirestoreDailyGenerationQuotaRepository(client=firestore_client, success_cap=1, attempt_cap=10)
    assert repo.try_consume_success(TODAY) is True
    assert repo.try_consume_success(TODAY) is False

    assert repo.try_consume_success(TOMORROW) is True
    assert repo.get_status(TODAY).success_count == 1
    assert repo.get_status(TOMORROW).success_count == 1


@requires_firestore_emulator
def test_concurrent_try_consume_success_does_not_overcount(firestore_client):
    """20 real, concurrent (thread-pooled) transactions against a cap of
    10. The invariant that actually matters — the one "atomic" is claiming
    — is that the stored count NEVER exceeds the cap and never disagrees
    with how many calls actually reported True; a naive read-then-write
    (not wrapped in a transaction) would violate this under the same test.

    It is NOT asserted that exactly 10 calls return True: under this much
    real concurrency on one document, some transactions can exhaust
    Firestore's commit-retry budget and fail closed (return False) even
    though a slot was technically free — found by running this test, not
    assumed; see FirestoreDailyGenerationQuotaRepository._try_increment's
    comment. So sum(results) <= 10 is the honest, correct assertion."""
    repo = FirestoreDailyGenerationQuotaRepository(client=firestore_client, success_cap=10, attempt_cap=1000)

    with ThreadPoolExecutor(max_workers=20) as pool:
        results = list(pool.map(lambda _: repo.try_consume_success(TODAY), range(20)))

    successes = sum(results)
    assert successes <= 10
    assert repo.get_status(TODAY).success_count == successes
