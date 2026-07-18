from app.domain.entities.attempt import Attempt


class InMemoryAttemptRepository:
    """Process-local attempt store. Used when Firestore isn't configured."""

    def __init__(self) -> None:
        self._records: list[Attempt] = []

    def record(self, attempt: Attempt) -> None:
        self._records.append(attempt)

    def exists_for(self, player_id: str, case_id: str) -> bool:
        return any(a.player_id == player_id and a.case_id == case_id for a in self._records)
