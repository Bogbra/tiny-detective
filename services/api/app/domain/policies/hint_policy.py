class HintPolicy:
    def __init__(self, max_hints: int = 3) -> None:
        self.max_hints = max_hints

    def can_request_hint(self, hints_used: int) -> bool:
        return hints_used < self.max_hints

    def remaining_hints(self, hints_used: int) -> int:
        return max(0, self.max_hints - hints_used)
