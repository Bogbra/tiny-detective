from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CaseId:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("CaseId must not be empty")
