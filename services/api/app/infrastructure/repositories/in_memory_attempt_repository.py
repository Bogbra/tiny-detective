from app.domain.entities.attempt import Attempt


class InMemoryAttemptRepository:
    """Process-local attempt store. Used when Firestore isn't configured."""

    def __init__(self) -> None:
        self._records: list[Attempt] = []

    def record(self, attempt: Attempt) -> None:
        self._records.append(attempt)
