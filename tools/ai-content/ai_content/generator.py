import json
from pathlib import Path

from .fidelity_checker import check_fidelity
from .logic_builder import CaseLogic
from .models import CandidateClue, CandidateSuspect, CaseCandidate, TokenUsage
from .openai_client import get_openai_client
from .prompts import load_prompt

DEFAULT_MODEL = "gpt-4o-mini"

# Unset previously meant the API default (~1.0) — high creative variance,
# which turned out to be a real cost, not a neutral choice: the live
# case-generation feature (services/api) measured a live production
# rejection rate far higher than a small pre-deployment sample suggested,
# and the SAME two logic-consistency failures every time ("solution depends
# on information not present in any clue", "two suspects equally
# supported"). Inspecting real generated candidates confirmed a genuine
# generator problem, not judge over-strictness: clues describing vague,
# unattributed sensory details ("a faint smell of vanilla") that
# solution.explanation then silently "matches" to the culprit — a fact
# introduced in the explanation, never actually in a clue. Lower
# temperature (less wandering) plus v2's explicit clue-authoring guidance
# are the fix — see ADR-0007's addendum and prompts/generate_case_v2.md.
DEFAULT_TEMPERATURE = 0.6


class GenerationError(Exception):
    pass


class PromptFidelityError(Exception):
    """The LLM's rendered prose dropped or paraphrased a required fact from
    the CaseLogic it was given — see fidelity_checker.check_fidelity. This
    is a real, expected-to-be-rare rejection reason for CaseProseRenderer,
    not a bug: the render prompt asks for verbatim phrases specifically so
    this is mechanically checkable."""

    def __init__(self, reasons: tuple[str, ...]) -> None:
        self.reasons = reasons
        super().__init__("; ".join(reasons))


class OpenAICaseGenerator:
    """Generates raw case candidate JSON. Not responsible for validation,
    approval, or publishing — the pipeline (ai_content/pipeline.py) owns that.
    """

    # v2: v1's clue-authoring guidance was too easy to satisfy without
    # actually grounding the solution in the clues themselves — see
    # DEFAULT_TEMPERATURE's comment above for the full diagnosis.
    PROMPT_FILE = "generate_case_v2.md"

    def __init__(self, model: str = DEFAULT_MODEL, temperature: float = DEFAULT_TEMPERATURE) -> None:
        self.model = model
        self.temperature = temperature
        self.prompt_version = Path(self.PROMPT_FILE).stem
        # Populated after each generate() call — previously only the two
        # evaluators tracked this; the live case-generation feature
        # (services/api) needs real, measured per-request cost across the
        # WHOLE pipeline including the generator call, not just the judges.
        # See evaluate_cases.py for the established read-.last_usage-after
        # pattern this mirrors.
        self.last_usage: TokenUsage | None = None

    def generate(self, *, difficulty_hint: str | None = None) -> dict:
        client = get_openai_client()
        user_prompt = "Generate one new detective case." + (
            f" Target difficulty: {difficulty_hint}." if difficulty_hint else ""
        )
        response = client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": load_prompt(self.PROMPT_FILE)},
                {"role": "user", "content": user_prompt},
            ],
        )
        self.last_usage = None
        if response.usage is not None:
            self.last_usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        content = response.choices[0].message.content
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise GenerationError(f"model did not return valid JSON: {exc}") from exc


def case_logic_to_prompt_json(case_logic: CaseLogic) -> dict:
    return {
        "settingSentence": case_logic.template.setting_sentence,
        "problemSentence": case_logic.template.problem_sentence,
        "missingItem": case_logic.template.missing_item,
        "incidentLocation": case_logic.template.incident_location,
        "suspects": [
            {
                "token": s.token,
                "role": s.role,
                "isCulprit": s.is_culprit,
                "claimedLocation": s.claimed_location,
                "signatureItem": s.signature_item,
            }
            for s in case_logic.suspects
        ],
        "clues": [
            {"clueId": c.clue_id, "kind": c.kind, "requiredPhrases": list(c.required_phrases)}
            for c in case_logic.clues
        ],
    }


def build_case_candidate_from_rendered(case_logic: CaseLogic, rendered: dict) -> CaseCandidate:
    # Identity (is_culprit, suspect ordering) comes entirely from case_logic
    # — never read from the LLM response, since the whole point of this
    # pipeline is that the LLM was never asked to decide it. Only prose
    # (name/publicStatement/privateReasoning/clue text/title/etc.) is read
    # from rendered.
    suspects_raw = rendered.get("suspects", [])
    names_by_token = {s.get("token"): s.get("name", "") for s in suspects_raw}
    statements_by_token = {s.get("token"): s.get("publicStatement", "") for s in suspects_raw}
    reasoning_by_token = {s.get("token"): s.get("privateReasoning", "") for s in suspects_raw}

    suspects = tuple(
        CandidateSuspect(
            suspect_id=f"suspect_{i}",
            name=names_by_token.get(s.token) or s.role,
            role=s.role,
            public_statement=statements_by_token.get(s.token, ""),
            private_reasoning=reasoning_by_token.get(s.token, ""),
            is_culprit=s.is_culprit,
        )
        for i, s in enumerate(case_logic.suspects, start=1)
    )

    clues_raw = rendered.get("clues", [])
    clue_text_by_id = {c.get("clueId"): c.get("text", "") for c in clues_raw}
    clues = tuple(
        CandidateClue(clue_id=f"clue_{i}", text=clue_text_by_id.get(c.clue_id, ""))
        for i, c in enumerate(case_logic.clues, start=1)
    )

    return CaseCandidate(
        title=rendered.get("title", ""),
        setting=rendered.get("setting", ""),
        problem=rendered.get("problem", ""),
        suspects=suspects,
        clues=clues,
        solution_explanation=rendered.get("solutionExplanation", ""),
        difficulty=None,
        tone="cozy",
    )


class CaseProseRenderer:
    """Phase 2 of the deterministic-logic pipeline (see logic_builder.py):
    takes an already-solved, already-verified CaseLogic and asks the LLM
    only to write prose around it — it cannot change who's guilty or which
    detail identifies them, since it's never asked to decide either. See
    ADR-0007's redesign addendum for why this replaces OpenAICaseGenerator
    for the live case-generation feature specifically.
    """

    PROMPT_FILE = "generate_case_v3.md"

    def __init__(self, model: str = DEFAULT_MODEL, temperature: float = DEFAULT_TEMPERATURE) -> None:
        self.model = model
        self.temperature = temperature
        self.prompt_version = Path(self.PROMPT_FILE).stem
        self.last_usage: TokenUsage | None = None

    def render(self, case_logic: CaseLogic) -> CaseCandidate:
        client = get_openai_client()
        response = client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": load_prompt(self.PROMPT_FILE)},
                {"role": "user", "content": json.dumps(case_logic_to_prompt_json(case_logic))},
            ],
        )
        self.last_usage = None
        if response.usage is not None:
            self.last_usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        content = response.choices[0].message.content
        try:
            rendered = json.loads(content)
        except json.JSONDecodeError as exc:
            raise GenerationError(f"model did not return valid JSON: {exc}") from exc

        fidelity = check_fidelity(case_logic, rendered)
        if not fidelity.passed:
            raise PromptFidelityError(fidelity.reasons)

        return build_case_candidate_from_rendered(case_logic, rendered)
