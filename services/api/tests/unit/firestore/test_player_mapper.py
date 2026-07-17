from datetime import datetime, timezone

from app.domain.entities.player import Player
from app.infrastructure.firestore.player_mapper import document_to_player, player_to_document


def test_round_trip_preserves_all_fields():
    player = Player(
        player_id="player-1",
        display_name="Alex",
        streak=3,
        total_score=250,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        last_played_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )

    document = player_to_document(player)
    restored = document_to_player(player.player_id, document)

    assert restored == player


def test_document_uses_camel_case_field_names():
    player = Player(player_id="player-1")

    document = player_to_document(player)

    assert set(document.keys()) == {"displayName", "streak", "totalScore", "createdAt", "lastPlayedAt"}


def test_missing_optional_fields_default_sensibly():
    restored = document_to_player("player-2", {})

    assert restored.streak == 0
    assert restored.total_score == 0
    assert restored.display_name is None
