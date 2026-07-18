from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.dependencies import get_player_repository
from app.api.rate_limiting import limiter
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
# so the limit here is about write volume, not model spend). 10/minute,
# not the tighter 5/minute used for /hint: a real player only ever needs
# one call, but a single legitimate multi-player test flow in this suite
# (test_hint_endpoint_rate_limits_by_caller) creates 6 in quick succession
# from one caller — the limit needs headroom above realistic legitimate
# bursts, not just above a single call.
@router.post("/players", response_model=PlayerResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
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
