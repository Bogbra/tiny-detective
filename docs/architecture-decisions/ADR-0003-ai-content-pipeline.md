# ADR-0003: AI Content Pipeline (Generation, Evaluation, Draft Storage)

## Status

Accepted

## Context

The project spec requires AI-generated cases to pass through schema validation, rule-based validation, logic consistency evaluation, safety evaluation, and difficulty evaluation before ever becoming a draft — and its strategic goal explicitly says "AI **and** rule-based evaluators", not "AI evaluators for everything". The pipeline needs to be genuinely testable in CI without needing a live API key or spending money on every test run, while still doing real semantic judgment where rules can't.

## Decision

Split the pipeline stages by what they actually need:

- **Schema Parser** and **Rule-Based Validator** (`tools/ai-content/ai_content/{schema_parser,rule_validator}.py`) are pure Python — no AI call. The rule validator also runs a cheap keyword denylist as a first line of defense against unsafe content, on top of (not instead of) the AI safety judge.
- **Logic Consistency Evaluator** and **Safety Evaluator** are AI-judged (OpenAI, `gpt-4o-mini` by default) — these require semantic judgment ("is this solvable", "is this actually safe") that rules can't reliably capture. Both are defined as `Protocol` interfaces (`ai_content/evaluators.py`) with a real `OpenAI*Evaluator` implementation and, in tests, a hand-rolled fake — the same port/adapter pattern already used for the backend's repositories (`services/api/app/application/ports.py`) and the Flutter app's `CaseRepository`.
- **Difficulty Evaluator** is a heuristic (`difficulty_evaluator.py`) — the project spec's own criteria (clue count, suspect count) are structural enough that an AI call would be overkill.
- **Draft storage** is local JSON files (`tools/ai-content/drafts/`, gitignored) standing in for the eventual Firestore `cases` collection — consistent with Phase 3's in-memory repositories standing in for Firestore before Phase 7.

`tools/ai-content` is its own `uv` project, separate from `services/api` — the backend never needs the OpenAI SDK; only offline tooling calls AI providers directly, per the project spec's "Flutter app must never call AI provider APIs directly" rule extended to its logical conclusion for the backend too (AI calls live in `tools/ai-content` or admin-only backend endpoints, not scattered around).

Provider choice: OpenAI (`OPENAI_API_KEY`), chosen by the project owner. Nothing about the pipeline design is OpenAI-specific — swapping providers means reimplementing `OpenAICaseGenerator`/`OpenAISafetyEvaluator`/`OpenAILogicConsistencyEvaluator` behind the same interfaces.

## Consequences

- `pytest` in `tools/ai-content` runs fully offline, deterministically, for free — verified by running the suite with no `OPENAI_API_KEY` set at all.
- A separate script, `evaluate_cases.py`, exists specifically to spend real API calls sanity-checking the AI judges' quality against `evals/golden_cases.json` and `evals/invalid_cases.json` — this is a manual eval-quality tool, not part of CI, and costs money each time it's run.
- Some overlap exists between this pipeline's rule-based checks (e.g. "exactly one culprit", "no duplicate suspects") and the backend's `CaseConsistencyPolicy` (Phase 2) — not extracted into a shared package, since the two operate on different data shapes (raw AI candidate JSON here vs. parsed `DetectiveCase` domain entities there) and the overlap is small enough that extraction now would be premature.
- `import_cases.py` and `publish_case.py` (named in the project spec's monorepo structure) are **not built yet** — there's nothing for them to import into until Phase 7 gives the backend a real persistent repository. Building them against the in-memory repository now would mean rebuilding them again in Phase 7 for no benefit.

## Addendum: judge quality measurement and per-role prompt versioning

Added after review — "the pipeline runs" says nothing about whether the AI judges are actually any good at their job:

- `evaluate_cases.py` was rewritten from a single-pass sanity check into a real measurement: precision/recall/specificity against `evals/golden_cases.json` and `evals/invalid_cases.json`, each fixture run `--repeats` times at `temperature=0` to catch run-to-run instability (an LLM judge is not guaranteed deterministic even at `temperature=0`), plus token-cost tracking. Both AI evaluators now default to `temperature=0.0` in production too, not just for this measurement — a judge used as a gate should not be flipping its verdict between otherwise-identical calls. Results are written to `evals/eval_baseline.json`, **committed to the repo** (not gitignored) as a regression baseline for judge quality, the same way a snapshot test's baseline is committed — rerun after any prompt change and diff against it.
- The draft record now tracks `promptVersions: {generator, logic, safety}` instead of a single generic `promptVersion` string. The project spec's Firestore schema only has one `promptVersion` field, but three distinct prompts are actually involved in judging one candidate — if judge output quality shifts, a single field can't tell you whether the generator's prompt or a specific judge's prompt caused it. Each evaluator/generator now exposes its own `prompt_version` (derived from its prompt filename); the pipeline reads it directly off the evaluator instances that were actually used (`getattr(..., "prompt_version", None)`) rather than trusting the caller to pass the right string.
- The rule-based keyword denylist's docstring and `docs/ai-workflow.md` were both made more explicit that it is a coarse pre-filter, not the safety mechanism — passing the rules stage means "not obviously bad", not "judged safe"; only a safety-evaluator pass means the latter.

## Addendum 2: expanded golden set, safety prompt v1 → v2, and a note on judge reliability

The first `evaluate_cases.py` run (2 golden cases) found the real logic judge correctly rejecting the original `museum_key` fixture for relying on an unstated premise and an ambiguous clue — a genuine golden-dataset defect, not a judge bug (see `evals/golden_cases.json`'s `museum_key` entry for the repaired version and its `note` field). But n=2 golden cases is too small to draw any conclusion beyond "one fixture was wrong" — recall at that sample size is closer to an anecdote than a rate. The golden set was expanded to 8 cases, tagged by `tier`: 4 "airtight" (every suspect's alibi is either directly confirmed or directly implicated by an explicitly-stated fact) and 4 "casual" (fair, ordinary inference, the game's actual intended difficulty). `evaluate_cases.py` now reports `recall[tier]` separately so a future regression can be localized to a specific evidence style instead of only a blended number.

Measuring against the 8-case set surfaced a second, different finding: the **safety** judge, not the logic judge, rejected 2 of 4 airtight-tier cases (`office_plant_contest`, `birthday_cake_topper`) — reasons given were "implies theft of a harmless object" and "suspect has a motive", which describes the mystery genre's core mechanic, not an actual safety violation. `birthday_cake_topper` was additionally unstable at `temperature=0` (2 rejects, 1 accept across 3 identical calls). The v1 safety prompt (`evaluate_case_safety_v1.md`) already stated "harmless mischief" was acceptable — the model applied that instruction inconsistently rather than ignoring it outright, since the same evidence pattern ("physical trace tying a suspect to a harmless act") passed cleanly in the casual-tier fixtures. This was diagnosed as a prompt-compliance gap: a rule stated once, abstractly, was followed unreliably at the margin.

**Fix**: `evaluate_case_safety_v2.md` — same rejection categories, but adds explicit paired accept/reject examples (an accepted "suspect secretly took a harmless object, evidence ties them to it" vs. a rejected "suspect physically harmed someone"), on the general principle that a rule stated with a positive and a negative example is followed more reliably than the same rule stated as an abstract sentence. Kept deliberately narrow — the goal was to stop over-rejecting the genre's core mechanic, not to loosen the actual safety boundary. `OpenAISafetyEvaluator.PROMPT_FILE` now points at `_v2`; `_v1` is left untouched as the historical artifact the first baseline was measured against, per this ADR's own prompt-versioning discipline — editing `_v1` in place would have made the existing `eval_baseline.json`'s `promptVersions: {safety: "evaluate_case_safety_v1"}` field silently wrong.

Before/after, full 15-fixture set (`evals/eval_baseline.json`):

| | precision | recall | recall[airtight] | recall[casual] | specificity | unstable |
|---|---|---|---|---|---|---|
| v1 | 1.00 | 0.75 | 0.50 (n=4) | 1.00 (n=4) | 1.00 | `birthday_cake_topper` |
| v2 | 1.00 | 1.00 | 1.00 (n=4) | 1.00 (n=4) | 1.00 | none |

Precision and specificity did not move — the fix raised recall without loosening the actual gate; every invalid-case fixture, including the two built specifically to trip the logic judge (`hidden_only_solution`, `ambiguous_equally_likely_suspects`), still rejects 100% of the time. The two previously-failing fixtures were re-run individually at `--repeats 10` under v2 and came back 10/10 stable each, confirming this isn't a lucky roll at the default `--repeats 3`.

**Structural note, not yet built**: `birthday_cake_topper`'s instability was resolved by the prompt fix here, but the risk it exposed is general — any LLM judge used as a single-call gate can land on a decision boundary where a small fraction of calls disagree, and `temperature=0` reduces but does not eliminate this. A more robust architecture for a judge gating product quality would take an odd-numbered majority vote (e.g. 3 calls, 2-of-3 wins, a tie counts as reject) instead of trusting a single call. `OpenAISafetyEvaluator`/`OpenAILogicConsistencyEvaluator` still make exactly one call per `evaluate()` today — worth revisiting if `evaluate_cases.py` surfaces instability again on a future prompt or model change.
