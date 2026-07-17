#!/usr/bin/env python3
"""Generate new detective case candidates and run them through the evaluation
pipeline. Accepted candidates are stored as drafts (tools/ai-content/drafts/);
rejected ones are printed with the stage and reasons they failed.

Calls the real OpenAI API — requires OPENAI_API_KEY.

Usage:
    OPENAI_API_KEY=... uv run generate_cases.py [--count N] [--difficulty easy|medium|hard]
"""

import argparse
import sys

from ai_content.generator import GenerationError, OpenAICaseGenerator
from ai_content.openai_evaluators import OpenAILogicConsistencyEvaluator, OpenAISafetyEvaluator
from ai_content.pipeline import CaseGenerationPipeline


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--difficulty", choices=["easy", "medium", "hard"], default=None)
    args = parser.parse_args()

    generator = OpenAICaseGenerator()
    pipeline = CaseGenerationPipeline(
        safety_evaluator=OpenAISafetyEvaluator(),
        logic_evaluator=OpenAILogicConsistencyEvaluator(),
    )

    accepted = 0
    for i in range(args.count):
        try:
            raw = generator.generate(difficulty_hint=args.difficulty)
        except GenerationError as exc:
            print(f"[{i + 1}/{args.count}] generation failed: {exc}")
            continue

        result = pipeline.process(
            raw, model=generator.model, generator_prompt_version=generator.prompt_version
        )
        if result.accepted:
            accepted += 1
            print(f"[{i + 1}/{args.count}] accepted -> {result.draft_path}")
        else:
            print(f"[{i + 1}/{args.count}] rejected at '{result.stage_failed}': {list(result.reasons)}")

    print(f"\nDone: {accepted}/{args.count} case(s) accepted as drafts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
