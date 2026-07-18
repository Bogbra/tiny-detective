#!/usr/bin/env python3
"""Measures the REAL OpenAI-based Logic Consistency and Safety judges against
evals/{golden,invalid}_cases.json.

This is not a "does it run" smoke test. A judge that rejects everything has
100% accuracy on the invalid set and is still useless — it would also reject
every good case. What matters is precision/recall against BOTH fixture sets,
and whether the judges are actually stable (LLM judges at temperature=0 are
not guaranteed deterministic; each fixture is run --repeats times and any
run-to-run disagreement is flagged).

Also tracks token usage and estimates cost per candidate and for a
50-candidate batch, and writes a machine-readable baseline to
evals/eval_baseline.json — rerun this after any prompt change and diff
against the previous baseline to catch judge-quality regressions.

Costs real API calls: len(fixtures) * repeats * 2 (logic + safety), though
fixtures that fail schema/rules validation never reach the AI judges at all
(the pipeline short-circuits), so the real call count is usually lower.

Requires OPENAI_API_KEY.

Usage:
    OPENAI_API_KEY=... uv run evaluate_cases.py [--repeats N] [--model gpt-4o-mini]
"""

import argparse
import json
import sys
import tempfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from ai_content.draft_store import DraftStore
from ai_content.openai_evaluators import (
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    OpenAILogicConsistencyEvaluator,
    OpenAISafetyEvaluator,
)
from ai_content.pipeline import CaseGenerationPipeline

EVALS_DIR = Path(__file__).resolve().parent / "evals"
DEFAULT_REPEATS = 3

# gpt-4o-mini list pricing (USD per 1M tokens) at time of writing. Verify
# against https://openai.com/api/pricing/ before trusting the cost estimate
# below — this constant will go stale.
PRICE_PER_1M_INPUT_TOKENS = 0.15
PRICE_PER_1M_OUTPUT_TOKENS = 0.60


def _run_once(logic_evaluator, safety_evaluator, candidate_json: dict, tmp_root: Path):
    pipeline = CaseGenerationPipeline(
        safety_evaluator=safety_evaluator,
        logic_evaluator=logic_evaluator,
        draft_store=DraftStore(Path(tempfile.mkdtemp(prefix="ai-content-eval-", dir=tmp_root))),
    )
    result = pipeline.process(candidate_json)

    tokens = {"prompt_tokens": 0, "completion_tokens": 0}
    for evaluator in (logic_evaluator, safety_evaluator):
        last = getattr(evaluator, "last_usage", None)
        if last:
            tokens["prompt_tokens"] += last["prompt_tokens"]
            tokens["completion_tokens"] += last["completion_tokens"]

    return result, tokens


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--repeats", type=int, default=DEFAULT_REPEATS)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--only",
        action="append",
        default=None,
        help="Fixture name to run (repeatable). Default: all fixtures. Does not "
        "overwrite eval_baseline.json when used, to avoid clobbering a full-set baseline "
        "with a partial one.",
    )
    args = parser.parse_args()

    golden = json.loads((EVALS_DIR / "golden_cases.json").read_text())
    invalid = json.loads((EVALS_DIR / "invalid_cases.json").read_text())

    if args.only:
        golden = [c for c in golden if c["name"] in args.only]
        invalid = [c for c in invalid if c["name"] in args.only]

    fixtures = [
        {
            "name": c["name"],
            "candidate": c["candidate"],
            "expected_accept": True,
            "expected_stage": None,
            "tier": c.get("tier"),
        }
        for c in golden
    ] + [
        {
            "name": c["name"],
            "candidate": c["candidate"],
            "expected_accept": False,
            "expected_stage": c.get("expected_failure_stage"),
            "tier": None,
        }
        for c in invalid
    ]

    per_fixture: list[dict] = []
    total_tokens = {"prompt_tokens": 0, "completion_tokens": 0}
    tp = fp = tn = fn = 0

    with tempfile.TemporaryDirectory(prefix="ai-content-eval-run-") as tmp_root_str:
        tmp_root = Path(tmp_root_str)

        for fixture in fixtures:
            verdicts: list[bool] = []
            stages: list[str | None] = []

            for _ in range(args.repeats):
                logic_evaluator = OpenAILogicConsistencyEvaluator(model=args.model)
                safety_evaluator = OpenAISafetyEvaluator(model=args.model)
                result, tokens = _run_once(logic_evaluator, safety_evaluator, fixture["candidate"], tmp_root)
                verdicts.append(result.accepted)
                stages.append(result.stage_failed)
                total_tokens["prompt_tokens"] += tokens["prompt_tokens"]
                total_tokens["completion_tokens"] += tokens["completion_tokens"]

            stable = len(set(verdicts)) == 1
            majority_accept = Counter(verdicts).most_common(1)[0][0]
            correct = majority_accept == fixture["expected_accept"]

            if fixture["expected_accept"] and majority_accept:
                tp += 1
            elif fixture["expected_accept"] and not majority_accept:
                fn += 1
            elif not fixture["expected_accept"] and majority_accept:
                fp += 1
            else:
                tn += 1

            # None (accepted) or "logic"/"safety" means it reached an AI judge;
            # "schema"/"rules" means the pipeline short-circuited before that.
            reached_ai = any(s not in ("schema", "rules") for s in stages)

            per_fixture.append(
                {
                    "name": fixture["name"],
                    "tier": fixture["tier"],
                    "expectedAccept": fixture["expected_accept"],
                    "expectedStage": fixture["expected_stage"],
                    "verdicts": verdicts,
                    "stagesFailed": stages,
                    "stable": stable,
                    "majorityAccept": majority_accept,
                    "correct": correct,
                    "reachedAiEvaluation": reached_ai,
                }
            )

            flag = "OK   " if correct else "WRONG"
            stability_note = "" if stable else "  ** UNSTABLE across repeats **"
            tier_note = f" [{fixture['tier']}]" if fixture["tier"] else ""
            print(
                f"[{flag}] {fixture['name']}{tier_note}: verdicts={verdicts} stages={stages}{stability_note}"
            )

    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    recall = tp / (tp + fn) if (tp + fn) else float("nan")
    specificity = tn / (tn + fp) if (tn + fp) else float("nan")

    golden_by_tier: dict[str, list[dict]] = {}
    for f in per_fixture:
        if f["tier"]:
            golden_by_tier.setdefault(f["tier"], []).append(f)
    recall_by_tier = {
        tier: sum(f["correct"] for f in items) / len(items) for tier, items in golden_by_tier.items()
    }

    total_token_count = total_tokens["prompt_tokens"] + total_tokens["completion_tokens"]
    cost_usd = (
        total_tokens["prompt_tokens"] / 1_000_000 * PRICE_PER_1M_INPUT_TOKENS
        + total_tokens["completion_tokens"] / 1_000_000 * PRICE_PER_1M_OUTPUT_TOKENS
    )
    total_candidate_runs = len(fixtures) * args.repeats
    cost_per_candidate = cost_usd / total_candidate_runs if total_candidate_runs else 0.0
    cost_per_50_batch = cost_per_candidate * 50

    unstable = [f["name"] for f in per_fixture if not f["stable"]]

    print("\n--- Summary ---")
    print(f"precision={precision:.2f}  recall={recall:.2f}  specificity={specificity:.2f}")
    print(f"tp={tp} fp={fp} tn={tn} fn={fn}  (fp = unsafe/inconsistent content ACCEPTED — the dangerous one)")
    for tier, tier_recall in sorted(recall_by_tier.items()):
        print(f"  recall[{tier}] = {tier_recall:.2f}  (n={len(golden_by_tier[tier])})")
    print(f"unstable fixtures: {unstable or 'none'}")
    print(
        f"tokens: {total_tokens['prompt_tokens']} prompt + {total_tokens['completion_tokens']} "
        f"completion = {total_token_count}"
    )
    print(
        f"estimated cost: ${cost_usd:.4f} this run, ~${cost_per_candidate:.5f}/candidate, "
        f"~${cost_per_50_batch:.2f} per 50-candidate batch "
        f"(gpt-4o-mini list pricing at time of writing — verify current pricing)"
    )

    if fp > 0:
        print(
            "\n*** WARNING: at least one unsafe or logically-inconsistent candidate was "
            "ACCEPTED. This is the dangerous failure mode — content that should have been "
            "rejected would have reached draft storage. Do not trust these judges in "
            "production until this is fixed. ***"
        )

    baseline = {
        "generatedAt": datetime.now(UTC).isoformat(),
        "model": args.model,
        "temperature": DEFAULT_TEMPERATURE,
        "repeatsPerFixture": args.repeats,
        "metrics": {
            "precision": None if precision != precision else precision,  # NaN -> null in JSON
            "recall": None if recall != recall else recall,
            "specificity": None if specificity != specificity else specificity,
            "truePositives": tp,
            "falsePositives": fp,
            "trueNegatives": tn,
            "falseNegatives": fn,
        },
        "recallByTier": recall_by_tier,
        "unstableFixtures": unstable,
        "tokenUsage": {
            "promptTokens": total_tokens["prompt_tokens"],
            "completionTokens": total_tokens["completion_tokens"],
            "totalTokens": total_token_count,
        },
        "estimatedCostUsd": {
            "thisRun": round(cost_usd, 4),
            "perCandidate": round(cost_per_candidate, 5),
            "per50CandidateBatch": round(cost_per_50_batch, 2),
            "pricingNote": (
                "gpt-4o-mini list pricing at time of writing — verify against "
                "https://openai.com/api/pricing/ before relying on this"
            ),
        },
        "fixtures": per_fixture,
    }

    if args.only:
        print("\n--only was used: eval_baseline.json NOT overwritten (partial run).")
    else:
        baseline_path = EVALS_DIR / "eval_baseline.json"
        baseline_path.write_text(json.dumps(baseline, indent=2))
        print(f"\nBaseline written to {baseline_path}")

    return 1 if fp > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
