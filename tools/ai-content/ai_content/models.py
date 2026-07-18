from dataclasses import dataclass
from typing import TypedDict


class TokenUsage(TypedDict):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass(frozen=True, slots=True)
class CandidateSuspect:
    suspect_id: str
    name: str
    role: str
    public_statement: str
    private_reasoning: str
    is_culprit: bool


@dataclass(frozen=True, slots=True)
class CandidateClue:
    clue_id: str
    text: str


@dataclass(frozen=True, slots=True)
class CaseCandidate:
    """A parsed, normalized case candidate — the pipeline's internal shape.

    Assigns suspect_id/clue_id slugs during parsing since the raw AI output
    (the project spec's "AI Case Data Example") only has suspect names and plain
    clue strings, not stable ids yet.
    """

    title: str
    setting: str
    problem: str
    suspects: tuple[CandidateSuspect, ...]
    clues: tuple[CandidateClue, ...]
    solution_explanation: str
    difficulty: str | None = None
    tone: str | None = None
