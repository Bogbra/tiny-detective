from datetime import UTC, datetime

from google.cloud import firestore

from app.domain.entities.detective_case import DetectiveCase
from app.domain.value_objects.case_id import CaseId
from app.infrastructure.firestore.case_mapper import case_to_document, document_to_case
from app.infrastructure.firestore.firestore_client import get_firestore_client

CASES_COLLECTION = "cases"
DAILY_CASES_COLLECTION = "daily_cases"


class FirestoreCaseRepository:
    """Real `cases/{caseId}` + `daily_cases/{yyyy-mm-dd}` collections, per
    the project spec's Firestore Data Model — a date-keyed daily-case history, more
    faithful to the spec than the in-memory repository's single pointer.
    """

    def __init__(self, client: firestore.Client | None = None) -> None:
        self._client = client or get_firestore_client()

    def get(self, case_id: CaseId) -> DetectiveCase | None:
        doc = self._client.collection(CASES_COLLECTION).document(case_id.value).get()
        if not doc.exists:
            return None
        return document_to_case(case_id.value, doc.to_dict())

    def get_daily(self) -> DetectiveCase | None:
        today = datetime.now(UTC).date().isoformat()
        daily_doc = self._client.collection(DAILY_CASES_COLLECTION).document(today).get()
        if not daily_doc.exists:
            return None
        return self.get(CaseId(daily_doc.to_dict()["caseId"]))

    def set_daily(self, case_id: CaseId) -> None:
        today = datetime.now(UTC).date().isoformat()
        self._client.collection(DAILY_CASES_COLLECTION).document(today).set(
            {
                "caseId": case_id.value,
                "publishedAt": datetime.now(UTC),
            }
        )

    def save(self, case: DetectiveCase) -> None:
        self._client.collection(CASES_COLLECTION).document(case.case_id.value).set(case_to_document(case))

    def list_all(self) -> list[DetectiveCase]:
        return [
            document_to_case(doc.id, doc.to_dict())
            for doc in self._client.collection(CASES_COLLECTION).stream()
        ]
