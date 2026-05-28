"""B05 — Sentiment composition Plutchik 6 emociones.

MASTER §3.1 #05.

Agrega las 6 emociones Plutchik discretas presentes en ``social_posts.emotions``
(poblado por Sprint S1 T5 Gemma 3:12b) y ``sentiment_analyses.emotions`` (Layer 2
NLP sobre comments). Emociones trackeadas:

    trust · anger · joy · fear · sadness · disgust

Compute lógica:
    1. Extraer ``emotions`` JSONB dict de social_posts (proxy caption sentiment)
    2. Extraer ``emotions`` de sentiment_analyses (agregado sobre comments)
    3. Promediar por emoción
    4. Reportar ratio trust/anger y warnings si ratio < 1 o anger > 0.30

Returns:
    {
        "status": "ok",
        "data": {
            "emociones_promedio": {"trust": 0.21, "anger": 0.15, ...},
            "n_posts_con_emotions": 45,
            "n_comments_con_emotions": 120,
            "ratio_trust_anger": 1.4,
            "warnings": ["anger 35% supera umbral 30%"],
        }
    }

Insufficient:
    - 0 posts con ``emotions`` populated (Sprint S2 T3 extensión pendiente)
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

BLOQUE = "B05"
VENTANA_DIAS = 90
# Ekman-7 lo que el NLP (pysentimiento) realmente emite. Antes el código declaraba
# `PLUTCHIK_6` con `trust` y `anticipation` que el modelo nunca pobla — ratio_trust_anger
# siempre era 0.0 → señal "Hostilidad" falsa. D-EKMAN-1 (2026-05-12).
EKMAN_6 = ["joy", "anger", "sadness", "fear", "disgust", "surprise"]
# alias retro-compat (otros servicios la importan)
PLUTCHIK_6 = EKMAN_6

UMBRAL_ANGER_ALERTA = 0.30
UMBRAL_RATIO_JA_MIN = 1.0
# alias retro-compat
UMBRAL_RATIO_TA_MIN = UMBRAL_RATIO_JA_MIN


def _normalize_emotions(raw: dict | None) -> dict[str, float]:
    """Normaliza el dict emotions extrayendo las 6 Ekman (acepta claves mixtas)."""
    if not isinstance(raw, dict):
        return {}
    
    # Soporte para nesting legacy Plutchik (Sprint S2 T3)
    data = raw.get("plutchik_6") if "plutchik_6" in raw else raw
    if not isinstance(data, dict):
        return {}

    out: dict[str, float] = {}
    for emo in EKMAN_6:
        val = data.get(emo)
        if val is None:
            val = data.get(emo.upper())
        if val is None:
            val = data.get(emo.capitalize())
        if isinstance(val, (int, float)):
            out[emo] = float(val)
    return out


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
    profile_ids = [p.id for p in profiles]

    posts_result = await db.execute(
        select(SocialPost).where(
            SocialPost.profile_id.in_(profile_ids),
            SocialPost.published_at >= since,
            SocialPost.emotions.is_not(None),
        )
    )
    posts = list(posts_result.scalars().all())

    sa_result = await db.execute(
        select(SentimentAnalysis)
        .join(SocialPost, SentimentAnalysis.post_id == SocialPost.id)
        .where(
            SocialPost.profile_id.in_(profile_ids),
            SocialPost.published_at >= since,
            SentimentAnalysis.emotions.is_not(None),
        )
    )
    analyses = list(sa_result.scalars().all())

    if not posts and not analyses:
        return build_insufficient(
            BLOQUE,
            missing=[
                "social_posts.emotions=NULL en todos los posts 90d",
                "sentiment_analyses.emotions=NULL en todos los analyses 90d",
                "Sprint S2 T3 extensión NLP Plutchik pendiente (cierre Joy 2026-04-19)",
            ],
        )

    acumulado: dict[str, list[float]] = {e: [] for e in EKMAN_6}
    for p in posts:
        ems = _normalize_emotions(p.emotions)
        for k, v in ems.items():
            acumulado[k].append(v)
    for a in analyses:
        ems = _normalize_emotions(a.emotions)
        for k, v in ems.items():
            acumulado[k].append(v)

    emociones_promedio: dict[str, float] = {}
    total_ekman = 0.0
    for emo in EKMAN_6:
        values = acumulado[emo]
        avg = round(sum(values) / len(values), 4) if values else 0.0
        emociones_promedio[emo] = avg
        total_ekman += avg

    # Normalización para visibilidad en Radar: 
    # El usuario se queja de que solo ve joy/anger. Si others=90%, las ekman son <1%.
    # Normalizamos el set Ekman-6 para que su distribución interna sea visible.
    if total_ekman > 0:
        for emo in EKMAN_6:
            emociones_promedio[emo] = round(emociones_promedio[emo] / total_ekman, 4)

    joy = emociones_promedio["joy"]
    anger = emociones_promedio["anger"]
    ratio = round(joy / anger, 3) if anger > 0 else None

    warnings: list[str] = []
    if anger >= UMBRAL_ANGER_ALERTA:
        warnings.append(f"anger {anger * 100:.0f}% supera umbral {UMBRAL_ANGER_ALERTA * 100:.0f}%")
    if ratio is not None and ratio < UMBRAL_RATIO_JA_MIN:
        warnings.append(f"ratio joy/anger {ratio} < umbral {UMBRAL_RATIO_JA_MIN}")

    return build_ok(
        BLOQUE,
        {
            "emociones_promedio": emociones_promedio,
            "n_posts_con_emotions": len(posts),
            "n_comments_con_emotions": len(analyses),
            "ratio_joy_anger": ratio,
            # alias retro-compat para frontend viejo durante migración
            "ratio_trust_anger": ratio,
            "warnings": warnings,
            "ventana_dias": VENTANA_DIAS,
        },
    )
