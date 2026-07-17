from app.domain.entities.player import Player


class InMemoryPlayerRepository:
    """Process-local player store. Replaced by a Firestore-backed repository in Phase 7."""

    def __init__(self) -> None:
        self._players: dict[str, Player] = {}

    def get(self, player_id: str) -> Player | None:
        return self._players.get(player_id)

    def save(self, player: Player) -> None:
        self._players[player.player_id] = player
