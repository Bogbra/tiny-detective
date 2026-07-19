from datetime import UTC, datetime

import pytest

from app.application.errors import NoPublishableCaseError
from app.application.use_cases.publish_next_daily_case import PublishNextDailyCase
from app.domain.value_objects.case_id import CaseId
from app.domain.value_objects.publish_status import PublishStatus
from app.infrastructure.repositories.in_memory_case_repository import InMemoryCaseRepository


def test_raises_when_no_case_is_eligible(make_case):
    case_repository = InMemoryCaseRepository(initial_cases=[make_case(status=PublishStatus.DRAFT)])

    with pytest.raises(NoPublishableCaseError):
        PublishNextDailyCase(case_repository).execute()


def test_publishes_the_only_eligible_case(make_case):
    case = make_case(status=PublishStatus.APPROVED)
    case_repository = InMemoryCaseRepository(initial_cases=[case])

    published_id = PublishNextDailyCase(case_repository).execute()

    assert published_id.value == case.case_id.value
    assert case_repository.get_daily().case_id.value == case.case_id.value


def test_republishes_the_sole_case_when_it_is_already_todays_daily(make_case):
    case = make_case(status=PublishStatus.APPROVED)
    case_repository = InMemoryCaseRepository(initial_cases=[case])
    case_repository.set_daily(case.case_id)

    published_id = PublishNextDailyCase(case_repository).execute()

    assert published_id.value == case.case_id.value


def test_rotates_away_from_todays_case_when_an_alternative_exists(make_case):
    todays_case = make_case(
        case_id=CaseId("case_a"),
        status=PublishStatus.LIVE,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    fresher_case = make_case(
        case_id=CaseId("case_b"),
        status=PublishStatus.APPROVED,
        created_at=datetime(2026, 1, 2, tzinfo=UTC),
    )
    case_repository = InMemoryCaseRepository(initial_cases=[todays_case, fresher_case])
    case_repository.set_daily(todays_case.case_id)

    published_id = PublishNextDailyCase(case_repository).execute()

    assert published_id.value == "case_b"


def test_ignores_live_generated_cases_even_when_status_is_live(make_case):
    # Found live, not in review: player-generated cases are saved with
    # status=LIVE too (see generate_case.py), so without a source filter
    # this use case would rotate the public daily case onto a random
    # one-off, per-player generated case instead of the curated one.
    curated_case = make_case(case_id=CaseId("case_curated"), status=PublishStatus.LIVE, source="curated")
    generated_case = make_case(
        case_id=CaseId("case_live_abc123"), status=PublishStatus.LIVE, source="live_generated"
    )
    case_repository = InMemoryCaseRepository(initial_cases=[curated_case, generated_case])
    case_repository.set_daily(curated_case.case_id)

    published_id = PublishNextDailyCase(case_repository).execute()

    assert published_id.value == "case_curated"


def test_raises_when_only_live_generated_cases_exist(make_case):
    generated_case = make_case(
        case_id=CaseId("case_live_abc123"), status=PublishStatus.LIVE, source="live_generated"
    )
    case_repository = InMemoryCaseRepository(initial_cases=[generated_case])

    with pytest.raises(NoPublishableCaseError):
        PublishNextDailyCase(case_repository).execute()


def test_ignores_draft_and_rejected_cases_when_rotating(make_case):
    live_case = make_case(case_id=CaseId("case_live"), status=PublishStatus.LIVE)
    draft_case = make_case(case_id=CaseId("case_draft"), status=PublishStatus.DRAFT)
    rejected_case = make_case(case_id=CaseId("case_rejected"), status=PublishStatus.REJECTED)
    case_repository = InMemoryCaseRepository(initial_cases=[live_case, draft_case, rejected_case])
    case_repository.set_daily(live_case.case_id)

    published_id = PublishNextDailyCase(case_repository).execute()

    assert published_id.value == "case_live"
