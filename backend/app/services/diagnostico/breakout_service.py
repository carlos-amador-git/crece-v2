"""B02 — Breakout Scale Brookings (Categorías 1-6).

MASTER §3.1 #02.

Detecta posts que cruzan fronteras algorítmicas hacia no-seguidores. Heurística
T1 (sin reach real de APIs):

    ratio_breakout = views / followers

    Cat 1 (~baseline):     ratio ≤ 1.5×
    Cat 2 (amplificado):   1.5× < ratio ≤ 3×
    Cat 3 (breakout):      3× < ratio ≤ 10×
    Cat 4 (viral fuerte):  10× < ratio ≤ 50×
    Cat 5 (viral nacional):50× < ratio ≤ 500×
    Cat 6 (global/mega):   ratio > 500×

T3 exacto vendría de ``unconnected_reach`` (Meta Graph / TikTok Business), no
disponible en S2.

Returns:
    {
        "status": "ok",
        "data": {
            "max_categoria": 3,
            "posts_por_categoria": {"1": 12, "2": 4, "3": 1, "4": 0, "5": 0, "6": 0},
            "posts_breakout": [  # categoria ≥ 3
                {"post_id": 42, "platform": "TWITTER", "views": 45000, "followers": 3100, "ratio": 14.5, "categoria": 3},
                ...
            ],
            "views_breakout_pct": 18.2,  # % de views totales que vinieron de posts breakout
            "fidelity": "T3_proxy"        # recordatorio: heurística, no reach real
        }
    }

Insufficient data:
    - 0 posts con views > 0 (plataformas sin video o sin columna views poblada)
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.social import SocialPost, SocialProfile
from app.services.diagnostico._common import (
    build_dirigente_not_found,
    build_insufficient,
    build_ok,
    load_dirigente_scoped,
)

BLOQUE = "B02"
VENTANA_DIAS = 90


def _categoria_from_ratio(ratio: float) -> int:
    if ratio <= 1.5:
        return 1
    if ratio <= 3.0:
        return 2
    if ratio <= 10.0:
        return 3
    if ratio <= 50.0:
        return 4
    if ratio <= 500.0:
        return 5
    return 6


async def compute(
    db: AsyncSession,
    dirigente_id: int,
    org_id: int | None = None,
) -> dict:
    dirigente = await load_dirigente_scoped(db, dirigente_id, org_id)
    if dirigente is None:
        return build_dirigente_not_found(BLOQUE, dirigente_id)

    profiles_result = await db.execute(
        select(SocialProfile).where(SocialProfile.dirigente_id == dirigente_id)
    )
    profiles = list(profiles_result.scalars().all())
    if not profiles:
        return build_insufficient(BLOQUE, missing=["social_profiles=0"])

    since = datetime.now(UTC) - timedelta(days=VENTANA_DIAS)
    profile_by_id = {p.id: p for p in profiles}

    posts_result = await db.execute(
        select(SocialPost).where(
            SocialPost.profile_id.in_([p.id for p in profiles]),
            SocialPost.published_at >= since,
            SocialPost.views > 0,
        )
    )
    posts = list(posts_result.scalars().all())
    if not posts:
        return build_insufficient(
            BLOQUE,
            missing=["0 posts con views>0 en 90d (plataformas sin video o ingest sin views)"],
        )

    posts_por_categoria = {str(i): 0 for i in range(1, 7)}
    posts_breakout = []
    max_cat = 1
    total_views = 0
    breakout_views = 0

    for post in posts:
        profile = profile_by_id.get(post.profile_id)
        if profile is None or profile.followers_count <= 0:
            continue
        ratio = (post.views or 0) / profile.followers_count
        cat = _categoria_from_ratio(ratio)
        posts_por_categoria[str(cat)] += 1
        max_cat = max(max_cat, cat)
        total_views += post.views or 0

        if cat >= 3:
            breakout_views += post.views or 0
            posts_breakout.append(
                {
                    "post_id": post.id,
                    "platform": profile.platform.value,
                    "views": post.views,
                    "followers": profile.followers_count,
                    "ratio": round(ratio, 2),
                    "categoria": cat,
                    "published_at": post.published_at.isoformat() if post.published_at else None,
                }
            )

    views_breakout_pct = (breakout_views / total_views * 100.0) if total_views > 0 else 0.0

    # Top 10 breakouts ordenados por ratio
    posts_breakout.sort(key=lambda x: x["ratio"], reverse=True)
    posts_breakout = posts_breakout[:10]

    return build_ok(
        BLOQUE,
        {
            "max_categoria": max_cat,
            "posts_por_categoria": posts_por_categoria,
            "posts_breakout": posts_breakout,
            "views_breakout_pct": round(views_breakout_pct, 2),
            "n_posts_evaluados": len(posts),
            "fidelity": "T3_proxy",
            "nota": "Heurística views/followers. T3 exacto requiere unconnected_reach (Meta Graph/TikTok Business).",
        },
    )
