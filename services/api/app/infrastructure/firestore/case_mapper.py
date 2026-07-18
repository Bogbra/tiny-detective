"""Pure DetectiveCase <-> Firestore document mapping — no Firestore
connection needed to test this. Field names match the project spec's Firestore
`cases/{caseId}` schema (camelCase).
"""

from app.domain.entities.clue import Clue
from app.domain.entities.detective_case import DetectiveCase
from app.domain.entities.solution import Solution
from app.domain.entities.suspect import Suspect
from app.domain.value_objects.case_id import CaseId
from app.domain.value_objects.difficulty import Difficulty
from app.domain.value_objects.publish_status import PublishStatus


def case_to_document(case: DetectiveCase) -> dict:
    return {
        "title": case.title,
        "setting": case.setting,
        "problem": case.problem,
        "suspects": [
            {
                "suspectId": s.suspect_id,
                "name": s.name,
                "role": s.role,
                "publicStatement": s.public_statement,
                "isCulprit": s.is_culprit,
                "privateReasoning": s.private_reasoning,
                "personality": s.personality,
            }
            for s in case.suspects
        ],
        "clues": [
            {
                "clueId": c.clue_id,
                "text": c.text,
                "relevance": c.relevance,
                "relatedSuspectIds": list(c.related_suspect_ids),
                "unlockOrder": c.unlock_order,
            }
            for c in case.clues
        ],
        "solution": {
            "culpritSuspectId": case.solution.culprit_suspect_id,
            "explanation": case.solution.explanation,
            "requiredClueIds": list(case.solution.required_clue_ids),
        },
        "difficulty": case.difficulty.value,
        "locale": case.locale,
        "status": case.status.value,
        "createdAt": case.created_at,
        "updatedAt": case.updated_at,
        "source": case.source,
    }


def document_to_case(case_id_value: str, data: dict) -> DetectiveCase:
    suspects = tuple(
        Suspect(
            suspect_id=s["suspectId"],
            name=s["name"],
            role=s["role"],
            public_statement=s["publicStatement"],
            is_culprit=s["isCulprit"],
            private_reasoning=s.get("privateReasoning"),
            personality=s.get("personality"),
        )
        for s in data["suspects"]
    )
    clues = tuple(
        Clue(
            clue_id=c["clueId"],
            text=c["text"],
            relevance=c.get("relevance"),
            related_suspect_ids=tuple(c.get("relatedSuspectIds") or ()),
            unlock_order=c.get("unlockOrder", 0),
        )
        for c in data["clues"]
    )
    solution = Solution(
        culprit_suspect_id=data["solution"]["culpritSuspectId"],
        explanation=data["solution"]["explanation"],
        required_clue_ids=tuple(data["solution"].get("requiredClueIds") or ()),
    )
    return DetectiveCase(
        case_id=CaseId(case_id_value),
        title=data["title"],
        setting=data["setting"],
        problem=data["problem"],
        suspects=suspects,
        clues=clues,
        solution=solution,
        difficulty=Difficulty(data["difficulty"]),
        locale=data.get("locale", "en"),
        status=PublishStatus(data["status"]),
        created_at=data.get("createdAt"),
        updated_at=data.get("updatedAt"),
        source=data.get("source", "curated"),
    )
