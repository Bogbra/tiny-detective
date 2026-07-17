import uuid

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from app.domain.entities.hint_request import HintRequest
from app.domain.value_objects.case_id import CaseId
from app.infrastructure.firestore.firestore_client import get_firestore_client
from app.infrastructure.firestore.hint_request_mapper import hint_request_to_document

HINT_REQUESTS_COLLECTION = "hint_requests"


class FirestoreHintRequestRepository:
    def __init__(self, client: firestore.Client | None = None) -> None:
        self._client = client or get_firestore_client()

    def count_for_case(self, case_id: CaseId, player_id: str) -> int:
        query = (
            self._client.collection(HINT_REQUESTS_COLLECTION)
            .where(filter=FieldFilter("caseId", "==", case_id.value))
            .where(filter=FieldFilter("playerId", "==", player_id))
        )
        return sum(1 for _ in query.stream())

    def record(self, hint_request: HintRequest) -> None:
        doc_id = hint_request.hint_request_id or str(uuid.uuid4())
        self._client.collection(HINT_REQUESTS_COLLECTION).document(doc_id).set(
            hint_request_to_document(hint_request)
        )
