# AI Workflow

## Case Generation Pipeline (Phase 5)

Location: `tools/ai-content` — a standalone offline tool (its own `uv` project), never called from `apps/game` or from `services/api`'s request path.

```text
generation (OpenAI)
  -> schema validation (pure Python)
  -> rule-based validation (pure Python, incl. a keyword safety pre-filter)
  -> logic consistency evaluation (OpenAI)
  -> safety evaluation (OpenAI)
  -> difficulty evaluation (heuristic)
  -> draft storage (local JSON, tools/ai-content/drafts/)
  -> approval / publishing (Phase 7 — needs a real backend repository)
```

Each stage short-circuits the next: a candidate that fails schema validation never reaches the AI evaluators, so a malformed or obviously-unsafe candidate costs zero API calls beyond generation. Only candidates that pass every stage get written to draft storage — nothing generated ever becomes a live case directly.

The rule-based stage's keyword denylist is a coarse, cheap pre-filter — it catches only literal banned words for free. It is **not** the safety mechanism; it exists so obviously bad content never spends an API call. The AI Safety Evaluator is the actual judge of what's safe. See `ai_content/rule_validator.py`'s module docstring.

### Provider

OpenAI (`gpt-4o-mini` by default, `temperature=0.0` by default for both AI-judged evaluators — see below), read from the `OPENAI_API_KEY` environment variable — never logged, never hardcoded. See [ADR-0003](architecture-decisions/ADR-0003-ai-content-pipeline.md) for why only the Logic Consistency and Safety evaluators are AI-judged (Schema/Rule/Difficulty stages are deterministic).

`ai_content/openai_client.py` loads `tools/ai-content/.env` automatically at import time (via `python-dotenv`) if present — a no-op otherwise. Copy `.env.example` to `.env` and fill in the key rather than exporting it every session; `.env` is gitignored.

### Running it

```bash
cd tools/ai-content
cp .env.example .env                # fill in OPENAI_API_KEY; loaded automatically, never logged
uv run generate_cases.py --count 3  # generate + evaluate + store as drafts
uv run evaluate_cases.py            # measure real judge quality against evals/ — see below
uv run pytest                       # automated tests — no API key needed, uses fake evaluators
```

### Judge quality: precision, recall, stability, cost

`temperature=0` does not make an LLM judge deterministic, and "it ran without crashing" says nothing about whether the judges actually catch bad content or wrongly reject good content. `evaluate_cases.py` measures this properly against `evals/golden_cases.json` (should be accepted) and `evals/invalid_cases.json` (should be rejected, including cases specifically designed to test the logic judge: `hidden_only_solution`, `ambiguous_equally_likely_suspects`):

- **Precision / recall / specificity** — a judge that rejects everything scores 100% on the invalid set and is still useless; precision and recall against *both* fixture sets is what actually tells you the gate works. The dangerous failure mode is a false positive: unsafe or inconsistent content getting *accepted*.
- **Stability** — each fixture is run `--repeats` times (default 3) at `temperature=0`; any run that disagrees with the others on the same fixture is flagged. A judge that flips its verdict across repeats on the same input isn't a reliable gate.
- **Cost** — tracks real token usage per call and estimates cost per candidate and for a 50-candidate batch (`gpt-4o-mini` list pricing, verify current pricing before trusting it).

The golden set (`evals/golden_cases.json`) is tagged by `tier`: `airtight` (every suspect's alibi is directly confirmed or directly implicated by an explicitly-stated fact) and `casual` (fair, ordinary inference — the game's actual intended difficulty). `evaluate_cases.py` reports `recall[tier]` separately, so a future regression can be localized instead of hiding in a blended number. Use `--only <fixture-name>` (repeatable) to re-run specific fixtures at a higher `--repeats` without touching the committed baseline (a partial `--only` run never overwrites `eval_baseline.json`).

Results are written to `evals/eval_baseline.json` — **committed to the repo**, not gitignored, since it's the actual regression baseline for the AI judges: rerun after any prompt change and diff the committed file against the new run's output to catch judge-quality regressions before they ship, the same way a snapshot test's baseline is committed. Exits non-zero if any candidate that should have been rejected was accepted.

Current committed baseline: precision=1.00, recall=1.00 (airtight=1.00 n=4, casual=1.00 n=4), specificity=1.00, 0 unstable fixtures, ~$0.0067 for the full 15-fixture run. See [ADR-0003](architecture-decisions/ADR-0003-ai-content-pipeline.md)'s second addendum for the full before/after story, including a safety-prompt fix (v1 → v2) this measurement found necessary.

### Prompts

Versioned under `tools/ai-content/prompts/`:

- `generate_case_v1.md` — case generation, enforces the cozy/family-safe tone and structural rules (3 suspects, 3–5 clues, exactly one culprit) directly in the prompt.
- `evaluate_case_logic_v1.md` — logic consistency judge (solvability, no hidden-only solutions, no equally-likely suspects).
- `evaluate_case_safety_v1.md` — safety judge, superseded by `_v2` in code (`OpenAISafetyEvaluator.PROMPT_FILE`) but kept as the historical artifact `eval_baseline.json`'s older runs were measured against — never edit a versioned prompt file in place, always bump the suffix.
- `evaluate_case_safety_v2.md` — current safety judge. Adds explicit accept/reject examples clarifying that a suspect secretly doing something minor and harmless is the mystery genre's core mechanic, not a safety violation — v1 rejected two golden cases for exactly this ("implies theft of a harmless object").

### What isn't built yet

`import_cases.py` and `publish_case.py` — bridging a local draft into the backend's actual case repository. Deferred to Phase 7, when the backend has a real persistent repository (Firestore) to import into instead of the in-memory one.

## AI Hint Assistant (Phase 6)

Location: `services/api/app/infrastructure/ai/` — unlike case generation, a hint request happens live inside a player's real-time API call, so this AI integration lives in the backend service itself, not the offline `tools/ai-content` tool. See [ADR-0004](architecture-decisions/ADR-0004-hint-assistant-guardrails.md) for the full design and why that's a deliberate departure from ADR-0003's "the backend never needs the OpenAI SDK."

```text
Player requests hint
  -> backend loads the case, checks the hint limit (Phase 2/3, unchanged)
  -> backend calls the AI with case.public_view() ONLY (no solution, no private data)
  -> AI returns {clueId, commentary}
  -> backend verifies clueId is a real clue in this case (else: fallback)
  -> backend scans commentary for any suspect name/role (else: fallback)
  -> backend returns the grounded hint, or the Phase 3 deterministic fallback
```

### Why the AI can't leak the solution

Three independent layers, not one check relied on alone:

1. **The AI never sees the solution or private suspect data.** It's given `case.public_view()` — the same type Phase 2 built to structurally omit `solution`/`is_culprit`/`private_reasoning`. It can't leak what it was never told, which is a stronger guarantee than "tell it the answer but instruct it not to say."
2. **Every hint is grounded in a real, existing clue.** The AI must return an existing `clueId`; an invented or wrong id is rejected before the hint is ever shown. The final hint text always embeds the clue's actual, server-controlled text — the AI's only free-form output is a short commentary sentence.
3. **The commentary is scanned for suspect names and roles** (`app/domain/policies/hint_guardrail_policy.py`, pure Python, no AI needed to check) before being shown. Names are always a violation. A role is a violation *unless* that exact role word is grounded in the specific clue this hint is about — e.g. commentary saying "the visitor wristband" when paired with the clue "a visitor wristband was found" is quoting already-public clue vocabulary, not identifying the suspect whose role is "Visitor"; the same word used referentially against an unrelated clue ("the curator's statement doesn't fit...") is not grounded and is rejected. Only the commentary is checked, never the clue text itself (already public, already on the player's screen).

Any failure at any point — no API key, network error, malformed response, ungrounded `clueId`, or a guardrail violation — returns the Phase 3 deterministic fallback hint (`FALLBACK_HINT_TEXT`). The hint endpoint never errors because of the AI.

Automated tests can never accidentally call the real API: `get_openai_client()` (both here and in `tools/ai-content`) raises if `PYTEST_CURRENT_TEST` is set, regardless of whether a real `.env` happens to exist on the machine running the tests.

### Running it

Requires `OPENAI_API_KEY` in `services/api/.env` (see `.env.example`) — unset is safe, the endpoint just always falls back.

```bash
cd services/api
uv run uvicorn app.main:app --reload
uv run pytest   # includes tests/unit/test_request_hint_use_case.py — fake assistant, no API key needed
```

### Prompt

`services/api/app/infrastructure/ai/prompts/generate_hint_v2.md` — deliberately kept backend-local rather than shared with `tools/ai-content/prompts/`, since `services/api` is an independently deployed container (see ADR-0004). `v1.md` is kept as the historical artifact, never edited in place. Instructs the model to pick one real `clueId` and write spoiler-free commentary, never naming a suspect or using a role to point at one — but clarifies that quoting a clue's own vocabulary is fine even if it overlaps with a role word, since `v1`'s blanket "never mention a role" combined with the guardrail also blocking roles unconditionally rejected a correctly-grounded hint in real testing (see ADR-0004's addendum).

### What isn't verified yet

No test has exercised the real OpenAI-backed assistant end-to-end in this project — `test_request_hint_use_case.py` proves the guardrail/fallback *orchestration* correctly using a fake assistant. Whether the real prompt reliably produces useful, well-grounded commentary (as opposed to just passing the structural checks) is unverified until manually checked against the real API, the same gap Phase 5 had before a key was provided.
