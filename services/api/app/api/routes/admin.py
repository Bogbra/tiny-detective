"""Admin endpoints for the case status lifecycle (draft -> approved/rejected -> live).

POST /admin/cases/generate and POST /admin/cases/evaluate are not implemented
yet — they depend on the AI case generation pipeline built in Phase 5.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_case_repository, require_admin
from app.application.errors import (
    CaseNotFoundError,
    CaseNotInDraftError,
    CaseNotPublishableError,
    NoPublishableCaseError,
)
from app.application.ports import CaseRepository
from app.application.use_cases.approve_case import ApproveCase
from app.application.use_cases.publish_daily_case import PublishDailyCase
from app.application.use_cases.publish_next_daily_case import PublishNextDailyCase
from app.application.use_cases.reject_case import RejectCase
from app.contracts.responses.admin import AdminActionResponse
from app.domain.value_objects.case_id import CaseId

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/cases", tags=["admin"], dependencies=[Depends(require_admin)])


@router.post("/{case_id}/approve", response_model=AdminActionResponse)
def approve_case(
    case_id: str, case_repository: CaseRepository = Depends(get_case_repository)
) -> AdminActionResponse:
    try:
        ApproveCase(case_repository).execute(CaseId(case_id))
    except CaseNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CaseNotInDraftError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return AdminActionResponse(case_id=case_id, status="approved")


@router.post("/{case_id}/reject", response_model=AdminActionResponse)
def reject_case(
    case_id: str, case_repository: CaseRepository = Depends(get_case_repository)
) -> AdminActionResponse:
    try:
        RejectCase(case_repository).execute(CaseId(case_id))
    except CaseNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CaseNotInDraftError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return AdminActionResponse(case_id=case_id, status="rejected")


@router.post("/{case_id}/publish-daily", response_model=AdminActionResponse)
def publish_daily(
    case_id: str, case_repository: CaseRepository = Depends(get_case_repository)
) -> AdminActionResponse:
    try:
        PublishDailyCase(case_repository).execute(CaseId(case_id))
    except CaseNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CaseNotPublishableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return AdminActionResponse(case_id=case_id, status="live")


@router.post("/publish-next-daily", response_model=AdminActionResponse)
def publish_next_daily(case_repository: CaseRepository = Depends(get_case_repository)) -> AdminActionResponse:
    """Auto-selecting sibling of publish-daily, meant to be called by a
    scheduled job rather than a human — see ADR-0006's Cloud Scheduler
    addendum. Takes no case_id: PublishNextDailyCase picks the case itself.
    A 409 here means the case catalog is genuinely empty, the real signal
    a scheduler-failure alert should fire on.

    Logs at severity ERROR on that 409, deliberately, not just returning
    the HTTP status: a caught HTTPException never reaches
    logging_middleware's own error path (that only fires on an *unhandled*
    exception escaping call_next — FastAPI resolves HTTPException into a
    response before this middleware sees it), so without this explicit
    log line an empty catalog would only ever produce an ordinary INFO
    access-log entry. That would mean the exact regression this endpoint
    exists to prevent — a daily case nobody remembered to publish — could
    recur silently even with the scheduler itself working perfectly,
    just for a different underlying reason (nothing left to publish
    rather than nobody running the job). See docs/operations.md #7 for
    the Cloud Monitoring alert policy this severity is meant to trip.
    """
    try:
        case_id = PublishNextDailyCase(case_repository).execute()
    except NoPublishableCaseError as exc:
        logger.error("publish-next-daily found no publishable case: %s", exc)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return AdminActionResponse(case_id=case_id.value, status="live")
