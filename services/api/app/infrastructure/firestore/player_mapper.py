"""Pure Player <-> Firestore document mapping. Field names match the project spec's
`players/{playerId}` schema. Firestore's client natively round-trips Python
datetime objects as Firestore Timestamps — no manual serialization needed.
"""

from app.domain.entities.player import Player


def player_to_document(player: Player) -> dict:
    return {
        "displayName": player.display_name,
        "streak": player.streak,
        "totalScore": player.total_score,
        "createdAt": player.created_at,
        "lastPlayedAt": player.last_played_at,
    }


def document_to_player(player_id: str, data: dict) -> Player:
    return Player(
        player_id=player_id,
        display_name=data.get("displayName"),
        streak=data.get("streak", 0),
        total_score=data.get("totalScore", 0),
        created_at=data.get("createdAt"),
        last_played_at=data.get("lastPlayedAt"),
    )
