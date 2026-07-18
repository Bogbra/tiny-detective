from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.dependencies import get_player_repository
from app.api.rate_limiting import limiter, per_instance_limit
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


# Public, unauthenticated, and unbounded creation would let a caller mint
# unlimited players/documents for free — cheap individually, but a real
# storage-growth and quota-exhaustion vector at scale with no other gate
# on it (unlike /cases/generate or /hint, this endpoint costs no AI call,
# so the limit here is about write volume, not model spend, and there's no
# secondary cluster-wide backstop underneath it — see rate_limiting.py's
# per_instance_limit for why that makes instance-count-awareness matter
# here specifically). Intended cluster-wide rate: 10/minute, comfortably
# above the largest legitimate multi-call burst in this test suite
# (test_hint_endpoint_rate_limits_by_caller creates 6 players in one test).
@router.post("/players", response_model=PlayerResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(per_instance_limit(10))
def create_player(
    request: Request,
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
