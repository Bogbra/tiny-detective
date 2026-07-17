from google.cloud import firestore

from app.domain.entities.player import Player
from app.infrastructure.firestore.firestore_client import get_firestore_client
from app.infrastructure.firestore.player_mapper import document_to_player, player_to_document

PLAYERS_COLLECTION = "players"


class FirestorePlayerRepository:
    def __init__(self, client: firestore.Client | None = None) -> None:
        self._client = client or get_firestore_client()

    def get(self, player_id: str) -> Player | None:
        doc = self._client.collection(PLAYERS_COLLECTION).document(player_id).get()
        if not doc.exists:
            return None
        return document_to_player(player_id, doc.to_dict())

    def save(self, player: Player) -> None:
        self._client.collection(PLAYERS_COLLECTION).document(player.player_id).set(
            player_to_document(player)
        )
