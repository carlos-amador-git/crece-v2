"""B04 — Benchmark vs competidores directos (proxies D-22).

MASTER §3.1 #04 + D-22.

En S2 los 8 dirigentes piloto tienen ``competidor_directo_ids=[]`` porque los
competidores son conocimiento del cliente (Onboarding S5). Para que el bloque
funcione en S2 se usa fallback a proxies de desarrollo documentados en
``backend/scripts/seed_proxies_desarrollo_s2.py``.

Proxies S2 (fixture desarrollo — NO sale a producción):
    Piña (1)      → [2, 5, 6]   # Solano, Jiménez, Cravioto
    Solano (2)    → [1, 5, 8]
    Pineda (3)    → [4]
    Nolasco (4)   → [3]
    Jiménez (5)   → [1, 2, 7]
    Cravioto (6)  → [1, 5, 7]
    Ballesteros(7)→ [5, 6, 8]
    Máynez (8)    → [2, 5, 7]

Returns:
    {
        "status": "ok",
        "data": {
            "self": {"dirigente_id": 1, "followers_total": ..., "er_avg_pct": ..., "posts_semana": ...},
            "rivales": [{...}],
            "origen_competidores": "dirigente.competidor_directo_ids" | "proxies_s2" | "ninguno"
        }
    }

Insufficient:
    - Sin competidor_directo_ids NI proxy → cannot compare
    - 0 posts del self en 4 semanas → self vacío
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from statistics import mean

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dirigente import Dirigente
from app.models.social import SocialPost, SocialProfile
from app.services.diagnostico._common import (
    build_dirigente_not_found,
    build_insufficient,
    build_ok,
    load_dirigente_scoped,
)

BLOQUE = "B04"
VENTANA_DIAS = 28  # últimas 4 semanas

# TODO(S5): eliminar cuando Onboarding Wizard permita declarar competidores.
# Ver ``backend/scripts/seed_proxies_desarrollo_s2.py`` para fixture canónico.
PROXIES_S2_DESARROLLO: dict[int, list[int]] = {
    1: [2, 5, 6],
    2: [1, 5, 8],
    3: [4],
    4: [3],
    5: [1, 2, 7],
    6: [1, 5, 7],
    7: [5, 6, 8],
    8: [2, 5, 7],
}


async def _stats_dirigente(
    db: AsyncSession, dirigente_id: int, since: datetime
) -> dict | None:
    """Agrega métricas básicas de un dirigente en ventana."""
    profiles_result = await db.execute(
        select(SocialProfile).where(SocialProfile.dirigente_id == dirigente_id)
    )
    profiles = list(profiles_result.scalars().all())
    if not profiles:
        return None

    followers_total = sum(p.followers_count for p in profiles)

    posts_result = await db.execute(
        select(SocialPost).where(
            SocialPost.profile_id.in_([p.id for p in profiles]),
            SocialPost.published_at >= since,
        )
    )
    posts = list(posts_result.scalars().all())

    n_posts = len(posts)
    posts_semana = round(n_posts / 4.0, 2)
    er_values = [p.engagement_rate for p in posts if p.engagement_rate is not None]
    er_avg_pct = round(mean(er_values) * 100.0, 3) if er_values else None
    sentiments = [p.sentiment_score for p in posts if p.sentiment_score is not None]
    sentiment_avg = round(mean(sentiments), 3) if sentiments else None

    return {
        "dirigente_id": dirigente_id,
        "followers_total": followers_total,
        "n_plataformas": len(profiles),
        "posts_28d": n_posts,
        "posts_semana": posts_semana,
        "er_avg_pct": er_avg_pct,
        "sentiment_avg": sentiment_avg,
    }


async def compute(
    db: AsyncSession,
    dirigente_id: int,
    org_id: int | None = None,
) -> dict:
    dirigente = await load_dirigente_scoped(db, dirigente_id, org_id)
    if dirigente is None:
        return build_dirigente_not_found(BLOQUE, dirigente_id)

    since = datetime.now(UTC) - timedelta(days=VENTANA_DIAS)

    # 1) Tomar competidor_directo_ids del modelo
    rivales_ids: list[int] = list(dirigente.competidor_directo_ids or [])
    origen = "dirigente.competidor_directo_ids"

    # 2) Fallback D-22: proxies S2 desarrollo
    if not rivales_ids:
        rivales_ids = PROXIES_S2_DESARROLLO.get(dirigente_id, [])
        origen = "proxies_s2" if rivales_ids else "ninguno"

    self_stats = await _stats_dirigente(db, dirigente_id, since)
    if self_stats is None:
        return build_insufficient(
            BLOQUE, missing=["self sin social_profiles"]
        )

    if not rivales_ids:
        return build_insufficient(
            BLOQUE,
            missing=[
                "dirigente.competidor_directo_ids vacío",
                f"Sin proxy S2 para dirigente_id={dirigente_id}",
                "Competidores se declaran en Onboarding Wizard S5 (D-22)",
            ],
            extra={"self": self_stats, "origen_competidores": origen},
        )

    # 3) Stats rivales
    rivales: list[dict] = []
    rivales_con_data = 0
    for rid in rivales_ids:
        # verificar existencia y scoping (no queremos cruzar orgs)
        rd = await load_dirigente_scoped(db, rid, org_id)
        if rd is None:
            rivales.append({"dirigente_id": rid, "status": "no_encontrado"})
            continue
        stats = await _stats_dirigente(db, rid, since)
        if stats is None:
            rivales.append({"dirigente_id": rid, "status": "sin_profiles", "full_name": rd.full_name})
            continue
        stats["full_name"] = rd.full_name
        stats["status"] = "ok"
        rivales.append(stats)
        rivales_con_data += 1

    if rivales_con_data == 0:
        return build_insufficient(
            BLOQUE,
            missing=["Todos los rivales sin datos en ventana 28d"],
            extra={"self": self_stats, "rivales": rivales, "origen_competidores": origen},
        )

    return build_ok(
        BLOQUE,
        {
            "self": {"full_name": dirigente.full_name, **self_stats},
            "rivales": rivales,
            "origen_competidores": origen,
            "ventana_dias": VENTANA_DIAS,
            "nota_d22": (
                "proxies_s2 es fixture de desarrollo. En producción los competidores "
                "se declaran en Onboarding Wizard (Sprint S5)."
            ),
        },
    )
