"""Proves the use cases actually work end-to-end against real Firestore-backed
repositories, not just that each repository works in isolation — the same
CaseRepository/PlayerRepository/etc. Protocol interfaces the use cases were
built against since Phase 3, now satisfied by a different adapter.
"""

from app.application.use_cases.request_hint import RequestHint
from app.application.use_cases.submit_solution import SubmitSolution
from app.domain.entities.player import Player
from app.infrastructure.firestore.firestore_attempt_repository import FirestoreAttemptRepository
from app.infrastructure.firestore.firestore_case_repository import FirestoreCaseRepository
from app.infrastructure.firestore.firestore_hint_request_repository import (
    FirestoreHintRequestRepository,
)
from app.infrastructure.firestore.firestore_player_repository import FirestorePlayerRepository

from tests.fakes import FakeHintAssistant

from .conftest import requires_firestore_emulator


@requires_firestore_emulator
def test_submit_solution_persists_an_attempt_and_updates_the_player(firestore_client, make_case):
    case = make_case()
    case_repository = FirestoreCaseRepository(client=firestore_client)
    case_repository.save(case)

    player_repository = FirestorePlayerRepository(client=firestore_client)
    player_repository.save(Player(player_id="player-1"))

    hint_request_repository = FirestoreHintRequestRepository(client=firestore_client)
    attempt_repository = FirestoreAttemptRepository(client=firestore_client)

    use_case = SubmitSolution(
        case_repository, player_repository, hint_request_repository, attempt_repository
    )
    result = use_case.execute(case.case_id, "player-1", "suspect_3")

    assert result.correct is True
    assert result.score == 100

    attempts = list(firestore_client.collection("case_attempts").stream())
    assert len(attempts) == 1
    assert attempts[0].to_dict()["playerId"] == "player-1"
    assert attempts[0].to_dict()["correct"] is True

    assert player_repository.get("player-1").total_score == 100


@requires_firestore_emulator
def test_request_hint_persists_a_hint_request(firestore_client, make_case):
    case = make_case()
    case_repository = FirestoreCaseRepository(client=firestore_client)
    case_repository.save(case)

    player_repository = FirestorePlayerRepository(client=firestore_client)
    player_repository.save(Player(player_id="player-1"))

    hint_request_repository = FirestoreHintRequestRepository(client=firestore_client)
    # Fake assistant — this test is about persistence wiring, not AI; the
    # fallback path is exercised deliberately so no OPENAI_API_KEY is needed.
    assistant = FakeHintAssistant(None)

    use_case = RequestHint(case_repository, hint_request_repository, assistant, player_repository)
    result = use_case.execute(case.case_id, "player-1")

    assert result.hints_used == 1

    records = list(firestore_client.collection("hint_requests").stream())
    assert len(records) == 1
    assert records[0].to_dict()["playerId"] == "player-1"
