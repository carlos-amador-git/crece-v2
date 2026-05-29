"""Genera sample_recent_oficialistas.csv + posts_for_claude_oficialistas.json
sobre los 20 posts más recientes de Jiménez Godoy (id=5) + Cravioto (id=6).

Decisión CEO 2026-05-09 (Opción B): incluir 2 oficialistas CDMX en la reunión 2026-05-10.

Salida:
  /app/evaluations/triangulacion-posts-2026-05-09/sample_recent_oficialistas.csv
  /app/evaluations/triangulacion-posts-2026-05-09/posts_for_claude_oficialistas.json
"""
from __future__ import annotations

import asyncio
import csv
import json
import os
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

DIRIGENTE_IDS = [5, 6]  # Jiménez Godoy, Cravioto
PER_DIRIGENTE = 20
MAX_CHARS = 800

OUT_DIR = Path("/app/evaluations/triangulacion-posts-2026-05-09")
SAMPLE_CSV = OUT_DIR / "sample_recent_oficialistas.csv"
SAMPLE_JSON = OUT_DIR / "posts_for_claude_oficialistas.json"


async def main() -> int:
    eng = create_async_engine(os.environ["DATABASE_URL"], echo=False)
    Session = async_sessionmaker(eng, expire_on_commit=False)

    async with Session() as db:
        rows = (await db.execute(text("""
            WITH ranked AS (
                SELECT
                    sp.id,
                    sp.content,
                    sp.published_at,
                    sprof.platform::text AS plataforma,
                    d.id AS dirigente_id,
                    d.full_name AS dirigente_nombre,
                    sp.tono_discurso,
                    sp.target_politico,
                    sp.nlp_model_version,
                    ROW_NUMBER() OVER (PARTITION BY d.id ORDER BY sp.published_at DESC) AS rn
                FROM social_posts sp
                JOIN social_profiles sprof ON sprof.id = sp.profile_id
                JOIN dirigentes d ON d.id = sprof.dirigente_id
                WHERE d.id = ANY(:ids)
                  AND sp.content IS NOT NULL
                  AND length(sp.content) > 30
                  AND sp.published_at > NOW() - INTERVAL '90 days'
            )
            SELECT id, dirigente_id, dirigente_nombre, plataforma, content,
                   published_at, tono_discurso, target_politico, nlp_model_version
              FROM ranked
             WHERE rn <= :n
             ORDER BY dirigente_id, published_at DESC
        """), {"ids": DIRIGENTE_IDS, "n": PER_DIRIGENTE})).all()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with SAMPLE_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "post_id", "dirigente_id", "dirigente_nombre", "plataforma",
            "content", "published_at", "current_tono", "current_target", "current_version",
        ])
        w.writeheader()
        for r in rows:
            w.writerow({
                "post_id": r.id,
                "dirigente_id": r.dirigente_id,
                "dirigente_nombre": r.dirigente_nombre,
                "plataforma": r.plataforma,
                "content": (r.content or "")[:MAX_CHARS],
                "published_at": r.published_at.isoformat() if r.published_at else "",
                "current_tono": r.tono_discurso or "",
                "current_target": r.target_politico or "",
                "current_version": r.nlp_model_version or "",
            })

    needs_class = [r for r in rows if not r.tono_discurso or not r.target_politico]
    payload = []
    for r in needs_class:
        payload.append({
            "post_id": r.id,
            "dirigente": r.dirigente_nombre,
            "plataforma": r.plataforma,
            "fecha": r.published_at.isoformat()[:10] if r.published_at else "",
            "content": (r.content or "")[:MAX_CHARS],
        })
    SAMPLE_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[+] Sample total: {len(rows)} posts")
    print(f"[+] Necesitan clasificación: {len(needs_class)} posts")
    by_dir: dict = {}
    for r in needs_class:
        by_dir[r.dirigente_nombre] = by_dir.get(r.dirigente_nombre, 0) + 1
    for nombre, n in by_dir.items():
        print(f"    {nombre}: {n}")
    print(f"[+] CSV: {SAMPLE_CSV}")
    print(f"[+] JSON: {SAMPLE_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
