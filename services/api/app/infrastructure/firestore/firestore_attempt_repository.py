import uuid

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

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

    def exists_for(self, player_id: str, case_id: str) -> bool:
        # Two plain equality (==) filters on different fields — Firestore's
        # automatic single-field indexes cover this without a composite
        # index; one would only be needed if this also had a range filter
        # or an orderBy on a different field. No firestore.indexes.json
        # entry needed.
        query = (
            self._client.collection(CASE_ATTEMPTS_COLLECTION)
            .where(filter=FieldFilter("playerId", "==", player_id))
            .where(filter=FieldFilter("caseId", "==", case_id))
            .limit(1)
        )
        return next(query.stream(), None) is not None
