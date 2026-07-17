"""Redacted views of domain entities safe to return to players.

These types intentionally omit solution data and private suspect fields
(``is_culprit``, ``private_reasoning``, ``personality``) at the type level,
rather than relying on callers to remember to filter them out.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PublicSuspect:
    suspect_id: str
    name: str
    role: str
    public_statement: str


@dataclass(frozen=True, slots=True)
class PublicClue:
    clue_id: str
    text: str


@dataclass(frozen=True, slots=True)
class PublicDetectiveCase:
    case_id: str
    title: str
    setting: str
    problem: str
    suspects: tuple[PublicSuspect, ...]
    clues: tuple[PublicClue, ...]
    difficulty: str
