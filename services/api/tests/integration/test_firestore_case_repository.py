import dataclasses

from app.domain.value_objects.case_id import CaseId
from app.domain.value_objects.publish_status import PublishStatus
from app.infrastructure.firestore.firestore_case_repository import FirestoreCaseRepository

from .conftest import requires_firestore_emulator


@requires_firestore_emulator
def test_save_and_get_round_trip(firestore_client, make_case):
    repo = FirestoreCaseRepository(client=firestore_client)
    case = make_case()

    repo.save(case)
    fetched = repo.get(case.case_id)

    assert fetched == case


@requires_firestore_emulator
def test_get_returns_none_for_unknown_case(firestore_client):
    repo = FirestoreCaseRepository(client=firestore_client)

    assert repo.get(CaseId("does-not-exist")) is None


@requires_firestore_emulator
def test_status_transitions_persist_through_draft_approved_live(firestore_client, make_case):
    repo = FirestoreCaseRepository(client=firestore_client)
    case = make_case(status=PublishStatus.DRAFT)
    repo.save(case)
    assert repo.get(case.case_id).status == PublishStatus.DRAFT

    repo.save(dataclasses.replace(case, status=PublishStatus.APPROVED))
    assert repo.get(case.case_id).status == PublishStatus.APPROVED

    repo.save(dataclasses.replace(case, status=PublishStatus.LIVE))
    assert repo.get(case.case_id).status == PublishStatus.LIVE


@requires_firestore_emulator
def test_set_daily_and_get_daily_round_trip(firestore_client, make_case):
    repo = FirestoreCaseRepository(client=firestore_client)
    case = make_case()
    repo.save(case)

    assert repo.get_daily() is None

    repo.set_daily(case.case_id)
    daily = repo.get_daily()

    assert daily is not None
    assert daily.case_id == case.case_id


@requires_firestore_emulator
def test_public_view_excludes_solution_and_private_fields_after_real_persistence(firestore_client, make_case):
    """Proves public/private separation holds end-to-end THROUGH real
    storage: the raw Firestore document must contain the solution/private
    data (the backend needs it server-side), but the domain object read
    back from it still produces a public_view() that excludes it entirely —
    same guarantee Phase 2 proved in isolation, now proven through the
    actual persistence layer too."""
    repo = FirestoreCaseRepository(client=firestore_client)
    case = make_case()
    repo.save(case)

    raw_doc = firestore_client.collection("cases").document(case.case_id.value).get().to_dict()
    assert "culpritSuspectId" in raw_doc["solution"]
    assert any(s["isCulprit"] for s in raw_doc["suspects"])
    assert any(s["privateReasoning"] for s in raw_doc["suspects"])

    fetched = repo.get(case.case_id)
    public = fetched.public_view()

    assert not hasattr(public, "solution")
    for suspect in public.suspects:
        assert not hasattr(suspect, "is_culprit")
        assert not hasattr(suspect, "private_reasoning")
