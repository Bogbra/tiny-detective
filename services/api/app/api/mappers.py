from app.contracts.responses.case import CaseResponse, ClueResponse, SuspectResponse
from app.domain.entities.public_views import PublicDetectiveCase


def to_case_response(public_case: PublicDetectiveCase) -> CaseResponse:
    return CaseResponse(
        case_id=public_case.case_id,
        title=public_case.title,
        setting=public_case.setting,
        problem=public_case.problem,
        suspects=[
            SuspectResponse(
                suspect_id=s.suspect_id,
                name=s.name,
                role=s.role,
                public_statement=s.public_statement,
            )
            for s in public_case.suspects
        ],
        clues=[ClueResponse(clue_id=c.clue_id, text=c.text) for c in public_case.clues],
        difficulty=public_case.difficulty,
    )
