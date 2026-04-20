"""B16 — Rastreador Promesas de Campaña (MASTER §3.2 #16).

Lee la tabla ``promesas_dirigente`` y correlaciona los textos de las promesas
con posts recientes del dirigente para detectar:

    - cumplidas: posts recientes contienen keywords de la promesa + tono
                 positivo/logro
    - contradichas: posts recientes contienen keywords de la promesa + tono
                    de retractación, cambio de opinión, o acción contraria
    - pendientes: sin evidencia en posts, fecha_compromiso ya vencida

Metodología:
    - Tokenización de texto_promesa → keywords significativas
    - Para cada post en ventana de análisis, intersección de tokens
    - Co-ocurrencia >= 60% keywords clave + verificación tonal simple

Returns:
    {
        "promesas_cumplidas": [...],
        "promesas_pendientes": [...],
        "promesas_contradichas": [...],
        "n_promesas_total": 10,
        "pct_cumplidas": 40.0,
    }

Insufficient:
    - 0 promesas registradas en la tabla para el dirigente
"""
from __future__ import annotations

import re
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.promesa_dirigente import PromesaDirigente, PromesaEstado
from app.models.social import SocialPost, SocialProfile
from app.services.diagnostico_tier2._common import (
    build_dirigente_not_found,
    build_insufficient,
    build_ok,
    load_dirigente_scoped,
)

BLOQUE = "B16"
VENTANA_DIAS_POSTS = 180
UMBRAL_MATCH_KEYWORDS = 0.6  # 60% de keywords presentes

STOPWORDS = {
    "el", "la", "los", "las", "un", "una", "de", "del", "al", "a",
    "en", "y", "o", "que", "por", "para", "con", "sin", "sobre",
    "como", "pero", "si", "es", "son", "será", "sera", "fue", "va",
    "me", "te", "se", "le", "lo", "mi", "tu", "su", "más", "mas",
    "voy", "vamos", "vamos a", "prometo",
}
CONTRA_TOKENS = {
    "no", "nunca", "jamás", "jamas", "cancelamos", "canceló", "cancelo",
    "imposible", "renuncié", "renuncie", "postergar", "pospuesto", "retiro",
    "retracto", "retracté", "retracte",
}


def _keywords(text: str) -> set[str]:
    text = re.sub(r"[^\wáéíóúñü ]", " ", text.lower())
    return {t for t in text.split() if len(t) >= 4 and t not in STOPWORDS}


def _match_ratio(kw_promesa: set[str], content: str) -> float:
    if not kw_promesa or not content:
        return 0.0
    kw_post = _keywords(content)
    inter = kw_promesa & kw_post
    return len(inter) / max(len(kw_promesa), 1)


async def compute(
    db: AsyncSession,
    dirigente_id: int,
    org_id: int | None = None,
) -> dict:
    dirigente = await load_dirigente_scoped(db, dirigente_id, org_id)
    if dirigente is None:
        return build_dirigente_not_found(BLOQUE, dirigente_id)

    res = await db.execute(
        select(PromesaDirigente).where(PromesaDirigente.dirigente_id == dirigente_id)
    )
    promesas = list(res.scalars().all())
    if not promesas:
        return build_insufficient(
            BLOQUE,
            missing=[
                "0 promesas registradas en `promesas_dirigente` para este dirigente",
                "Para activar B16, registrar promesas vía endpoint admin o seed",
            ],
        )

    since = datetime.now(UTC) - timedelta(days=VENTANA_DIAS_POSTS)
    profiles_res = await db.execute(
        select(SocialProfile).where(SocialProfile.dirigente_id == dirigente_id)
    )
    profile_ids = [p.id for p in profiles_res.scalars().all()]
    posts: list[SocialPost] = []
    if profile_ids:
        posts_res = await db.execute(
            select(SocialPost).where(
                SocialPost.profile_id.in_(profile_ids),
                SocialPost.published_at >= since,
                SocialPost.content.is_not(None),
            )
        )
        posts = list(posts_res.scalars().all())

    cumplidas: list[dict] = []
    pendientes: list[dict] = []
    contradichas: list[dict] = []
    hoy = date.today()

    for pr in promesas:
        kws = _keywords(pr.texto_promesa)
        posts_match: list[dict] = []
        posts_contra: list[dict] = []
        for post in posts:
            ratio = _match_ratio(kws, post.content or "")
            if ratio < UMBRAL_MATCH_KEYWORDS:
                continue
            post_tokens = (post.content or "").lower().split()
            contradice = any(ct in post_tokens for ct in CONTRA_TOKENS)
            ref = {
                "post_id": post.id,
                "match_ratio": round(ratio, 3),
                "published_at": post.published_at.isoformat() if post.published_at else None,
                "snippet": (post.content or "")[:120],
            }
            if contradice:
                posts_contra.append(ref)
            else:
                posts_match.append(ref)

        base = {
            "promesa_id": pr.id,
            "texto_promesa": pr.texto_promesa,
            "fecha_compromiso": pr.fecha_compromiso.isoformat() if pr.fecha_compromiso else None,
            "estado_registrado": pr.estado.value if pr.estado else None,
            "evidencia_url": pr.evidencia_url,
            "keywords_promesa": sorted(list(kws))[:10],
            "posts_match": posts_match[:5],
            "posts_contradictorios": posts_contra[:5],
        }

        # Clasificación: estado DB > evidencia de posts
        if pr.estado == PromesaEstado.CUMPLIDA or posts_match:
            cumplidas.append(base)
        elif pr.estado == PromesaEstado.CONTRADICHA or posts_contra:
            contradichas.append(base)
        else:
            vencida = (
                pr.fecha_compromiso is not None
                and pr.fecha_compromiso < hoy
            )
            pendientes.append({**base, "vencida": vencida})

    total = len(promesas)
    pct_cumplidas = round((len(cumplidas) / total) * 100.0, 2)

    return build_ok(
        BLOQUE,
        {
            "promesas_cumplidas": cumplidas,
            "promesas_pendientes": pendientes,
            "promesas_contradichas": contradichas,
            "n_promesas_total": total,
            "pct_cumplidas": pct_cumplidas,
            "ventana_posts_dias": VENTANA_DIAS_POSTS,
            "umbral_match_keywords": UMBRAL_MATCH_KEYWORDS,
            "metodologia": "keyword_cooccurrence_v1",
        },
    )
