"""Atomic daily counters backing the live case-generation feature's global
budget (see ADR-0007). No existing repository in this codebase does atomic
read-check-increment — built fresh using google-cloud-firestore's
@firestore.transactional, which retries the wrapped function automatically
on a write conflict (Firestore's optimistic concurrency model), giving the
correctness this needs under concurrent requests.

No separate pure-mapper module here (contrast case_mapper.py etc.) — the
document shape is a two-field counter, not worth splitting a mapping layer
out for. See ADR-0007.

Atomicity is verified against the Firestore emulator (see
tests/integration/test_firestore_generation_quota_repository.py) — the
emulator does not serialize concurrent transactions identically to real GCP
Firestore under genuine concurrent production load, and no such load test
is planned. Documented, not silently assumed: "locally verified against the
emulator, real-concurrency behavior unverified," the same honest framing
docs/scalability.md already uses for composite indexes.
"""

from datetime import date

from google.cloud import firestore

from app.application.ports import DEFAULT_DAILY_ATTEMPT_CAP, DEFAULT_DAILY_SUCCESS_CAP, QuotaStatus
from app.infrastructure.firestore.firestore_client import get_firestore_client

RATE_LIMITS_COLLECTION = "rate_limits"


def _document_id(today: date) -> str:
    return f"case_generation_{today.isoformat()}"


class FirestoreDailyGenerationQuotaRepository:
    def __init__(
        self,
        client: firestore.Client | None = None,
        success_cap: int = DEFAULT_DAILY_SUCCESS_CAP,
        attempt_cap: int = DEFAULT_DAILY_ATTEMPT_CAP,
    ) -> None:
        self._client = client or get_firestore_client()
        self._success_cap = success_cap
        self._attempt_cap = attempt_cap

    def get_status(self, today: date) -> QuotaStatus:
        doc = self._client.collection(RATE_LIMITS_COLLECTION).document(_document_id(today)).get()
        data = doc.to_dict() or {}
        return QuotaStatus(
            success_count=data.get("successCount", 0),
            success_cap=self._success_cap,
            attempt_count=data.get("attemptCount", 0),
            attempt_cap=self._attempt_cap,
        )

    def try_reserve_attempt(self, today: date) -> bool:
        return self._try_increment(today, field="attemptCount", cap=self._attempt_cap)

    def try_consume_success(self, today: date) -> bool:
        return self._try_increment(today, field="successCount", cap=self._success_cap)

    def _try_increment(self, today: date, *, field: str, cap: int) -> bool:
        doc_ref = self._client.collection(RATE_LIMITS_COLLECTION).document(_document_id(today))

        @firestore.transactional
        def _run(transaction: firestore.Transaction) -> bool:
            snapshot = doc_ref.get(transaction=transaction)
            data = snapshot.to_dict() or {}
            current = data.get(field, 0)
            if current >= cap:
                return False
            transaction.set(doc_ref, {field: current + 1}, merge=True)
            return True

        try:
            # max_attempts above the client default (5): found by testing,
            # not assumed — a real 20-way-concurrent burst against one
            # document (tests/integration/..._does_not_overcount) exhausted
            # the default and raised ValueError instead of returning
            # cleanly. Even with this higher ceiling, sufficiently extreme
            # contention can still exhaust it — handled below, not assumed
            # away.
            return _run(self._client.transaction(max_attempts=15))
        except ValueError:
            # Transaction couldn't commit within max_attempts (real
            # contention, not a cap decision). Fails closed: deny the
            # reservation rather than risk a double-count or crash the
            # request with a 500. Under pathological concurrency this can
            # make a request see "quota exhausted" even when a slot was
            # technically available — an accepted, documented trade-off for
            # a low-traffic demo feature (see ADR-0007), not silently
            # assumed to never happen.
            return False
