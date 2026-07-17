# AI Content Tools

Offline tooling for the AI case generation pipeline: generating detective case candidates and running them through schema/rule/logic/safety/difficulty evaluation before they become drafts. Its own `uv` project, separate from `services/api` — see [`docs/ai-workflow.md`](../../docs/ai-workflow.md) and [ADR-0003](../../docs/architecture-decisions/ADR-0003-ai-content-pipeline.md) for the full design.

## Setup

```bash
cd tools/ai-content
uv sync
cp .env.example .env   # fill in OPENAI_API_KEY — loaded automatically (ai_content/openai_client.py), gitignored
```

Required for `generate_cases.py` / `evaluate_cases.py` only — `uv run pytest` doesn't need it (uses fake evaluators).

## Usage

```bash
uv run generate_cases.py --count 3 [--difficulty easy|medium|hard]   # generate + evaluate + store as drafts
uv run evaluate_cases.py [--repeats 3] [--model gpt-4o-mini]         # measure judge precision/recall/stability/cost — real API calls
uv run pytest                                                        # automated tests — no API key needed
```

Accepted cases are written to `drafts/` (gitignored, local-only). `import_cases.py` and `publish_case.py` — bridging drafts into the real backend — land in Phase 7 once there's a persistent repository to import into.

`evaluate_cases.py` is not a smoke test — it measures whether the real OpenAI-based Logic Consistency and Safety judges actually work: precision/recall against `evals/golden_cases.json` and `evals/invalid_cases.json`, run-to-run stability (each fixture repeated `--repeats` times), and token cost. Writes `evals/eval_baseline.json`, **committed to the repo** as a regression baseline — rerun after any prompt change and diff against the committed baseline. See [`docs/ai-workflow.md`](../../docs/ai-workflow.md#judge-quality-precision-recall-stability-cost).

## Layout

```text
ai_content/          pipeline package (schema parser, rule validator, AI evaluators, generator, draft store)
prompts/              versioned prompt templates (generate_case_v1.md, evaluate_case_logic_v1.md, evaluate_case_safety_v1.md)
evals/                golden_cases.json / invalid_cases.json fixtures, eval_baseline.json (committed baseline from evaluate_cases.py)
tests/                automated tests — use hand-rolled fakes for the AI evaluators, never call the real API
```
