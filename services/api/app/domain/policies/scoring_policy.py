class ScoringPolicy:
    def __init__(self, max_score: int = 100, hint_penalty: int = 15, min_score: int = 10) -> None:
        self.max_score = max_score
        self.hint_penalty = hint_penalty
        self.min_score = min_score

    def calculate_score(self, *, correct: bool, hints_used: int) -> int:
        if not correct:
            return 0
        return max(self.min_score, self.max_score - hints_used * self.hint_penalty)
