from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.dependencies import (
    get_case_repository,
    get_hint_assistant,
    get_hint_request_repository,
    get_player_repository,
)
from app.api.rate_limiting import limiter
from app.application.errors import CaseNotFoundError, HintLimitExceededError, PlayerNotFoundError
from app.application.ports import CaseRepository, HintAssistant, HintRequestRepository, PlayerRepository
from app.application.use_cases.request_hint import RequestHint
from app.contracts.requests.hint import RequestHintRequest
from app.contracts.responses.hint import HintResponse
from app.domain.value_objects.case_id import CaseId

router = APIRouter(tags=["hints"])


@router.post("/cases/{case_id}/hint", response_model=HintResponse)
@limiter.limit("5/minute")
def request_hint(
    request: Request,
    case_id: str,
    body: RequestHintRequest,
    case_repository: CaseRepository = Depends(get_case_repository),
    hint_request_repository: HintRequestRepository = Depends(get_hint_request_repository),
    hint_assistant: HintAssistant = Depends(get_hint_assistant),
    player_repository: PlayerRepository = Depends(get_player_repository),
) -> HintResponse:
    use_case = RequestHint(case_repository, hint_request_repository, hint_assistant, player_repository)
    try:
        result = use_case.execute(CaseId(case_id), body.player_id)
    except CaseNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PlayerNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except HintLimitExceededError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return HintResponse(
        text=result.text, hints_used=result.hints_used, hints_remaining=result.hints_remaining
    )
