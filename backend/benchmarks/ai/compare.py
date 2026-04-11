"""Side-by-side comparison of benchmark outputs with rubric scoring.

Usage:
    python -m benchmarks.ai.compare \
        --test-case test_cases/alejandro_pina_diagnostico.json \
        --outputs outputs/2026-04-11/iter_01_ollama.md,outputs/2026-04-11/iter_01_claude.md \
        --out outputs/2026-04-11/compare_01.md
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from benchmarks.ai.rubric import score_output


def compare(test_case_path: Path, output_paths: list[Path], out_path: Path) -> None:
    test_case = json.loads(test_case_path.read_text(encoding="utf-8"))

    lines: list[str] = [
        f"# Benchmark Compare — {test_case_path.stem}",
        "",
        f"**Test case:** `{test_case_path.name}`",
        f"**Outputs comparados:** {len(output_paths)}",
        "",
        "## Scores por rúbrica",
        "",
        "| Output | Total | Coverage | Specificity | Factual | Compliance | Length | Hallucinations |",
        "|--------|-------|----------|-------------|---------|------------|--------|----------------|",
    ]

    results = []
    for p in output_paths:
        if not p.exists():
            lines.append(f"| {p.name} | ERROR: file missing | - | - | - | - | - | - |")
            continue
        text = p.read_text(encoding="utf-8")
        r = score_output(text, test_case)
        results.append((p, r))
        bd = r.breakdown
        lines.append(
            f"| `{p.name}` | **{r.total}** | {bd['coverage']} | {bd['specificity']} "
            f"| {bd['factual']} | {bd['compliance']} | {bd['length']} | {bd['hallucinations']} |"
        )

    lines.append("")
    lines.append("## Notas por output")
    lines.append("")
    for p, r in results:
        lines.append(f"### {p.name}")
        for note in r.notes:
            lines.append(f"- {note}")
        lines.append("")

    if len(results) >= 2:
        baseline, reference = results[0], results[-1]
        gap = reference[1].total - baseline[1].total
        lines.append("## Gap análisis")
        lines.append("")
        lines.append(f"- **Baseline:** `{baseline[0].name}` = {baseline[1].total}")
        lines.append(f"- **Referencia:** `{reference[0].name}` = {reference[1].total}")
        lines.append(f"- **Brecha:** {gap:+.1f} puntos")
        lines.append("")
        lines.append("### Dimensiones donde baseline está más atrás")
        deltas = {
            k: reference[1].breakdown[k] - baseline[1].breakdown[k]
            for k in baseline[1].breakdown
        }
        for k, v in sorted(deltas.items(), key=lambda kv: kv[1], reverse=True):
            lines.append(f"- `{k}`: {v:+.1f}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-case", required=True, type=Path)
    parser.add_argument("--outputs", required=True, type=str,
                        help="comma-separated list of output markdown files")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    output_paths = [Path(p.strip()) for p in args.outputs.split(",") if p.strip()]
    compare(args.test_case, output_paths, args.out)


if __name__ == "__main__":
    main()
