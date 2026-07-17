from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_attempt_repository,
    get_case_repository,
    get_hint_request_repository,
    get_player_repository,
)
from app.api.mappers import to_case_response
from app.application.errors import CaseNotFoundError, PlayerNotFoundError
from app.application.ports import (
    AttemptRepository,
    CaseRepository,
    HintRequestRepository,
    PlayerRepository,
)
from app.application.use_cases.get_case import GetCase
from app.application.use_cases.get_daily_case import GetDailyCase
from app.application.use_cases.submit_solution import SubmitSolution
from app.contracts.requests.solution import SubmitSolutionRequest
from app.contracts.responses.case import CaseResponse
from app.contracts.responses.solution import SubmitSolutionResponse
from app.domain.errors import UnknownSuspectError
from app.domain.value_objects.case_id import CaseId

router = APIRouter(tags=["cases"])


@router.get("/cases/daily", response_model=CaseResponse)
def get_daily_case(
    case_repository: CaseRepository = Depends(get_case_repository),
) -> CaseResponse:
    try:
        public_case = GetDailyCase(case_repository).execute()
    except CaseNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return to_case_response(public_case)


@router.get("/cases/{case_id}", response_model=CaseResponse)
def get_case(
    case_id: str, case_repository: CaseRepository = Depends(get_case_repository)
) -> CaseResponse:
    try:
        public_case = GetCase(case_repository).execute(CaseId(case_id))
    except CaseNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return to_case_response(public_case)


@router.post("/cases/{case_id}/solution", response_model=SubmitSolutionResponse)
def submit_solution(
    case_id: str,
    body: SubmitSolutionRequest,
    case_repository: CaseRepository = Depends(get_case_repository),
    player_repository: PlayerRepository = Depends(get_player_repository),
    hint_request_repository: HintRequestRepository = Depends(get_hint_request_repository),
    attempt_repository: AttemptRepository = Depends(get_attempt_repository),
) -> SubmitSolutionResponse:
    use_case = SubmitSolution(
        case_repository, player_repository, hint_request_repository, attempt_repository
    )
    try:
        result = use_case.execute(CaseId(case_id), body.player_id, body.suspect_id)
    except CaseNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PlayerNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except UnknownSuspectError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return SubmitSolutionResponse(
        correct=result.correct,
        score=result.score,
        feedback=result.feedback,
        solution_explanation=result.solution_explanation,
        streak=result.streak,
    )
