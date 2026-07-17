from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_player_repository
from app.application.errors import PlayerNotFoundError
from app.application.ports import PlayerRepository
from app.application.use_cases.get_player import GetPlayer
from app.contracts.responses.score import ScoreResponse

router = APIRouter(tags=["scores"])


@router.get("/scores/{player_id}", response_model=ScoreResponse)
def get_score(
    player_id: str, player_repository: PlayerRepository = Depends(get_player_repository)
) -> ScoreResponse:
    try:
        player = GetPlayer(player_repository).execute(player_id)
    except PlayerNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ScoreResponse(player_id=player.player_id, total_score=player.total_score, streak=player.streak)
