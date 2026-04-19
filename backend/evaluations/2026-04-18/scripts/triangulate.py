"""Triangula outputs de Claude, Gemini y Gemma sobre los mismos 60 IDs.

Input:
  data/sample_60_claude.jsonl
  data/sample_60_gemini.jsonl
  data/sample_60_gemma.jsonl

Output:
  output/triangulation_matrix.csv  — tabla cruzada completa
  output/agreement_summary.md      — conteos + kappas
"""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent.parent
DATA = EVAL_DIR / "data"
OUT = EVAL_DIR / "output"
OUT.mkdir(exist_ok=True)

SOURCES = ["claude", "gemini", "gemma"]


def load(path: Path) -> dict[str, dict]:
    out = {}
    if not path.exists():
        return out
    for l in path.read_text().strip().split("\n"):
        if not l:
            continue
        row = json.loads(l)
        out[row["id"]] = row
    return out


def intensity_bucket(v) -> str:
    """Colapsa intensidad a 3 buckets para métricas discretas."""
    if v is None:
        return "unknown"
    try:
        n = int(v)
    except (TypeError, ValueError):
        return "unknown"
    if n < 0:
        return "negativa"
    if n == 0:
        return "neutral"
    return "positiva"


def pairwise_kappa(items_a: list, items_b: list) -> float:
    """Cohen's kappa categórico, asume listas alineadas."""
    if not items_a or len(items_a) != len(items_b):
        return float("nan")
    categories = sorted({*items_a, *items_b})
    n = len(items_a)
    po = sum(a == b for a, b in zip(items_a, items_b)) / n
    counts_a = Counter(items_a)
    counts_b = Counter(items_b)
    pe = sum((counts_a[c] / n) * (counts_b[c] / n) for c in categories)
    if pe == 1:
        return 1.0
    return (po - pe) / (1 - pe)


def fleiss_kappa_3way(rows: list[tuple]) -> float:
    """Fleiss kappa para 3 raters categóricos.

    rows: list of (cat_claude, cat_gemini, cat_gemma) tuples.
    """
    if not rows:
        return float("nan")
    N = len(rows)
    n_raters = 3
    categories = sorted({c for r in rows for c in r})
    if len(categories) < 2:
        return 1.0
    # P_i per row
    P_i = []
    nij_totals = {c: 0 for c in categories}
    for r in rows:
        counts = Counter(r)
        s = sum(v * (v - 1) for v in counts.values())
        P_i.append(s / (n_raters * (n_raters - 1)))
        for c in categories:
            nij_totals[c] += counts.get(c, 0)
    P_bar = sum(P_i) / N
    p_j = {c: nij_totals[c] / (N * n_raters) for c in categories}
    P_e = sum(v * v for v in p_j.values())
    if P_e == 1:
        return 1.0
    return (P_bar - P_e) / (1 - P_e)


def agreement_level(cats: list[str]) -> str:
    uniq = set(cats)
    if len(uniq) == 1:
        return "3/3"
    if len(uniq) == 2:
        return "2/3"
    return "divergence"


def main() -> None:
    claude = load(DATA / "sample_60_claude.jsonl")
    gemini = load(DATA / "sample_60_gemini.jsonl")
    gemma = load(DATA / "sample_60_gemma.jsonl")

    all_ids = set(claude) | set(gemini) | set(gemma)
    common_ids = sorted(set(claude) & set(gemini) & set(gemma))

    print(f"Claude rows: {len(claude)}")
    print(f"Gemini rows: {len(gemini)}")
    print(f"Gemma rows:  {len(gemma)}")
    print(f"Common IDs:  {len(common_ids)}")

    # Matriz detallada
    matrix_rows = []
    for id_ in sorted(all_ids):
        c = claude.get(id_, {})
        g = gemini.get(id_, {})
        m = gemma.get(id_, {})
        row = {
            "id": id_,
            "tono_claude": c.get("tono"),
            "tono_gemini": g.get("tono"),
            "tono_gemma": m.get("tono"),
            "target_claude": c.get("target"),
            "target_gemini": g.get("target"),
            "target_gemma": m.get("target"),
            "intens_claude": c.get("intensidad"),
            "intens_gemini": g.get("intensidad"),
            "intens_gemma": m.get("intensidad"),
            "pol_claude": c.get("polaridad_preliminar"),
            "pol_gemini": g.get("polaridad_preliminar"),
            "pol_gemma": m.get("polaridad_preliminar"),
            "err_claude": c.get("_err") or "",
            "err_gemini": g.get("_err") or "",
            "err_gemma": m.get("_err") or "",
        }
        if id_ in common_ids:
            row["tono_agreement"] = agreement_level([c.get("tono"), g.get("tono"), m.get("tono")])
            row["target_agreement"] = agreement_level([c.get("target"), g.get("target"), m.get("target")])
            row["pol_agreement"] = agreement_level([c.get("polaridad_preliminar"), g.get("polaridad_preliminar"), m.get("polaridad_preliminar")])
            intensity_cats = [intensity_bucket(x.get("intensidad")) for x in (c, g, m)]
            row["intens_bucket_agreement"] = agreement_level(intensity_cats)
        matrix_rows.append(row)

    csv_path = OUT / "triangulation_matrix.csv"
    # Unión de todas las keys para manejar rows con/sin agreement columns
    all_keys: list[str] = []
    seen: set[str] = set()
    for row in matrix_rows:
        for k in row.keys():
            if k not in seen:
                seen.add(k)
                all_keys.append(k)
    with csv_path.open("w") as f:
        if matrix_rows:
            writer = csv.DictWriter(f, fieldnames=all_keys, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(matrix_rows)

    # Summary con kappa
    def collect(dim: str) -> tuple[list, list, list]:
        a, b, c = [], [], []
        for id_ in common_ids:
            va = claude[id_].get(dim)
            vb = gemini[id_].get(dim)
            vc = gemma[id_].get(dim)
            if dim == "intensidad":
                va = intensity_bucket(va)
                vb = intensity_bucket(vb)
                vc = intensity_bucket(vc)
            a.append(va)
            b.append(vb)
            c.append(vc)
        return a, b, c

    dims = ["tono", "target", "polaridad_preliminar", "intensidad"]
    lines = ["# Acuerdo triangulación NLP Layer 2 — 2026-04-18", ""]
    lines.append(f"- Claude rows: {len(claude)}")
    lines.append(f"- Gemini rows: {len(gemini)}")
    lines.append(f"- Gemma rows:  {len(gemma)}")
    lines.append(f"- Common IDs (usados en kappa): {len(common_ids)}")
    lines.append("")
    lines.append("## Acuerdo por dimensión (sobre common IDs)")
    lines.append("")
    lines.append("| Dimensión | 3/3 | 2/3 | divergence | Cohen C-G | Cohen C-M | Cohen G-M | Fleiss 3-way |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for dim in dims:
        a, b, c = collect(dim)
        counts = Counter(agreement_level([x, y, z]) for x, y, z in zip(a, b, c))
        k_cg = pairwise_kappa(a, b)
        k_cm = pairwise_kappa(a, c)
        k_gm = pairwise_kappa(b, c)
        triples = list(zip(a, b, c))
        k_fl = fleiss_kappa_3way(triples)
        label = dim if dim != "intensidad" else "intensidad (bucket)"
        lines.append(
            f"| {label} | {counts.get('3/3',0)} | {counts.get('2/3',0)} | {counts.get('divergence',0)} | "
            f"{k_cg:.3f} | {k_cm:.3f} | {k_gm:.3f} | {k_fl:.3f} |"
        )
    lines.append("")
    lines.append("## Interpretación kappa (Landis & Koch)")
    lines.append("")
    lines.append("- `<0.00` sin acuerdo · `0.00–0.20` ligero · `0.21–0.40` aceptable · `0.41–0.60` moderado · `0.61–0.80` sustancial · `0.81–1.00` casi perfecto")
    lines.append("")
    lines.append("## Errores por modelo (rows con _err)")
    lines.append("")
    for name, store in [("claude", claude), ("gemini", gemini), ("gemma", gemma)]:
        errs = [r for r in store.values() if r.get("_err")]
        lines.append(f"- **{name}**: {len(errs)} errores")

    md_path = OUT / "agreement_summary.md"
    md_path.write_text("\n".join(lines))

    print(f"\n{csv_path}")
    print(md_path)


if __name__ == "__main__":
    main()
