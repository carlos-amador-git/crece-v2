"""B06 — Crisis Spike detector (ventana móvil 2h vs baseline).

MASTER §3.1 #06.

Detecta spike de toxicity / anger en ventana móvil 2h comparado contra baseline
de los últimos 7 días. Spike = velocidad (posts tóxicos/hora) > baseline × 3.

Heurística:
    1. Baseline 7d: n posts tóxicos / 168 horas
    2. Ventana activa 2h: n posts tóxicos / 2
    3. severity = min(actual / max(baseline, 0.1), 1.0)
    4. spike_detected = actual > baseline * 3

Post tóxico = sentiment_score < -0.4 OR emotions.anger > 0.5 OR
              sentiment_analyses.is_toxic=true.

Returns:
    {
        "status": "ok",
        "data": {
            "spike_detected": bool,
            "severity": 0.0-1.0,
            "ventana_inicio": ISO,
            "ventana_fin": ISO,
            "posts_toxicos_2h": 4,
            "posts_toxicos_baseline_hora": 0.08,
            "tasa_actual_hora": 2.0,
            "toxic_posts": [{post_id, platform, sentiment_score, emotions}]
        }
    }

Insufficient:
    - 0 posts con sentiment_score en 7d
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.social import SentimentAnalysis, SocialPost, SocialProfile
from app.services.diagnostico._common import (
    build_dirigente_not_found,
    build_insufficient,
    build_ok,
    load_dirigente_scoped,
)

BLOQUE = "B06"
VENTANA_ACTIVA_H = 2
VENTANA_BASELINE_H = 24 * 7  # 168h
UMBRAL_TOXIC_SENTIMENT = -0.4
UMBRAL_ANGER = 0.5
MULTIPLICADOR_SPIKE = 3.0


def _is_toxic_post(post: SocialPost, analyses_by_post: dict[int, list[SentimentAnalysis]]) -> bool:
    if post.sentiment_score is not None and post.sentiment_score < UMBRAL_TOXIC_SENTIMENT:
        return True
    if isinstance(post.emotions, dict):
        anger = post.emotions.get("anger") or post.emotions.get("ANGER") or 0
        try:
            if float(anger) >= UMBRAL_ANGER:
                return True
        except (TypeError, ValueError):
            pass
    for a in analyses_by_post.get(post.id, []):
        if a.is_toxic:
            return True
    return False


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

    now = datetime.now(UTC)
    baseline_since = now - timedelta(hours=VENTANA_BASELINE_H)
    active_since = now - timedelta(hours=VENTANA_ACTIVA_H)

    posts_result = await db.execute(
        select(SocialPost).where(
            SocialPost.profile_id.in_([p.id for p in profiles]),
            SocialPost.published_at >= baseline_since,
        )
    )
    posts = list(posts_result.scalars().all())
    if not posts:
        return build_insufficient(
            BLOQUE, missing=[f"0 posts en últimas {VENTANA_BASELINE_H}h (7d)"]
        )

    # Analyses por post (para fallback is_toxic)
    post_ids = [p.id for p in posts]
    analyses_result = await db.execute(
        select(SentimentAnalysis).where(SentimentAnalysis.post_id.in_(post_ids))
    )
    analyses = list(analyses_result.scalars().all())
    analyses_by_post: dict[int, list[SentimentAnalysis]] = {}
    for a in analyses:
        analyses_by_post.setdefault(a.post_id, []).append(a)

    toxic_all = [p for p in posts if _is_toxic_post(p, analyses_by_post)]
    toxic_active = [p for p in toxic_all if p.published_at and p.published_at >= active_since]
    toxic_baseline = [p for p in toxic_all if p.published_at and p.published_at < active_since]

    tasa_actual = len(toxic_active) / VENTANA_ACTIVA_H
    tasa_baseline = len(toxic_baseline) / max(VENTANA_BASELINE_H - VENTANA_ACTIVA_H, 1)

    spike = tasa_actual > tasa_baseline * MULTIPLICADOR_SPIKE and len(toxic_active) >= 2
    severity = min(tasa_actual / max(tasa_baseline * MULTIPLICADOR_SPIKE, 0.1), 1.0)

    profile_by_id = {p.id: p for p in profiles}
    toxic_posts_preview = [
        {
            "post_id": p.id,
            "platform": profile_by_id[p.profile_id].platform.value
            if p.profile_id in profile_by_id else None,
            "sentiment_score": p.sentiment_score,
            "emotions": p.emotions,
            "published_at": p.published_at.isoformat() if p.published_at else None,
        }
        for p in toxic_active[:10]
    ]

    return build_ok(
        BLOQUE,
        {
            "spike_detected": spike,
            "severity": round(severity, 3),
            "ventana_inicio": active_since.isoformat(),
            "ventana_fin": now.isoformat(),
            "posts_toxicos_2h": len(toxic_active),
            "posts_toxicos_baseline_hora": round(tasa_baseline, 4),
            "tasa_actual_hora": round(tasa_actual, 4),
            "toxic_posts": toxic_posts_preview,
            "umbrales": {
                "sentiment_score": UMBRAL_TOXIC_SENTIMENT,
                "anger": UMBRAL_ANGER,
                "multiplicador_spike": MULTIPLICADOR_SPIKE,
            },
        },
    )
