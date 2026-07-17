from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_player_repository
from app.application.errors import PlayerNotFoundError
from app.application.ports import PlayerRepository
from app.application.use_cases.create_player import CreatePlayer
from app.application.use_cases.get_player import GetPlayer
from app.contracts.responses.player import PlayerResponse
from app.domain.entities.player import Player

router = APIRouter(tags=["players"])


def _to_player_response(player: Player) -> PlayerResponse:
    return PlayerResponse(
        player_id=player.player_id,
        display_name=player.display_name,
        streak=player.streak,
        total_score=player.total_score,
    )


@router.post("/players", response_model=PlayerResponse, status_code=status.HTTP_201_CREATED)
def create_player(
    player_repository: PlayerRepository = Depends(get_player_repository),
) -> PlayerResponse:
    player = CreatePlayer(player_repository).execute()
    return _to_player_response(player)


@router.get("/players/{player_id}", response_model=PlayerResponse)
def get_player(
    player_id: str, player_repository: PlayerRepository = Depends(get_player_repository)
) -> PlayerResponse:
    try:
        player = GetPlayer(player_repository).execute(player_id)
    except PlayerNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _to_player_response(player)
