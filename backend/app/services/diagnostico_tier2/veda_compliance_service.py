"""B17 — Veda INE Compliance (MASTER §3.2 #17).

Filtro heurístico que evalúa si los posts recientes del dirigente (últimos
14 días) contienen keywords prohibidas en ventana veda electoral y si el
dirigente/distrito está actualmente en ventana de veda.

Lógica simplificada (Sprint S3):

    1. ``ventana_veda_activa``: configurable vía environment o parámetro
       ``en_veda`` del caller. En ausencia de calendario electoral por
       distrito, se asume False (modo informativo).
    2. ``posts_riesgo``: posts en los últimos N días que contienen keywords
       prohibidas. SIEMPRE se reporta (aun sin veda activa) para previsión.
    3. ``puede_publicar``: True si no hay veda activa O True-con-riesgo si
       hay veda pero el texto del borrador no toca keywords.

Returns:
    {
        "puede_publicar": true,
        "razon": "sin veda activa",
        "ventana_veda_activa": false,
        "posts_riesgo": [...],
        "n_posts_analizados": 45,
        "keywords_prohibidas": [...]
    }

Insufficient:
    - 0 posts en ventana analizada (sin datos para reportar)
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.social import SocialPost, SocialProfile
from app.services.diagnostico_tier2._common import (
    VEDA_KEYWORDS_PROHIBIDAS,
    build_dirigente_not_found,
    build_insufficient,
    build_ok,
    load_dirigente_scoped,
)

BLOQUE = "B17"
VENTANA_DIAS = 14


def _detecta_keywords(content: str | None) -> list[str]:
    if not content:
        return []
    t = content.lower()
    return [k for k in VEDA_KEYWORDS_PROHIBIDAS if k in t]


async def compute(
    db: AsyncSession,
    dirigente_id: int,
    org_id: int | None = None,
    en_veda: bool = False,
) -> dict:
    """Compute B17.

    Args:
        en_veda: flag externo que indica si la fecha actual está dentro de
                 ventana veda INE. Default False (modo informativo). El
                 calendario electoral por distrito se agregará en Sprint S4.
    """
    dirigente = await load_dirigente_scoped(db, dirigente_id, org_id)
    if dirigente is None:
        return build_dirigente_not_found(BLOQUE, dirigente_id)

    profiles_res = await db.execute(
        select(SocialProfile).where(SocialProfile.dirigente_id == dirigente_id)
    )
    profile_ids = [p.id for p in profiles_res.scalars().all()]
    if not profile_ids:
        return build_insufficient(BLOQUE, missing=["social_profiles=0"])

    since = datetime.now(UTC) - timedelta(days=VENTANA_DIAS)
    posts_res = await db.execute(
        select(SocialPost).where(
            SocialPost.profile_id.in_(profile_ids),
            SocialPost.published_at >= since,
        )
    )
    posts = list(posts_res.scalars().all())
    if not posts:
        return build_insufficient(
            BLOQUE, missing=[f"0 posts en últimos {VENTANA_DIAS} días"]
        )

    riesgo: list[dict] = []
    for p in posts:
        kw = _detecta_keywords(p.content)
        if kw:
            riesgo.append(
                {
                    "post_id": p.id,
                    "published_at": p.published_at.isoformat() if p.published_at else None,
                    "keywords_detectadas": kw,
                    "snippet": (p.content or "")[:150],
                    "platform": None,
                }
            )

    if en_veda:
        puede_publicar = len(riesgo) == 0
        razon = (
            "Veda activa sin keywords prohibidas en recientes"
            if puede_publicar
            else f"Veda activa + {len(riesgo)} posts con keywords prohibidas"
        )
    else:
        puede_publicar = True
        razon = "sin veda activa — modo informativo"

    return build_ok(
        BLOQUE,
        {
            "puede_publicar": puede_publicar,
            "razon": razon,
            "ventana_veda_activa": en_veda,
            "posts_riesgo": riesgo,
            "n_posts_analizados": len(posts),
            "n_posts_riesgo": len(riesgo),
            "keywords_prohibidas": VEDA_KEYWORDS_PROHIBIDAS,
            "ventana_dias": VENTANA_DIAS,
            "calendario_electoral_distrito": (
                "no implementado Sprint S3 — Sprint S4 integrará calendario INE por distrito"
            ),
            "distrito": dirigente.seccion_electoral,
        },
    )
