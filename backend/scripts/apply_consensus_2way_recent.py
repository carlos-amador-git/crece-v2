"""Aplica consenso 2-way (Claude + Gemini) sobre los 52 posts más recientes a `social_posts`.

Misma lógica que apply_consensus_2way_posts.py pero leyendo los CSVs `_recent`:
- results_claude_recent.csv
- results_gemini_recent.csv

Solo UPDATEa posts donde tono_discurso IS NULL (preserva los 8 posts ya clasificados
con consensus 2-way del primer batch).

Usage:
  docker exec -e DATABASE_URL='postgresql+asyncpg://crece:crece_dev@db:5432/crece' \\
    crece-backend python /app/scripts/apply_consensus_2way_recent.py [--dry-run]
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
CLAUDE_CSV = EVAL_DIR / "results_claude_recent.csv"
GEMINI_CSV = EVAL_DIR / "results_gemini_recent.csv"
CONSENSUS_CSV = EVAL_DIR / "consensus_2way_recent_2026-05-09.csv"

NLP_VERSION = "claude+gemini-2way-recent-2026-05-09"


def load_csv(path: Path, prefix: str) -> dict[int, dict]:
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
    tono_c = claude["tono"] if claude["tono"] in VALID_TONO else None
    tono_g = gemini["tono"] if gemini["tono"] in VALID_TONO else None
    tgt_c = claude["target"] if claude["target"] in VALID_TARGET else None
    tgt_g = gemini["target"] if gemini["target"] in VALID_TARGET else None

    if tono_c and tono_g and tono_c == tono_g:
        tono, tono_agree = tono_c, "2/2"
    elif tono_c:
        tono, tono_agree = tono_c, ("1/2_claude" if tono_g else "claude_only")
    elif tono_g:
        tono, tono_agree = tono_g, "1/2_gemini"
    else:
        tono, tono_agree = "", "0/2"

    if tgt_c and tgt_g and tgt_c == tgt_g:
        target, tgt_agree = tgt_c, "2/2"
    elif tgt_c:
        target, tgt_agree = tgt_c, ("1/2_claude" if tgt_g else "claude_only")
    elif tgt_g:
        target, tgt_agree = tgt_g, "1/2_gemini"
    else:
        target, tgt_agree = "", "0/2"

    razon = (claude["razon"] or gemini["razon"])[:480]
    return tono, target, tono_agree, tgt_agree, razon


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not CLAUDE_CSV.exists():
        print(f"ERROR: falta {CLAUDE_CSV}", file=sys.stderr)
        return 1
    if not GEMINI_CSV.exists():
        print(f"ERROR: falta {GEMINI_CSV} (Gemini aún no terminó?)", file=sys.stderr)
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
                    "post_id": pid, "tono_consenso": tono, "tono_agreement": t_a,
                    "target_consenso": target, "target_agreement": g_a, "applied": False,
                })
                continue

            if args.dry_run:
                rows_out.append({
                    "post_id": pid, "tono_consenso": tono, "tono_agreement": t_a,
                    "target_consenso": target, "target_agreement": g_a, "applied": "dry-run",
                })
                continue

            try:
                # SOLO actualiza si tono_discurso IS NULL (preservar consensus previo)
                res = await db.execute(text("""
                    UPDATE social_posts
                       SET tono_discurso = :tono,
                           target_politico = :target,
                           nlp_model_version = :ver,
                           llm_razon = :razon,
                           clasificacion_origen = 'ai_suggested'
                     WHERE id = :pid
                       AND tono_discurso IS NULL
                """), {
                    "tono": tono, "target": target, "ver": NLP_VERSION,
                    "razon": razon, "pid": pid,
                })
                await db.commit()
                if res.rowcount:
                    updated += 1
                    applied = True
                else:
                    skipped += 1
                    applied = "skipped_existing"
                rows_out.append({
                    "post_id": pid, "tono_consenso": tono, "tono_agreement": t_a,
                    "target_consenso": target, "target_agreement": g_a, "applied": applied,
                })
            except Exception as e:
                await db.rollback()
                errors += 1
                rows_out.append({
                    "post_id": pid, "tono_consenso": tono, "tono_agreement": t_a,
                    "target_consenso": target, "target_agreement": g_a,
                    "applied": False, "error": str(e)[:200],
                })

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
