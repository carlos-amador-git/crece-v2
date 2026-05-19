#!/usr/bin/env python3
"""
Compare 3-way triangulación NLP sobre 60 posts.
Evaluadores: Claude · Gemma3:12b · Gemini CLI

Vocabulario V2:
- Tono:   critico | propositivo | celebratorio | informativo | solidario | ataque | personal
- Target: gobierno | oposicion | ciudadania | medios | autopromocion | tema_especifico | dirigente

Uso:
    python3 backend/scripts/compare_triangulacion_posts_3way.py
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = ROOT / "evaluations" / "triangulacion-posts-2026-05-09"

CSV_CLAUDE = EVAL_DIR / "results_claude.csv"
CSV_GEMMA = EVAL_DIR / "results_gemma.csv"
CSV_GEMINI = EVAL_DIR / "results_gemini.csv"

OUT_MD = EVAL_DIR / "triangulacion-3way-2026-05-09.md"
OUT_CSV = EVAL_DIR / "triangulacion-3way-2026-05-09.csv"
OUT_JSON = EVAL_DIR / "triangulacion-3way-2026-05-09.json"

EVALUATORS = ("claude", "gemma", "gemini")
DIMENSIONS = ("tono", "target", "sentimiento")

VOCAB_TONO = {
    "critico", "propositivo", "celebratorio", "informativo",
    "solidario", "ataque", "personal",
}
VOCAB_TARGET = {
    "gobierno", "oposicion", "ciudadania", "medios",
    "autopromocion", "tema_especifico", "dirigente",
}


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------
def load_csv(path: Path, evaluator: str) -> dict[str, dict]:
    """Load evaluator CSV indexed by post_id."""
    if not path.exists():
        return {}
    out: dict[str, dict] = {}
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            pid = (row.get("post_id") or "").strip()
            if not pid:
                continue
            out[pid] = {
                "post_id": pid,
                "dirigente_id": (row.get("dirigente_id") or "").strip(),
                "dirigente_nombre": (row.get("dirigente_nombre") or "").strip(),
                "tono": (row.get(f"tono_{evaluator}") or "").strip().lower(),
                "target": (row.get(f"target_{evaluator}") or "").strip().lower(),
                "sentimiento": (row.get(f"sentimiento_{evaluator}") or "").strip().lower(),
                "razon": (row.get(f"razon_{evaluator}") or "").strip(),
            }
    return out


def precheck_inputs() -> dict[str, dict] | None:
    """Verify all 3 CSVs exist; if not, exit cleanly."""
    missing = []
    if not CSV_CLAUDE.exists():
        missing.append("Claude")
    if not CSV_GEMMA.exists():
        missing.append("Gemma3:12b")
    if not CSV_GEMINI.exists():
        missing.append("Gemini")
    if missing:
        for ev in missing:
            print(f"Esperando evaluador {ev}: archivo no encontrado.")
        return None

    data = {
        "claude": load_csv(CSV_CLAUDE, "claude"),
        "gemma": load_csv(CSV_GEMMA, "gemma"),
        "gemini": load_csv(CSV_GEMINI, "gemini"),
    }
    counts = {ev: len(rows) for ev, rows in data.items()}
    print(f"Filas por evaluador: {counts}")
    if any(c < 60 for c in counts.values()):
        print("WARNING: algún evaluador tiene <60 rows. Procediendo con intersección.")
    return data


# ---------------------------------------------------------------------------
# Cohen kappa (manual: scipy/sklearn no requeridos)
# ---------------------------------------------------------------------------
def cohen_kappa(labels_a: list[str], labels_b: list[str]) -> float:
    """Cohen's kappa para dos anotadores con etiquetas categóricas."""
    if len(labels_a) != len(labels_b) or not labels_a:
        return float("nan")
    n = len(labels_a)
    categories = sorted(set(labels_a) | set(labels_b))
    if not categories:
        return float("nan")

    agree = sum(1 for a, b in zip(labels_a, labels_b) if a == b)
    po = agree / n

    count_a = Counter(labels_a)
    count_b = Counter(labels_b)
    pe = sum((count_a[c] / n) * (count_b[c] / n) for c in categories)

    if pe == 1.0:
        return 1.0 if po == 1.0 else 0.0
    return (po - pe) / (1 - pe)


def fleiss_kappa(matrix: list[list[int]]) -> float:
    """
    Fleiss kappa para N items × k categorías.
    matrix[i][j] = número de evaluadores que asignaron categoría j al item i.
    """
    if not matrix:
        return float("nan")
    n = len(matrix)
    n_raters = sum(matrix[0])
    if n_raters < 2:
        return float("nan")

    p_j = []
    k = len(matrix[0])
    for j in range(k):
        p_j.append(sum(matrix[i][j] for i in range(n)) / (n * n_raters))

    P_i = []
    for i in range(n):
        s = sum(matrix[i][j] * (matrix[i][j] - 1) for j in range(k))
        P_i.append(s / (n_raters * (n_raters - 1)))

    P_bar = sum(P_i) / n
    Pe_bar = sum(p ** 2 for p in p_j)
    if Pe_bar == 1.0:
        return 1.0 if P_bar == 1.0 else 0.0
    return (P_bar - Pe_bar) / (1 - Pe_bar)


# ---------------------------------------------------------------------------
# Merge wide table
# ---------------------------------------------------------------------------
def build_wide(data: dict[str, dict]) -> list[dict]:
    """Build wide-format rows from intersection of post_ids."""
    common = set(data["claude"].keys()) & set(data["gemma"].keys()) & set(data["gemini"].keys())
    rows: list[dict] = []
    for pid in sorted(common):
        c = data["claude"][pid]
        g = data["gemma"][pid]
        m = data["gemini"][pid]
        row = {
            "post_id": pid,
            "dirigente_id": c["dirigente_id"] or g["dirigente_id"] or m["dirigente_id"],
            "dirigente_nombre": c["dirigente_nombre"] or g["dirigente_nombre"] or m["dirigente_nombre"],
        }
        for dim in DIMENSIONS:
            row[f"{dim}_claude"] = c[dim]
            row[f"{dim}_gemma"] = g[dim]
            row[f"{dim}_gemini"] = m[dim]
            row[f"acuerdo_{dim}"] = classify_agreement(c[dim], g[dim], m[dim])
        rows.append(row)
    return rows


def classify_agreement(c: str, g: str, m: str) -> str:
    if c == g == m and c != "":
        return "3/3"
    if c == g and c != "":
        return "2/3 (Claude+Gemma)"
    if c == m and c != "":
        return "2/3 (Claude+Gemini)"
    if g == m and g != "":
        return "2/3 (Gemma+Gemini)"
    return "0/3"


# ---------------------------------------------------------------------------
# Métricas
# ---------------------------------------------------------------------------
def agreement_pct(rows: list[dict], dim: str) -> dict:
    counter: Counter = Counter()
    for r in rows:
        counter[r[f"acuerdo_{dim}"]] += 1
    total = len(rows) or 1
    return {k: {"n": v, "pct": round(v / total * 100, 1)} for k, v in counter.most_common()}


def distribution(rows: list[dict], dim: str) -> dict[str, list[tuple[str, int]]]:
    out: dict[str, list[tuple[str, int]]] = {}
    for ev in EVALUATORS:
        c: Counter = Counter(r[f"{dim}_{ev}"] for r in rows if r[f"{dim}_{ev}"])
        out[ev] = c.most_common(3)
    return out


def pairwise_kappas(rows: list[dict]) -> dict[str, dict[str, float]]:
    pairs = list(combinations(EVALUATORS, 2))
    out: dict[str, dict[str, float]] = {}
    for a, b in pairs:
        key = f"{a}_vs_{b}"
        out[key] = {}
        for dim in DIMENSIONS:
            la = [r[f"{dim}_{a}"] for r in rows]
            lb = [r[f"{dim}_{b}"] for r in rows]
            out[key][dim] = round(cohen_kappa(la, lb), 4)
    return out


def fleiss_per_dim(rows: list[dict], dim: str, vocab: Iterable[str]) -> float:
    vocab_list = sorted(vocab)
    matrix = []
    for r in rows:
        labels = [r[f"{dim}_{ev}"] for ev in EVALUATORS]
        cnts = [labels.count(v) for v in vocab_list]
        if sum(cnts) != len(EVALUATORS):
            # incluir "otros" si hay etiquetas fuera del vocab
            cnts.append(len(EVALUATORS) - sum(cnts))
        matrix.append(cnts)
    # normalizar columnas
    max_len = max(len(r) for r in matrix)
    matrix = [r + [0] * (max_len - len(r)) for r in matrix]
    return round(fleiss_kappa(matrix), 4)


def divergences(rows: list[dict], odd_evaluator: str, dim: str = "tono", limit: int = 10) -> list[dict]:
    """Posts donde odd_evaluator difiere y los otros dos coinciden."""
    others = [ev for ev in EVALUATORS if ev != odd_evaluator]
    out = []
    for r in rows:
        odd = r[f"{dim}_{odd_evaluator}"]
        a = r[f"{dim}_{others[0]}"]
        b = r[f"{dim}_{others[1]}"]
        if a == b and a != odd and a:
            out.append({
                "post_id": r["post_id"],
                "dirigente": r["dirigente_nombre"],
                "consenso": a,
                "outlier": odd,
                "consenso_evaluators": others,
            })
        if len(out) >= limit:
            break
    return out


def per_dirigente_breakdown(rows: list[dict]) -> dict[str, dict]:
    by_dir: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_dir[r["dirigente_nombre"] or "?"].append(r)
    out = {}
    for name, items in by_dir.items():
        out[name] = {
            "n_posts": len(items),
            "acuerdo_3_3_tono_pct": round(
                sum(1 for r in items if r["acuerdo_tono"] == "3/3") / len(items) * 100, 1
            ),
            "acuerdo_3_3_target_pct": round(
                sum(1 for r in items if r["acuerdo_target"] == "3/3") / len(items) * 100, 1
            ),
        }
    return out


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------
def write_csv(rows: list[dict], path: Path) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    cols = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=cols)
        writer.writeheader()
        writer.writerows(rows)


def write_json(payload: dict, path: Path) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_md(payload: dict, path: Path) -> None:
    rows = payload["rows"]
    n = len(rows)
    lines: list[str] = []
    lines.append("# Triangulación NLP posts · 3-way Claude+Gemma+Gemini · 2026-05-09\n")
    lines.append("## Resumen ejecutivo")
    lines.append(f"- {n} posts evaluados por 3 inteligencias (intersección de post_id)")
    ag_t = payload["agreement"]["tono"].get("3/3", {"pct": 0})["pct"]
    ag_g = payload["agreement"]["target"].get("3/3", {"pct": 0})["pct"]
    ag_s = payload["agreement"]["sentimiento"].get("3/3", {"pct": 0})["pct"]
    lines.append(f"- Acuerdo 3/3 tono: **{ag_t}%**")
    lines.append(f"- Acuerdo 3/3 target: **{ag_g}%**")
    lines.append(f"- Acuerdo 3/3 sentimiento: **{ag_s}%**")
    lines.append(f"- Fleiss kappa tono: **{payload['fleiss']['tono']}**")
    lines.append(f"- Fleiss kappa target: **{payload['fleiss']['target']}**")
    lines.append("")

    lines.append("## Distribución por evaluador (top-3)\n")
    for dim in DIMENSIONS:
        lines.append(f"### {dim}")
        lines.append("| Evaluador | top-1 | top-2 | top-3 |")
        lines.append("|---|---|---|---|")
        for ev in EVALUATORS:
            top = payload["distribution"][dim][ev]
            cells = [f"{lbl} ({n})" for lbl, n in top]
            while len(cells) < 3:
                cells.append("—")
            lines.append(f"| {ev} | {cells[0]} | {cells[1]} | {cells[2]} |")
        lines.append("")

    lines.append("## Acuerdo pairwise (Cohen kappa)\n")
    lines.append("| Par | tono | target | sentimiento |")
    lines.append("|---|---|---|---|")
    for pair, dims in payload["pairwise_kappa"].items():
        lines.append(f"| {pair} | {dims['tono']} | {dims['target']} | {dims['sentimiento']} |")
    lines.append("")

    lines.append("## Acuerdo total por dimensión\n")
    for dim in DIMENSIONS:
        lines.append(f"### {dim}")
        lines.append("| Patrón | n | % |")
        lines.append("|---|---|---|")
        for k, v in payload["agreement"][dim].items():
            lines.append(f"| {k} | {v['n']} | {v['pct']}% |")
        lines.append("")

    lines.append("## Divergencias notables\n")
    for ev in EVALUATORS:
        lines.append(f"### Top 10 donde **{ev}** se desvía (otros 2 coinciden)")
        lines.append("| post_id | dirigente | consenso | outlier (este) |")
        lines.append("|---|---|---|---|")
        for d in payload["divergences"][ev]:
            lines.append(
                f"| {d['post_id']} | {d['dirigente']} | {d['consenso']} | {d['outlier']} |"
            )
        if not payload["divergences"][ev]:
            lines.append("| _sin divergencias relevantes_ | | | |")
        lines.append("")

    lines.append("## Acuerdo por dirigente\n")
    lines.append("| Dirigente | n_posts | acuerdo 3/3 tono | acuerdo 3/3 target |")
    lines.append("|---|---|---|---|")
    for name, stats in payload["per_dirigente"].items():
        lines.append(
            f"| {name} | {stats['n_posts']} | {stats['acuerdo_3_3_tono_pct']}% | {stats['acuerdo_3_3_target_pct']}% |"
        )
    lines.append("")

    lines.append("## Conclusión\n")
    lines.append("- Análisis cualitativo pendiente — revisar tablas anteriores para")
    lines.append("  identificar si Gemma3:12b está listo para producción sobre posts")
    lines.append("  o requiere ajuste de prompt sobre dimensiones con kappa < 0.4.")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    data = precheck_inputs()
    if data is None:
        return 0  # exit limpio cuando falta evaluador

    rows = build_wide(data)
    if not rows:
        print("ERROR: sin intersección de post_ids entre los 3 CSVs.")
        return 1

    payload = {
        "n_posts": len(rows),
        "agreement": {dim: agreement_pct(rows, dim) for dim in DIMENSIONS},
        "distribution": {dim: distribution(rows, dim) for dim in DIMENSIONS},
        "pairwise_kappa": pairwise_kappas(rows),
        "fleiss": {
            "tono": fleiss_per_dim(rows, "tono", VOCAB_TONO),
            "target": fleiss_per_dim(rows, "target", VOCAB_TARGET),
        },
        "divergences": {ev: divergences(rows, ev, "tono", 10) for ev in EVALUATORS},
        "per_dirigente": per_dirigente_breakdown(rows),
        "rows": rows,
    }

    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(rows, OUT_CSV)
    write_json(payload, OUT_JSON)
    write_md(payload, OUT_MD)

    print(f"OK · n={len(rows)} posts triangulados")
    print(f"  MD:   {OUT_MD}")
    print(f"  CSV:  {OUT_CSV}")
    print(f"  JSON: {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
