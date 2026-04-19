"""Extrae los 60 IDs del output Gemma general y los normaliza al schema unificado.

Input: benchmarks/scraping/results/2026-04-19/nlp_layer2_gemma_out.jsonl (live, en crecimiento)
Output: evaluations/2026-04-18/data/sample_60_gemma.jsonl

Si Gemma no tiene aún los 60 IDs, imprime cuántos faltan y escribe sólo los encontrados
con una advertencia clara — re-ejecutable cuando Gemma termine.
"""
from __future__ import annotations

import json
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent.parent
SAMPLE_PATH = EVAL_DIR / "data" / "sample_60.jsonl"
OUT_PATH = EVAL_DIR / "data" / "sample_60_gemma.jsonl"
GEMMA_JSONL = (
    EVAL_DIR.parent.parent
    / "benchmarks/scraping/results/2026-04-19/nlp_layer2_gemma_out.jsonl"
)


def load_target_ids() -> list[str]:
    return [json.loads(l)["id"] for l in SAMPLE_PATH.read_text().strip().split("\n")]


def index_gemma_by_id() -> dict[str, dict]:
    """Index por id. Si hay duplicados, toma la clasificación más reciente por
    classified_at, con preferencia por la que tenga campos completos (no todos None)."""
    buckets: dict[str, list[dict]] = {}
    for l in GEMMA_JSONL.read_text().strip().split("\n"):
        try:
            row = json.loads(l)
        except json.JSONDecodeError:
            continue
        buckets.setdefault(row["id"], []).append(row)

    out: dict[str, dict] = {}
    for id_, rows in buckets.items():
        # Prefer non-null classification, then most recent
        valid = [r for r in rows if isinstance(r.get("classification"), dict)
                 and r["classification"].get("tono") is not None]
        if valid:
            out[id_] = max(valid, key=lambda r: r.get("classified_at", ""))
        else:
            out[id_] = rows[-1]
    return out


def normalize(gemma_row: dict) -> dict:
    cls = gemma_row.get("classification", {}) or {}
    return {
        "id": gemma_row["id"],
        "source_model": "gemma3:12b",
        "tono": cls.get("tono"),
        "target": cls.get("target"),
        "intensidad": cls.get("intensidad"),
        "polaridad_preliminar": cls.get("polaridad_preliminar"),
        "razon_corta": (cls.get("razon_corta") or "")[:500],
        "classified_at": gemma_row.get("classified_at"),
        "_err": cls.get("_err"),
    }


def main() -> None:
    target_ids = load_target_ids()
    idx = index_gemma_by_id()
    found = [idx[i] for i in target_ids if i in idx]
    missing = [i for i in target_ids if i not in idx]

    with OUT_PATH.open("w") as f:
        for row in found:
            f.write(json.dumps(normalize(row), ensure_ascii=False) + "\n")

    print(f"Gemma total rows:  {len(idx)}")
    print(f"Sample target IDs: {len(target_ids)}")
    print(f"Matched:           {len(found)}")
    print(f"Missing:           {len(missing)}")
    if missing:
        print("  Primeros 5 missing:")
        for i in missing[:5]:
            print(f"    {i}")
    print(f"Output: {OUT_PATH}")


if __name__ == "__main__":
    main()
