import uuid
from datetime import UTC, datetime

from app.application.ports import PlayerRepository
from app.domain.entities.player import Player


class CreatePlayer:
    def __init__(self, player_repository: PlayerRepository) -> None:
        self._player_repository = player_repository

    def execute(self) -> Player:
        player = Player(player_id=str(uuid.uuid4()), created_at=datetime.now(UTC))
        self._player_repository.save(player)
        return player
