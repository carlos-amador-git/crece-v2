"""Backfill engagement_rate para posts ingeridos sin calcularlo.

CONTEXTO (revisión CEO 2026-05-26 · card B03 matriz 2×2):
La columna `social_posts.engagement_rate` tiene `default=0.0`. Posts ingeridos por
rutas que no calculan ER (RADAR ingest, Apify catchup, scripts) quedan en 0.0 aunque
tengan likes/comments reales. Esto arrastra la mediana de ER a 0 y rompe B03
(Neutros/Sin eco estructuralmente imposibles) y degrada B07/B15.

Afecta a TODOS los clientes (~2,139 posts globales con interacción real y ER=0).

FÓRMULA (consistente con bot_detection.py:314 y los valores ya existentes):
    - con views  (TikTok/YT/Reels): (likes + comments) / views * 100
    - sin views  (X/FB):            (likes + comments + shares) / followers * 100

NO inventa datos: deriva de likes/comments/shares/views/followers ya en BD.
Solo toca filas con ER=0/NULL Y con interacción real (>0). NO toca valores ya
calculados (≠0) ni ceros reales (sin interacción). Idempotente.

Uso:
    docker exec crece-backend python scripts/backfill_engagement_rate.py --dry-run
    docker exec crece-backend python scripts/backfill_engagement_rate.py --apply
"""
from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import text

from app.core.database import async_session_factory
from app.services.engagement import compute_engagement_rate

# Selecciona candidatos + calcula ER nuevo en una sola pasada.
SELECT_SQL = text(
    """
    SELECT p.id,
           pr.platform,
           COALESCE(p.likes, 0)   AS likes,
           COALESCE(p.comments, 0) AS comments,
           COALESCE(p.shares, 0)  AS shares,
           COALESCE(p.views, 0)   AS views,
           COALESCE(pr.followers_count, 0) AS followers
    FROM social_posts p
    JOIN social_profiles pr ON pr.id = p.profile_id
    WHERE (p.engagement_rate = 0 OR p.engagement_rate IS NULL)
      AND (COALESCE(p.likes,0) + COALESCE(p.comments,0) + COALESCE(p.shares,0)) > 0
    """
)

UPDATE_SQL = text("UPDATE social_posts SET engagement_rate = :er WHERE id = :pid")


def _compute_er(likes: int, comments: int, shares: int, views: int, followers: int) -> float | None:
    """Wrap del helper canónico. Devuelve None cuando no hay denominador
    (views==0 y followers==0) para no tocar esas filas."""
    if not (views and views > 0) and not (followers and followers > 0):
        return None
    return compute_engagement_rate(likes, comments, shares, views, followers)


async def main(apply: bool) -> None:
    async with async_session_factory() as db:
        rows = (await db.execute(SELECT_SQL)).mappings().all()
        print(f"Candidatos (ER=0/NULL con interacción real): {len(rows)}")

        cambios = []
        sin_denominador = 0
        for r in rows:
            er = _compute_er(r["likes"], r["comments"], r["shares"], r["views"], r["followers"])
            if er is None:
                sin_denominador += 1
                continue
            cambios.append((r["id"], er, r["platform"]))

        print(f"Calculables: {len(cambios)} · sin denominador (views=0 y followers=0): {sin_denominador}")
        print("Muestra (post_id · plataforma · ER nuevo):")
        for pid, er, plat in cambios[:10]:
            print(f"  #{pid} · {plat} · {er}%")

        if not apply:
            print("\n[DRY-RUN] No se escribió nada. Corre con --apply para aplicar.")
            return

        for pid, er, _plat in cambios:
            await db.execute(UPDATE_SQL, {"er": er, "pid": pid})
        await db.commit()
        print(f"\n[APPLY] {len(cambios)} filas actualizadas.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Aplica los cambios (sin esto = dry-run)")
    parser.add_argument("--dry-run", action="store_true", help="Solo reporta (default)")
    args = parser.parse_args()
    asyncio.run(main(apply=args.apply))
