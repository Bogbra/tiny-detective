from app.contracts.base import ApiModel


class SuspectResponse(ApiModel):
    suspect_id: str
    name: str
    role: str
    public_statement: str


class ClueResponse(ApiModel):
    clue_id: str
    text: str


class CaseResponse(ApiModel):
    case_id: str
    title: str
    setting: str
    problem: str
    suspects: list[SuspectResponse]
    clues: list[ClueResponse]
    difficulty: str
