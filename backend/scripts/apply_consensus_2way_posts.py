"""Aplica consenso 2-way (Claude + Gemini) sobre 60 posts a `social_posts`.

CONTEXTO 2026-05-09:
- Gemma timeout 70%+ en VPS Coolify, no se completó la triangulación 3-way.
- Claude (60/60) y Gemini (60/60) ya clasificaron sample.csv con vocab v2.
- Reunión HITL 2026-05-10 necesita posts con sugerencia previa para que dirigentes
  confirmen/editen.

REGLA CONSENSO:
- tono_claude == tono_gemini → consensus, agreement="2/2"
- tono_claude != tono_gemini → usa Claude (mejor matiz político MX), agreement="1/2"
- mismo para target.
- llm_razon = razon_claude (más estructurada en pruebas previas).
- nlp_model_version = "claude+gemini-2way-2026-05-09".
- clasificacion_origen = "ai_suggested" (constraint).

Salida:
- UPDATE social_posts SET tono_discurso, target_politico, nlp_model_version,
  llm_razon, clasificacion_origen WHERE id = post_id.
- Reporte CSV con consensus stats: post_id, tono_consenso, tono_agreement,
  target_consenso, target_agreement.

Usage:
  docker exec -e DATABASE_URL='postgresql+asyncpg://crece:crece_dev@db:5432/crece' \\
    crece-backend python /app/scripts/apply_consensus_2way_posts.py [--dry-run]
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import os
import sys
from collections import Counter
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

VALID_TONO = {"critico", "propositivo", "celebratorio", "informativo", "solidario", "ataque", "personal"}
VALID_TARGET = {"gobierno", "oposicion", "ciudadania", "medios", "autopromocion", "tema_especifico", "dirigente"}

EVAL_DIR = Path("/app/evaluations/triangulacion-posts-2026-05-09")
CLAUDE_CSV = EVAL_DIR / "results_claude.csv"
GEMINI_CSV = EVAL_DIR / "results_gemini.csv"
CONSENSUS_CSV = EVAL_DIR / "consensus_2way_2026-05-09.csv"

NLP_VERSION = "claude+gemini-2way-2026-05-09"


def load_csv(path: Path, prefix: str) -> dict[int, dict]:
    """Carga CSV indexado por post_id. prefix='claude' o 'gemini'."""
    out: dict[int, dict] = {}
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            pid_raw = (row.get("post_id") or "").strip()
            if not pid_raw or not pid_raw.isdigit():
                continue
            pid = int(pid_raw)
            out[pid] = {
                "tono": (row.get(f"tono_{prefix}") or "").strip().lower(),
                "target": (row.get(f"target_{prefix}") or "").strip().lower(),
                "razon": (row.get(f"razon_{prefix}") or "").strip(),
            }
    return out


def consensus(claude: dict, gemini: dict) -> tuple[str, str, str, str, str]:
    """Devuelve (tono, target, tono_agreement, target_agreement, razon)."""
    tono_c = claude["tono"] if claude["tono"] in VALID_TONO else None
    tono_g = gemini["tono"] if gemini["tono"] in VALID_TONO else None
    tgt_c = claude["target"] if claude["target"] in VALID_TARGET else None
    tgt_g = gemini["target"] if gemini["target"] in VALID_TARGET else None

    # tono
    if tono_c and tono_g and tono_c == tono_g:
        tono = tono_c
        tono_agree = "2/2"
    elif tono_c:
        tono = tono_c
        tono_agree = "1/2_claude" if tono_g else "claude_only"
    elif tono_g:
        tono = tono_g
        tono_agree = "1/2_gemini"
    else:
        tono = ""
        tono_agree = "0/2"

    # target
    if tgt_c and tgt_g and tgt_c == tgt_g:
        target = tgt_c
        tgt_agree = "2/2"
    elif tgt_c:
        target = tgt_c
        tgt_agree = "1/2_claude" if tgt_g else "claude_only"
    elif tgt_g:
        target = tgt_g
        tgt_agree = "1/2_gemini"
    else:
        target = ""
        tgt_agree = "0/2"

    razon = (claude["razon"] or gemini["razon"])[:480]
    return tono, target, tono_agree, tgt_agree, razon


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not CLAUDE_CSV.exists() or not GEMINI_CSV.exists():
        print(f"ERROR: faltan {CLAUDE_CSV} o {GEMINI_CSV}", file=sys.stderr)
        return 1

    claude = load_csv(CLAUDE_CSV, "claude")
    gemini = load_csv(GEMINI_CSV, "gemini")
    common = sorted(set(claude.keys()) & set(gemini.keys()))
    print(f"[+] Claude: {len(claude)} · Gemini: {len(gemini)} · Intersección: {len(common)}")

    if not common:
        print("ERROR: sin intersección de post_ids", file=sys.stderr)
        return 1

    eng = create_async_engine(os.environ["DATABASE_URL"], echo=False)
    Session = async_sessionmaker(eng, expire_on_commit=False)

    rows_out: list[dict] = []
    tono_agree_counter: Counter = Counter()
    tgt_agree_counter: Counter = Counter()
    updated = 0
    skipped = 0
    errors = 0

    async with Session() as db:
        for pid in common:
            tono, target, t_a, g_a, razon = consensus(claude[pid], gemini[pid])
            tono_agree_counter[t_a] += 1
            tgt_agree_counter[g_a] += 1

            if not tono or not target:
                skipped += 1
                rows_out.append({
                    "post_id": pid,
                    "tono_consenso": tono,
                    "tono_agreement": t_a,
                    "target_consenso": target,
                    "target_agreement": g_a,
                    "applied": False,
                })
                continue

            if args.dry_run:
                rows_out.append({
                    "post_id": pid,
                    "tono_consenso": tono,
                    "tono_agreement": t_a,
                    "target_consenso": target,
                    "target_agreement": g_a,
                    "applied": "dry-run",
                })
                continue

            try:
                await db.execute(text("""
                    UPDATE social_posts
                       SET tono_discurso = :tono,
                           target_politico = :target,
                           nlp_model_version = :ver,
                           llm_razon = :razon,
                           clasificacion_origen = 'ai_suggested'
                     WHERE id = :pid
                """), {
                    "tono": tono,
                    "target": target,
                    "ver": NLP_VERSION,
                    "razon": razon,
                    "pid": pid,
                })
                await db.commit()
                updated += 1
                rows_out.append({
                    "post_id": pid,
                    "tono_consenso": tono,
                    "tono_agreement": t_a,
                    "target_consenso": target,
                    "target_agreement": g_a,
                    "applied": True,
                })
            except Exception as e:
                await db.rollback()
                errors += 1
                rows_out.append({
                    "post_id": pid,
                    "tono_consenso": tono,
                    "tono_agreement": t_a,
                    "target_consenso": target,
                    "target_agreement": g_a,
                    "applied": False,
                    "error": str(e)[:200],
                })

    # Reporte
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    with CONSENSUS_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=[
            "post_id", "tono_consenso", "tono_agreement",
            "target_consenso", "target_agreement", "applied", "error",
        ])
        writer.writeheader()
        for r in rows_out:
            r.setdefault("error", "")
            writer.writerow(r)

    print()
    print(f"=== Aplicados ===")
    print(f"  Updated: {updated} · Skipped: {skipped} · Errors: {errors}")
    print(f"  Dry-run: {args.dry_run}")
    print()
    print(f"=== Tono agreement ===")
    for k, v in tono_agree_counter.most_common():
        print(f"  {k}: {v}")
    print()
    print(f"=== Target agreement ===")
    for k, v in tgt_agree_counter.most_common():
        print(f"  {k}: {v}")
    print()
    print(f"Reporte: {CONSENSUS_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
