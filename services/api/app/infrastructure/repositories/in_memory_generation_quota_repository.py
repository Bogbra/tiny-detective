from collections import defaultdict
from datetime import date

from app.application.ports import DEFAULT_DAILY_ATTEMPT_CAP, DEFAULT_DAILY_SUCCESS_CAP, QuotaStatus


class InMemoryDailyGenerationQuotaRepository:
    """Process-local, best-effort — not atomic across concurrent asyncio
    tasks the way FirestoreDailyGenerationQuotaRepository's transactions
    are. Fine for local dev and tests, which don't need true concurrency
    safety; real atomicity is Firestore's job and is what that repository's
    own integration test verifies against the emulator."""

    def __init__(
        self,
        success_cap: int = DEFAULT_DAILY_SUCCESS_CAP,
        attempt_cap: int = DEFAULT_DAILY_ATTEMPT_CAP,
    ) -> None:
        self._success_cap = success_cap
        self._attempt_cap = attempt_cap
        self._success_counts: dict[date, int] = defaultdict(int)
        self._attempt_counts: dict[date, int] = defaultdict(int)

    def get_status(self, today: date) -> QuotaStatus:
        return QuotaStatus(
            success_count=self._success_counts[today],
            success_cap=self._success_cap,
            attempt_count=self._attempt_counts[today],
            attempt_cap=self._attempt_cap,
        )

    def try_reserve_attempt(self, today: date) -> bool:
        if self._attempt_counts[today] >= self._attempt_cap:
            return False
        self._attempt_counts[today] += 1
        return True

    def try_consume_success(self, today: date) -> bool:
        if self._success_counts[today] >= self._success_cap:
            return False
        self._success_counts[today] += 1
        return True
