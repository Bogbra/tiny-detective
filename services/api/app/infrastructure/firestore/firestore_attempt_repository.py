import uuid

from google.cloud import firestore

from app.domain.entities.attempt import Attempt
from app.infrastructure.firestore.attempt_mapper import attempt_to_document
from app.infrastructure.firestore.firestore_client import get_firestore_client

CASE_ATTEMPTS_COLLECTION = "case_attempts"


class FirestoreAttemptRepository:
    def __init__(self, client: firestore.Client | None = None) -> None:
        self._client = client or get_firestore_client()

    def record(self, attempt: Attempt) -> None:
        doc_id = attempt.attempt_id or str(uuid.uuid4())
        self._client.collection(CASE_ATTEMPTS_COLLECTION).document(doc_id).set(
            attempt_to_document(attempt)
        )
