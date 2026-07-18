"""Post-generation guardrail for AI hint text, per the project spec's AI Hint
Flow ("Backend evaluates hint against guardrails"). Deterministic and pure —
no AI call needed to check whether a hint text leaks who the culprit is.

The project spec's forbidden-hint examples are name/id-based ("Lea is the
culprit."), but those are examples, not an exhaustive definition — the
actual rule is "must not reveal the culprit," and a unique role (only one
"Curator" in the case) identifies a suspect just as precisely as their name
does. A hint like "the curator's statement doesn't fit the sensor evidence"
names no one and still fully identifies them. Roles ARE checked.

The earlier version of this policy checked roles unconditionally and was
narrowed to names-only after a real false positive: a clue's own wording
("a visitor wristband was found...") legitimately shares a word with a
role ("Visitor"), and commentary paraphrasing that clue ("the visitor
wristband...") isn't an accusation. Dropping role-checking entirely to fix
that was an overcorrection — it reopened exactly the identification gap
above. The precise fix distinguishes the two cases directly: a role mention
is only safe if it's grounded in the specific clue this hint is actually
about (`referenced_clue_text`) — i.e. the AI is quoting/paraphrasing
already-public clue vocabulary, not using the role to point at a suspect.
A role mention that does NOT appear in that clue's own text has no such
excuse and is treated as identifying.
"""

from dataclasses import dataclass

from app.domain.entities.detective_case import DetectiveCase


@dataclass(frozen=True, slots=True)
class GuardrailResult:
    passed: bool
    violated_identifiers: tuple[str, ...] = ()


class HintGuardrailPolicy:
    def check(self, hint_text: str, case: DetectiveCase, referenced_clue_text: str = "") -> GuardrailResult:
        lowered = hint_text.lower()
        referenced_clue_lowered = referenced_clue_text.lower()
        violated: list[str] = []

        for suspect in case.suspects:
            if suspect.name and suspect.name.lower() in lowered:
                violated.append(suspect.name)
                continue

            if suspect.role and suspect.role.lower() in lowered:
                if suspect.role.lower() not in referenced_clue_lowered:
                    violated.append(suspect.role)

        return GuardrailResult(passed=not violated, violated_identifiers=tuple(violated))
