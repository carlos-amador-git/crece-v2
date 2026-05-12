"""Continuous improvement loop orchestrator.

For each iteration:
    1. Runs the current prompt version through selected providers
    2. Scores outputs with rubric
    3. Generates a compare_N.md
    4. Exits — the next iteration's prompt (v{N+1}.md) is written by a human or
       a second-stage agent that reads the compare report

This script does NOT auto-edit prompts. The human-in-the-loop step is
intentional: the rubric is a metric, not a generator.

Usage:
    python -m benchmarks.ai.loop \
        --prompts-dir prompts \
        --test-case test_cases/alejandro_pina_diagnostico.json \
        --providers offline \
        --max-iterations 3
"""

from __future__ import annotations

import argparse
import asyncio
import re
from datetime import datetime
from pathlib import Path

from benchmarks.ai.compare import compare
from benchmarks.ai.runner import run

BASE = Path(__file__).parent


def _list_prompt_versions(prompts_dir: Path, stem: str) -> list[Path]:
    """Return prompt files matching stem_v*.md, sorted by version number."""
    pattern = re.compile(rf"{re.escape(stem)}_v(\d+)\.md$")
    versioned = []
    for p in prompts_dir.iterdir():
        m = pattern.match(p.name)
        if m:
            versioned.append((int(m.group(1)), p))
    versioned.sort()
    return [p for _, p in versioned]


async def run_loop(
    prompts_dir: Path,
    test_case: Path,
    providers: list[str],
    max_iterations: int,
    stem: str = "diagnostico",
) -> None:
    versions = _list_prompt_versions(prompts_dir, stem)
    if not versions:
        raise SystemExit(f"No hay prompts con prefijo '{stem}_v' en {prompts_dir}")

    date_str = datetime.now().strftime("%Y-%m-%d")
    out_dir = BASE / "outputs" / date_str
    out_dir.mkdir(parents=True, exist_ok=True)

    for i, prompt_path in enumerate(versions[:max_iterations]):
        print(f"\n=== Iteración {i} — {prompt_path.name} ===")
        results = await run(
            prompt_path=prompt_path,
            test_case_path=test_case,
            providers=providers,
            iteration=i,
            out_dir=out_dir,
        )
        if results:
            compare(
                test_case_path=test_case,
                output_paths=list(results.values()),
                out_path=out_dir / f"compare_{i:02d}.md",
            )

    print(f"\n=== Loop terminado. Resultados en {out_dir} ===")
    print("Próximo paso: revisa compare_NN.md, edita el prompt a v{N+1}, re-ejecuta.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompts-dir", type=Path, default=BASE / "prompts")
    parser.add_argument("--test-case", type=Path, required=True)
    parser.add_argument("--providers", default="offline")
    parser.add_argument("--max-iterations", type=int, default=3)
    parser.add_argument("--stem", default="diagnostico")
    args = parser.parse_args()

    providers = [p.strip() for p in args.providers.split(",") if p.strip()]
    asyncio.run(run_loop(
        prompts_dir=args.prompts_dir,
        test_case=args.test_case,
        providers=providers,
        max_iterations=args.max_iterations,
        stem=args.stem,
    ))


if __name__ == "__main__":
    main()
