from app.application.errors import PlayerNotFoundError
from app.application.ports import PlayerRepository
from app.domain.entities.player import Player


class GetPlayer:
    def __init__(self, player_repository: PlayerRepository) -> None:
        self._player_repository = player_repository

    def execute(self, player_id: str) -> Player:
        player = self._player_repository.get(player_id)
        if player is None:
            raise PlayerNotFoundError(f"player '{player_id}' not found")
        return player
