"""B03 — Matriz 2×2 de contenido (4 cuadrantes).

MASTER §3.1 #03.

Clasifica cada post en 1 de 4 cuadrantes según:
    eje X: engagement_rate (alto/bajo vs mediana del dirigente)
    eje Y: sentiment_score   (positivo/negativo)

    Cuadrantes:
        INSIGNIA   → engagement alto + sentiment positivo
        CRISIS     → engagement alto + sentiment negativo
        VANIDAD    → engagement bajo + sentiment positivo
        MUERTA     → engagement bajo + sentiment negativo

Returns:
    {
        "status": "ok",
        "data": {
            "posts": [{post_id, platform, engagement_rate, sentiment_score, cuadrante}],
            "conteo_cuadrantes": {
                "INSIGNIA": 5, "CRISIS": 2, "VANIDAD": 8, "MUERTA": 3
            },
            "umbral_engagement": 0.032,   # mediana
            "umbral_sentiment": 0.0,       # sentiment neutral como separador
        }
    }

Insufficient:
    - 0 posts con engagement_rate y sentiment_score no nulos
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from statistics import median

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.social import SocialPost, SocialProfile
from app.services.diagnostico._common import (
    build_dirigente_not_found,
    build_insufficient,
    build_ok,
    load_dirigente_scoped,
)

BLOQUE = "B03"
VENTANA_DIAS = 90
UMBRAL_SENTIMENT = 0.0  # >=0 positivo, <0 negativo


def _cuadrante(engagement: float, sentiment: float, umbral_eng: float) -> str:
    high_eng = engagement >= umbral_eng
    positive = sentiment >= UMBRAL_SENTIMENT
    if high_eng and positive:
        return "INSIGNIA"
    if high_eng and not positive:
        return "CRISIS"
    if not high_eng and positive:
        return "VANIDAD"
    return "MUERTA"


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
            SocialPost.sentiment_score.is_not(None),
        )
    )
    posts = list(posts_result.scalars().all())
    if not posts:
        return build_insufficient(
            BLOQUE, missing=["0 posts con sentiment_score en 90d (falta pipeline NLP)"]
        )

    engagements = [p.engagement_rate for p in posts if p.engagement_rate is not None]
    if not engagements:
        return build_insufficient(BLOQUE, missing=["engagement_rate=NULL en todos los posts"])

    # Mediana sobre ER>0: posts sin ER calculado (=0) no deben arrastrar el umbral
    # a 0 y colapsar la matriz (todo cae en "alto", Neutros/Sin eco imposibles).
    # Los ER=0 caen correctamente en "bajo engagement". Mismo patrón que B15.
    engagements_nonzero = [e for e in engagements if e > 0]
    umbral_eng = median(engagements_nonzero) if engagements_nonzero else 0.0

    clasificados = []
    conteo = {"INSIGNIA": 0, "CRISIS": 0, "VANIDAD": 0, "MUERTA": 0}
    for post in posts:
        if post.engagement_rate is None or post.sentiment_score is None:
            continue
        profile = profile_by_id.get(post.profile_id)
        cuadrante = _cuadrante(post.engagement_rate, post.sentiment_score, umbral_eng)
        conteo[cuadrante] += 1
        clasificados.append(
            {
                "post_id": post.id,
                "platform": profile.platform.value if profile else None,
                "engagement_rate": round(post.engagement_rate, 4),
                "sentiment_score": round(post.sentiment_score, 4),
                "cuadrante": cuadrante,
                "likes": post.likes,
                "comments": post.comments,
                "shares": post.shares,
                "published_at": post.published_at.isoformat() if post.published_at else None,
            }
        )

    return build_ok(
        BLOQUE,
        {
            "posts": clasificados,
            "conteo_cuadrantes": conteo,
            "umbral_engagement": round(umbral_eng, 4),
            "umbral_sentiment": UMBRAL_SENTIMENT,
            "n_posts": len(clasificados),
            "leyenda": {
                "INSIGNIA": "alto engagement + positivo → amplificar",
                "CRISIS": "alto engagement + negativo → contener",
                "VANIDAD": "bajo engagement + positivo → recortar",
                "MUERTA": "bajo engagement + negativo → matar",
            },
        },
    )
