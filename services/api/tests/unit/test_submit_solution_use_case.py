import pytest

from app.application.errors import CaseNotFoundError, PlayerNotFoundError
from app.application.use_cases.submit_solution import SubmitSolution
from app.domain.entities.player import Player
from app.domain.errors import UnknownSuspectError
from app.domain.value_objects.case_id import CaseId
from app.infrastructure.repositories.in_memory_attempt_repository import InMemoryAttemptRepository
from app.infrastructure.repositories.in_memory_case_repository import InMemoryCaseRepository
from app.infrastructure.repositories.in_memory_hint_request_repository import (
    InMemoryHintRequestRepository,
)
from app.infrastructure.repositories.in_memory_player_repository import InMemoryPlayerRepository


def _use_case(case, *, known_player_id="player-1"):
    case_repository = InMemoryCaseRepository(initial_cases=[case])
    player_repository = InMemoryPlayerRepository()
    if known_player_id is not None:
        player_repository.save(Player(player_id=known_player_id))
    hint_request_repository = InMemoryHintRequestRepository()
    attempt_repository = InMemoryAttemptRepository()
    return (
        SubmitSolution(case_repository, player_repository, hint_request_repository, attempt_repository),
        player_repository,
    )


def test_first_correct_submission_scores_and_updates_streak(make_case):
    case = make_case()
    use_case, player_repository = _use_case(case)

    result = use_case.execute(case.case_id, "player-1", "suspect_3")

    assert result.correct is True
    assert result.score == 100
    assert result.streak == 1
    assert result.already_solved is False
    assert player_repository.get("player-1").total_score == 100
    assert player_repository.get("player-1").streak == 1


def test_first_incorrect_submission_scores_zero_and_resets_streak(make_case):
    case = make_case()
    use_case, player_repository = _use_case(case)
    player_repository.save(Player(player_id="player-1", streak=2))

    result = use_case.execute(case.case_id, "player-1", "suspect_1")

    assert result.correct is False
    assert result.score == 0
    assert result.streak == 0
    assert result.already_solved is False


def test_repeat_submission_does_not_add_score_or_change_streak(make_case):
    """The core anti-farming fix: resubmitting the same case must not keep
    granting score or advancing the streak, whatever the answer is this
    time. See task 3 of the security/ops audit."""
    case = make_case()
    use_case, player_repository = _use_case(case)

    first = use_case.execute(case.case_id, "player-1", "suspect_3")
    assert first.score == 100
    assert first.streak == 1
    assert first.already_solved is False

    second = use_case.execute(case.case_id, "player-1", "suspect_3")
    assert second.correct is True  # still an honest answer
    assert second.score == 0
    assert second.streak == 1  # unchanged, not incremented again
    assert second.already_solved is True

    # And the player's persisted totals never moved past the first attempt.
    player = player_repository.get("player-1")
    assert player.total_score == 100
    assert player.streak == 1


def test_repeat_submission_with_a_different_answer_still_does_not_score(make_case):
    case = make_case()
    use_case, player_repository = _use_case(case)

    use_case.execute(case.case_id, "player-1", "suspect_1")  # wrong first guess
    second = use_case.execute(case.case_id, "player-1", "suspect_3")  # correct second guess

    assert second.correct is True
    assert second.score == 0
    assert second.already_solved is True
    assert player_repository.get("player-1").total_score == 0


def test_repeat_submissions_are_still_recorded_as_attempts(make_case):
    """Repeats aren't silently dropped — the attempt log stays complete for
    auditing, only the score/streak effect is gated."""
    case = make_case()
    case_repository = InMemoryCaseRepository(initial_cases=[case])
    player_repository = InMemoryPlayerRepository()
    player_repository.save(Player(player_id="player-1"))
    hint_request_repository = InMemoryHintRequestRepository()

    class _CountingAttemptRepository(InMemoryAttemptRepository):
        def __init__(self):
            super().__init__()
            self.record_calls = 0

        def record(self, attempt):
            self.record_calls += 1
            super().record(attempt)

    attempt_repository = _CountingAttemptRepository()
    use_case = SubmitSolution(case_repository, player_repository, hint_request_repository, attempt_repository)

    use_case.execute(case.case_id, "player-1", "suspect_3")
    use_case.execute(case.case_id, "player-1", "suspect_3")

    assert attempt_repository.record_calls == 2


def test_a_different_player_on_the_same_case_scores_independently(make_case):
    case = make_case()
    case_repository = InMemoryCaseRepository(initial_cases=[case])
    player_repository = InMemoryPlayerRepository()
    player_repository.save(Player(player_id="player-1"))
    player_repository.save(Player(player_id="player-2"))
    hint_request_repository = InMemoryHintRequestRepository()
    attempt_repository = InMemoryAttemptRepository()
    use_case = SubmitSolution(case_repository, player_repository, hint_request_repository, attempt_repository)

    use_case.execute(case.case_id, "player-1", "suspect_3")
    result = use_case.execute(case.case_id, "player-2", "suspect_3")

    assert result.already_solved is False
    assert result.score == 100


def test_unknown_case_raises(make_case):
    case = make_case()
    use_case, _ = _use_case(case)

    with pytest.raises(CaseNotFoundError):
        use_case.execute(CaseId("does-not-exist"), "player-1", "suspect_3")


def test_unknown_player_raises(make_case):
    case = make_case()
    use_case, _ = _use_case(case, known_player_id=None)

    with pytest.raises(PlayerNotFoundError):
        use_case.execute(case.case_id, "never-registered", "suspect_3")


def test_unknown_suspect_raises(make_case):
    case = make_case()
    use_case, _ = _use_case(case)

    with pytest.raises(UnknownSuspectError):
        use_case.execute(case.case_id, "player-1", "not-a-real-suspect")
