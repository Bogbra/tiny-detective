import pytest

from app.application.errors import CaseNotFoundError, HintLimitExceededError
from app.application.ports import AssistantHint
from app.application.use_cases.request_hint import FALLBACK_HINT_TEXT, RequestHint
from app.domain.value_objects.case_id import CaseId
from app.infrastructure.repositories.in_memory_case_repository import InMemoryCaseRepository
from app.infrastructure.repositories.in_memory_hint_request_repository import (
    InMemoryHintRequestRepository,
)

from tests.fakes import FakeHintAssistant


def _use_case(case, assistant):
    case_repository = InMemoryCaseRepository(initial_cases=[case])
    hint_request_repository = InMemoryHintRequestRepository()
    return RequestHint(case_repository, hint_request_repository, assistant), hint_request_repository


def test_uses_ai_hint_when_grounded_and_safe(make_case):
    case = make_case()
    assistant = FakeHintAssistant(
        AssistantHint(clue_id=case.clues[0].clue_id, commentary="Look closely here.")
    )
    use_case, _ = _use_case(case, assistant)

    result = use_case.execute(case.case_id, "player-1")

    assert "Look closely here." in result.text
    assert case.clues[0].text in result.text
    assert result.hints_used == 1
    assert assistant.calls == 1
    assert assistant.last_hint_level == 1


def test_falls_back_when_assistant_returns_none(make_case):
    case = make_case()
    assistant = FakeHintAssistant(None)
    use_case, _ = _use_case(case, assistant)

    result = use_case.execute(case.case_id, "player-1")

    assert result.text == FALLBACK_HINT_TEXT


def test_falls_back_when_clue_id_is_invalid(make_case):
    """'hint does not invent facts' / 'hint is grounded in case clues' —
    an assistant response referencing a clue that doesn't exist in this case
    must not be trusted."""
    case = make_case()
    assistant = FakeHintAssistant(AssistantHint(clue_id="not-a-real-clue", commentary="???"))
    use_case, _ = _use_case(case, assistant)

    result = use_case.execute(case.case_id, "player-1")

    assert result.text == FALLBACK_HINT_TEXT


def test_falls_back_when_hint_names_the_culprit(make_case):
    """'hint does not reveal culprit'."""
    case = make_case()
    culprit_name = next(s.name for s in case.suspects if s.is_culprit)
    assistant = FakeHintAssistant(
        AssistantHint(clue_id=case.clues[0].clue_id, commentary=f"{culprit_name} looks suspicious.")
    )
    use_case, _ = _use_case(case, assistant)

    result = use_case.execute(case.case_id, "player-1")

    assert result.text == FALLBACK_HINT_TEXT
    assert culprit_name not in result.text


def test_falls_back_when_hint_names_an_innocent_suspect(make_case):
    case = make_case()
    innocent_name = next(s.name for s in case.suspects if not s.is_culprit)
    assistant = FakeHintAssistant(
        AssistantHint(clue_id=case.clues[0].clue_id, commentary=f"Reconsider {innocent_name}.")
    )
    use_case, _ = _use_case(case, assistant)

    result = use_case.execute(case.case_id, "player-1")

    assert result.text == FALLBACK_HINT_TEXT


def test_assistant_never_receives_solution_or_private_data(make_case):
    """'hint does not reveal full solution' — proven structurally: the
    assistant is only ever given case.public_view(), which has no field for
    the solution or private suspect data to leak in the first place."""
    case = make_case()
    assistant = FakeHintAssistant(None)
    use_case, _ = _use_case(case, assistant)

    use_case.execute(case.case_id, "player-1")

    received = assistant.last_public_case
    assert received is not None
    assert not hasattr(received, "solution")
    for suspect in received.suspects:
        assert not hasattr(suspect, "is_culprit")
        assert not hasattr(suspect, "private_reasoning")


def test_fallback_hint_works_and_still_counts_toward_the_limit(make_case):
    case = make_case()
    assistant = FakeHintAssistant(None)
    use_case, hint_request_repository = _use_case(case, assistant)

    result = use_case.execute(case.case_id, "player-1")

    assert result.text == FALLBACK_HINT_TEXT
    assert hint_request_repository.count_for_case(case.case_id, "player-1") == 1


def test_hint_limit_still_enforced(make_case):
    case = make_case()
    assistant = FakeHintAssistant(None)
    use_case, _ = _use_case(case, assistant)

    for _ in range(3):
        use_case.execute(case.case_id, "player-1")

    with pytest.raises(HintLimitExceededError):
        use_case.execute(case.case_id, "player-1")


def test_unknown_case_raises(make_case):
    assistant = FakeHintAssistant(None)
    case_repository = InMemoryCaseRepository()
    hint_request_repository = InMemoryHintRequestRepository()
    use_case = RequestHint(case_repository, hint_request_repository, assistant)

    with pytest.raises(CaseNotFoundError):
        use_case.execute(CaseId("does-not-exist"), "player-1")
