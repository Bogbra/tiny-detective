import dataclasses

from app.domain.entities.player import Player
from app.infrastructure.firestore.firestore_player_repository import FirestorePlayerRepository

from .conftest import requires_firestore_emulator


@requires_firestore_emulator
def test_save_and_get_round_trip(firestore_client):
    repo = FirestorePlayerRepository(client=firestore_client)
    player = Player(player_id="player-1", streak=2, total_score=150)

    repo.save(player)
    fetched = repo.get("player-1")

    assert fetched.streak == 2
    assert fetched.total_score == 150


@requires_firestore_emulator
def test_get_returns_none_for_unknown_player(firestore_client):
    repo = FirestorePlayerRepository(client=firestore_client)

    assert repo.get("does-not-exist") is None


@requires_firestore_emulator
def test_progress_updates_persist_across_saves(firestore_client):
    """Player progress persistence — read, update, save, confirm the NEW
    state is what's read back, same sequence SubmitSolution performs."""
    repo = FirestorePlayerRepository(client=firestore_client)
    repo.save(Player(player_id="player-1", streak=0, total_score=0))

    player = repo.get("player-1")
    repo.save(dataclasses.replace(player, streak=1, total_score=100))

    updated = repo.get("player-1")
    assert updated.streak == 1
    assert updated.total_score == 100
