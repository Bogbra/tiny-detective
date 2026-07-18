from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, StreamingResponse

from app.api.dependencies import (
    get_attempt_repository,
    get_case_generation_adapter,
    get_case_repository,
    get_generation_quota_repository,
    get_hint_request_repository,
    get_player_repository,
)
from app.api.mappers import to_case_response
from app.api.rate_limiting import limiter
from app.application.errors import CaseNotFoundError, PlayerNotFoundError
from app.application.ports import (
    AttemptRepository,
    CaseGenerationAdapter,
    CaseRepository,
    DailyGenerationQuotaRepository,
    HintRequestRepository,
    PlayerRepository,
)
from app.application.use_cases.generate_case import GenerateCase
from app.application.use_cases.get_case import GetCase
from app.application.use_cases.get_daily_case import GetDailyCase
from app.application.use_cases.submit_solution import SubmitSolution
from app.contracts.requests.solution import SubmitSolutionRequest
from app.contracts.responses.case import CaseResponse
from app.contracts.responses.generation import GenerationEventResponse
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


# Public, unauthenticated, and each call can trigger several real OpenAI
# calls — capped by two independent axes (see ADR-0007): a per-IP rate
# limit here, and a global daily budget checked below. POST (not GET) is
# deliberate despite the "SSE" association with the browser's native
# EventSource (GET-only) — the Flutter web client doesn't use EventSource
# at all, it reads a chunked text/event-stream body via package:http, which
# works with any HTTP method.
@router.post("/cases/generate")
@limiter.limit("3/minute")
async def generate_case(
    request: Request,
    case_generation_adapter: CaseGenerationAdapter = Depends(get_case_generation_adapter),
    case_repository: CaseRepository = Depends(get_case_repository),
    quota_repository: DailyGenerationQuotaRepository = Depends(get_generation_quota_repository),
):
    today = datetime.now(timezone.utc).date()

    # Fail fast with zero LLM calls if the day's budget is already gone —
    # a plain 429, not an SSE stream, so the frontend handles it exactly
    # like any other 429 (see GenerateCase.execute's own pre-check, which
    # this mirrors — this one avoids opening a stream at all).
    if quota_repository.get_status(today).exhausted:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "daily generation quota reached"},
        )

    use_case = GenerateCase(case_generation_adapter, case_repository, quota_repository)

    async def event_stream():
        async for event in use_case.execute(today):
            payload = GenerationEventResponse(
                step=event.step,
                status=event.status,
                detail=event.detail,
                attempt=event.attempt,
                case=to_case_response(event.case) if event.case is not None else None,
            )
            yield f"data: {payload.model_dump_json(by_alias=True)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
