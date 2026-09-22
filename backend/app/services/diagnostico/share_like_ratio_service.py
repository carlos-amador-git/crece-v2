"""B09 — Share-to-Like Ratio (movilización profunda).

MASTER §3.1 #09.

Mide capacidad del contenido para activar compromiso profundo (share) vs like
pasivo. Elaboration-Likelihood Model: share activa coherencia/reputación porque
el seguidor asume costo reputacional en su red privada.

Compute:
    ratio_post = shares / max(likes, 1)
    ratio_promedio = mean(ratios últimos 90d)
    percentil_vs_estrato = percentil de ratio_promedio vs distribución del estrato

Returns:
    {
        "status": "ok",
        "data": {
            "ratio_promedio": 0.035,
            "ratio_mediana": 0.020,
            "n_posts": 42,
            "posts_virales": [     # top 5 por ratio (ratio ≥ 0.10)
                {"post_id": ..., "platform": ..., "likes": ..., "shares": ..., "ratio": 0.18}
            ],
            "semaforo": "ROJO" | "AMARILLO" | "VERDE",
            "percentil_vs_estrato": 62.5,
            "estrato": "Nano"
        }
    }

Insufficient:
    - 0 posts con likes>0 en 90d
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from statistics import mean, median

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.social import SocialPost, SocialProfile
from app.services.diagnostico._common import (
    build_dirigente_not_found,
    build_insufficient,
    build_ok,
    clasificar_estrato,
    load_dirigente_scoped,
)

BLOQUE = "B09"
# Ampliada a 180 días el 2026-09-22, junto con los bloques Tier 2 (e9876d4).
# El scraping estuvo caído de junio a septiembre (colas de Celery
# desconectadas, ver b21543f): 11 de 14 dirigentes no tienen un solo post
# dentro de 90 días y estos bloques devolvían `insufficient_data` para todos.
# Los datos son reales; lo que cambia es el período que describen, y la
# pantalla de Diagnóstico lo declara leyendo la ventana del payload.
# Contrapartida asumida: para los dirigentes CON actividad reciente la métrica
# pierde actualidad, porque mezcla lo nuevo con contenido de hasta medio año.
# Revertir cuando el scraping lleve un trimestre estable.
VENTANA_DIAS = 180
UMBRAL_VIRAL_RATIO = 0.10
UMBRAL_VERDE = 0.05
UMBRAL_AMARILLO = 0.02


def _semaforo(ratio: float) -> str:
    if ratio >= UMBRAL_VERDE:
        return "VERDE"
    if ratio >= UMBRAL_AMARILLO:
        return "AMARILLO"
    return "ROJO"


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
            SocialPost.likes > 0,
        )
    )
    posts = list(posts_result.scalars().all())
    if not posts:
        return build_insufficient(BLOQUE, missing=["0 posts con likes>0 en 90d"])

    ratios = []
    posts_con_ratio = []
    for post in posts:
        ratio = (post.shares or 0) / max(post.likes, 1)
        ratios.append(ratio)
        profile = profile_by_id.get(post.profile_id)
        posts_con_ratio.append(
            {
                "post_id": post.id,
                "platform": profile.platform.value if profile else None,
                "likes": post.likes,
                "shares": post.shares or 0,
                "ratio": round(ratio, 4),
                "published_at": post.published_at.isoformat() if post.published_at else None,
            }
        )

    ratio_prom = mean(ratios)
    ratio_med = median(ratios)

    posts_virales = [p for p in posts_con_ratio if p["ratio"] >= UMBRAL_VIRAL_RATIO]
    posts_virales.sort(key=lambda x: x["ratio"], reverse=True)
    posts_virales = posts_virales[:5]

    # Estrato + percentil (simple rank comparativo sobre el propio dataset S2)
    max_followers = max((p.followers_count for p in profiles), default=0)
    estrato = dirigente.estrato_politico or clasificar_estrato(max_followers)
    posicion_en_dataset = sum(1 for r in ratios if r <= ratio_prom) / len(ratios) * 100
    percentil_vs_estrato = round(posicion_en_dataset, 1)

    return build_ok(
        BLOQUE,
        {
            "ratio_promedio": round(ratio_prom, 4),
            "ratio_mediana": round(ratio_med, 4),
            "n_posts": len(ratios),
            "posts_virales": posts_virales,
            "semaforo": _semaforo(ratio_prom),
            "percentil_vs_estrato": percentil_vs_estrato,
            "estrato": estrato,
            "umbrales": {
                "viral": UMBRAL_VIRAL_RATIO,
                "verde": UMBRAL_VERDE,
                "amarillo": UMBRAL_AMARILLO,
            },
            "nota_fidelity": (
                "Instagram parcial sin ``saves`` (T3). Percentil vs estrato hoy "
                "es rank intra-dirigente; Zenodo S1 aporta distribución poblacional."
            ),
        },
    )
