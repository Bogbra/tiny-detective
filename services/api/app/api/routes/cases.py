import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime

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
from app.api.rate_limiting import limiter, per_instance_limit
from app.application.errors import CaseNotFoundError, PlayerNotFoundError
from app.application.ports import (
    AttemptRepository,
    CaseGenerationAdapter,
    CaseRepository,
    DailyGenerationQuotaRepository,
    HintRequestRepository,
    PlayerRepository,
)
from app.application.use_cases.generate_case import GenerateCase, GenerationEvent
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

# Kept below the Flutter client's 45s per-chunk idle timeout
# (case_generation_api_client.dart) with real margin, so the heartbeat is
# always the thing that fires first under normal conditions, not a race.
HEARTBEAT_INTERVAL_SECONDS = 15


async def stream_generation_events(
    events: AsyncIterator[GenerationEvent], *, heartbeat_seconds: float = HEARTBEAT_INTERVAL_SECONDS
) -> AsyncIterator[str]:
    """Wraps a GenerateCase.execute() stream as real SSE text, interleaving
    a ": keep-alive" comment line whenever heartbeat_seconds passes with no
    real event — a valid, no-op SSE frame (anything starting with ":" is a
    comment per the spec, ignored by any real consumer) that keeps the
    connection visibly alive during a long attempt (each stage is a real
    OpenAI call, up to 30s — see openai_client.py's timeout, task 6) so an
    intermediary (a proxy, a load balancer) doesn't kill it as idle. A
    standalone function, not nested in the route, specifically so this is
    unit-testable with a short heartbeat_seconds instead of a real 15s
    wait — see tests/unit/test_stream_generation_events.py.

    Deliberately NOT `asyncio.wait_for(agen.__anext__(), timeout=...)` in a
    loop — that was the first version, and a real test with a genuinely
    slow generator caught a real bug in it: wait_for cancels the awaited
    coroutine on timeout, and cancelling an async generator's in-flight
    __anext__() call typically kills the generator rather than leaving it
    resumable. In production that would mean the FIRST heartbeat during a
    slow attempt could silently terminate the real GenerateCase.execute()
    stream early, never delivering the actual event. Fixed by keeping the
    __anext__() call alive as a single background task across multiple
    heartbeat intervals (asyncio.wait with a timeout does not cancel an
    unfinished task the way wait_for does) and only starting a new one
    once the current one actually completes.
    """
    agen = events.__aiter__()
    next_event_task = asyncio.ensure_future(agen.__anext__())
    try:
        while True:
            done, _pending = await asyncio.wait({next_event_task}, timeout=heartbeat_seconds)
            if not done:
                yield ": keep-alive\n\n"
                continue

            try:
                event = next_event_task.result()
            except StopAsyncIteration:
                return

            # Start waiting for the next event immediately, before doing
            # anything else — no gap in coverage between one event being
            # ready and the next wait beginning.
            next_event_task = asyncio.ensure_future(agen.__anext__())

            payload = GenerationEventResponse(
                step=event.step,
                status=event.status,
                detail=event.detail,
                attempt=event.attempt,
                case=to_case_response(event.case) if event.case is not None else None,
            )
            yield f"data: {payload.model_dump_json(by_alias=True)}\n\n"
    finally:
        # If the client disconnects (or anything else stops this generator
        # early), don't leave a dangling __anext__() task still running in
        # the background.
        next_event_task.cancel()


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
def get_case(case_id: str, case_repository: CaseRepository = Depends(get_case_repository)) -> CaseResponse:
    try:
        public_case = GetCase(case_repository).execute(CaseId(case_id))
    except CaseNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return to_case_response(public_case)


@router.post("/cases/{case_id}/solution", response_model=SubmitSolutionResponse)
@limiter.limit(per_instance_limit(10))
def submit_solution(
    request: Request,
    case_id: str,
    body: SubmitSolutionRequest,
    case_repository: CaseRepository = Depends(get_case_repository),
    player_repository: PlayerRepository = Depends(get_player_repository),
    hint_request_repository: HintRequestRepository = Depends(get_hint_request_repository),
    attempt_repository: AttemptRepository = Depends(get_attempt_repository),
) -> SubmitSolutionResponse:
    use_case = SubmitSolution(case_repository, player_repository, hint_request_repository, attempt_repository)
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
        already_solved=result.already_solved,
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
    today = datetime.now(UTC).date()

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

    return StreamingResponse(
        stream_generation_events(use_case.execute(today)), media_type="text/event-stream"
    )
