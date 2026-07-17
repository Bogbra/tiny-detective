class DomainError(Exception):
    """Base class for domain-level errors."""


class UnknownSuspectError(DomainError):
    """Raised when a submitted suspect id does not belong to the case."""
