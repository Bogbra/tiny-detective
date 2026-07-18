"""Local JSON "draft repository" — stands in for the Firestore `cases`
collection until Phase 7 wires that up. Only cases that pass every pipeline
stage get saved here, always with status "draft" (see pipeline.py) — nothing
generated ever becomes directly approved/live.
"""

import json
import uuid
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from .models import CaseCandidate

DEFAULT_DRAFTS_DIR = Path(__file__).resolve().parent.parent / "drafts"


class DraftStore:
    def __init__(self, directory: Path | None = None) -> None:
        self._directory = directory or DEFAULT_DRAFTS_DIR
        self._directory.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        candidate: CaseCandidate,
        *,
        difficulty: str,
        model: str | None,
        generator_prompt_version: str | None,
        logic_prompt_version: str | None,
        safety_prompt_version: str | None,
    ) -> Path:
        """Records which prompt version judged this candidate, not just which
        generated it. The project spec's Firestore schema has a single generic
        `promptVersion` field, but three distinct prompts are involved here
        (generate/logic/safety) — if judge quality shifts, this is what lets
        you tell whether the generator or a specific judge's prompt caused it.
        """
        generation_id = str(uuid.uuid4())
        culprit = next(s for s in candidate.suspects if s.is_culprit)
        record = {
            "generationId": generation_id,
            "status": "draft",
            "title": candidate.title,
            "setting": candidate.setting,
            "problem": candidate.problem,
            "suspects": [asdict(s) for s in candidate.suspects],
            "clues": [asdict(c) for c in candidate.clues],
            "solution": {
                "culpritSuspectId": culprit.suspect_id,
                "explanation": candidate.solution_explanation,
            },
            "difficulty": difficulty,
            "model": model,
            "promptVersions": {
                "generator": generator_prompt_version,
                "logic": logic_prompt_version,
                "safety": safety_prompt_version,
            },
            "createdAt": datetime.now(UTC).isoformat(),
        }
        path = self._directory / f"{generation_id}.json"
        path.write_text(json.dumps(record, indent=2))
        return path

    def list_drafts(self) -> list[dict]:
        return [json.loads(p.read_text()) for p in sorted(self._directory.glob("*.json"))]
