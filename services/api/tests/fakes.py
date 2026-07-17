from app.application.ports import AssistantHint


class FakeHintAssistant:
    """Hand-rolled test double — avoids a mocking package for one small interface.

    Shared between tests/unit (use-case orchestration tests) and
    tests/contract (so contract tests never hit the real OpenAI API, even
    if a real OPENAI_API_KEY happens to be present in the environment
    running the tests — test behavior and cost must not depend on that).
    """

    def __init__(self, hint: AssistantHint | None = None) -> None:
        self.hint = hint
        self.calls = 0
        self.last_public_case = None
        self.last_hint_level: int | None = None

    def generate_hint(self, public_case, hint_level):
        self.calls += 1
        self.last_public_case = public_case
        self.last_hint_level = hint_level
        return self.hint
