from app.contracts.base import ApiModel


class SubmitSolutionResponse(ApiModel):
    correct: bool
    score: int
    feedback: str
    solution_explanation: str
    streak: int
    already_solved: bool
