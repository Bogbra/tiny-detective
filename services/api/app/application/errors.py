class ApplicationError(Exception):
    """Base class for application-layer (use case) errors."""


class CaseNotFoundError(ApplicationError):
    pass


class PlayerNotFoundError(ApplicationError):
    pass


class HintLimitExceededError(ApplicationError):
    pass


class CaseNotInDraftError(ApplicationError):
    pass


class CaseNotPublishableError(ApplicationError):
    def __init__(self, violations: tuple[str, ...]) -> None:
        self.violations = violations
        super().__init__(f"case is not publishable: {list(violations)}")


class NoPublishableCaseError(ApplicationError):
    pass
