"""Selecciona una muestra stratified determinista de comments para triangulación.

Stratificación: plataforma × handle × bucket de longitud.
Seed fijo (42) → misma selección siempre.

Output: sample_60.jsonl (o N configurable) con rows alineados a schema.SampleRow.

Reglas:
  - Incluye TODAS las plataformas con comments disponibles
  - Balance por handle dentro de cada plataforma (al menos 1 por handle si existe)
  - Balance por longitud: corto (<50 chars), medio (50-150), largo (>150)
  - Excluye comments con text vacío o <5 chars (no aportan a triangulación)
  - Idempotente — re-correr con los mismos inputs devuelve los mismos IDs
"""
from __future__ import annotations

import json
import random
import sys
from collections import defaultdict
from pathlib import Path

# Reusa el loader del runner Gemma para garantizar equivalencia de fuentes
GEMMA_RESULTS_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "benchmarks/scraping/results/2026-04-19"
)

EVAL_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUT_PATH = EVAL_DATA_DIR / "sample_60.jsonl"
SEED = 42


def load_all_comments() -> list[dict]:
    """Mismo loader que nlp_layer2_gemma_bg.py — garantiza overlap."""
    out = []
    for p in GEMMA_RESULTS_DIR.glob("apify_replies_*.json"):
        if p.stem.endswith("_all"):
            continue
        handle = p.stem.replace("apify_replies_", "")
        data = json.loads(p.read_text())
        if not isinstance(data, list):
            continue
        for r in data:
            if not isinstance(r, dict):
                continue
            out.append({
                "id": f"X_{r.get('id','')}",
                "plataforma": "X",
                "handle_dirigente": handle,
                "comment_text": (r.get("text") or "")[:300],
                "post_text": (r.get("inReplyToId") or ""),
                "author": r.get("author.userName") or "",
                "likes": r.get("likeCount") or 0,
            })
    for p in GEMMA_RESULTS_DIR.glob("apify_ig_*.json"):
        handle = p.stem.replace("apify_ig_", "")
        for post in json.loads(p.read_text()):
            if post.get("ownerUsername") != handle:
                continue
            post_caption = (post.get("caption") or "")[:300]
            for c in (post.get("latestComments") or []):
                out.append({
                    "id": f"IG_{post.get('id','')}_{c.get('id','')}",
                    "plataforma": "Instagram",
                    "handle_dirigente": handle,
                    "comment_text": (c.get("text") or "")[:300],
                    "post_text": post_caption,
                    "author": c.get("ownerUsername") or "",
                    "likes": c.get("likesCount") or 0,
                })
    return out


def length_bucket(text: str) -> str:
    n = len(text or "")
    if n < 50:
        return "corto"
    if n <= 150:
        return "medio"
    return "largo"


def stratified_pick(comments: list[dict], n: int) -> list[dict]:
    """Stratification: plataforma × handle × bucket, round-robin con seed fijo."""
    # Filtrar vacíos / demasiado cortos
    usable = [c for c in comments if len((c.get("comment_text") or "").strip()) >= 5]

    # Agrupar por estrato
    strata: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for c in usable:
        key = (c["plataforma"], c["handle_dirigente"], length_bucket(c["comment_text"]))
        strata[key].append(c)

    # Shuffle determinista dentro de cada estrato
    rng = random.Random(SEED)
    for key in strata:
        strata[key].sort(key=lambda c: c["id"])  # orden estable
        rng.shuffle(strata[key])

    # Round-robin sobre estratos ordenados por clave
    ordered_keys = sorted(strata.keys())
    pointers = {k: 0 for k in ordered_keys}
    picked: list[dict] = []
    seen_ids: set[str] = set()

    while len(picked) < n:
        progress = False
        for k in ordered_keys:
            if len(picked) >= n:
                break
            i = pointers[k]
            if i < len(strata[k]):
                candidate = strata[k][i]
                pointers[k] += 1
                progress = True
                if candidate["id"] in seen_ids:
                    continue
                seen_ids.add(candidate["id"])
                picked.append(candidate)
        if not progress:
            break  # agotados todos los estratos

    return picked


def main() -> None:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    comments = load_all_comments()
    print(f"Total cargados: {len(comments)}")

    sample = stratified_pick(comments, n)
    print(f"Muestra seleccionada: {len(sample)}")

    EVAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w") as f:
        for row in sample:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")

    # Summary de cobertura
    by_platform: dict[str, int] = defaultdict(int)
    by_handle: dict[str, int] = defaultdict(int)
    by_bucket: dict[str, int] = defaultdict(int)
    for c in sample:
        by_platform[c["plataforma"]] += 1
        by_handle[c["handle_dirigente"]] += 1
        by_bucket[length_bucket(c["comment_text"])] += 1

    print(f"\nPor plataforma: {dict(by_platform)}")
    print(f"Por handle: {dict(sorted(by_handle.items()))}")
    print(f"Por bucket longitud: {dict(by_bucket)}")
    print(f"\nOutput: {OUT_PATH}")


if __name__ == "__main__":
    main()
