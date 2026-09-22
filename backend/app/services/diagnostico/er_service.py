"""B01 — Engagement Rate normalizado por estrato político.

MASTER §3.1 #01 · D-19.

Compara ER observado (últimos 90d) contra la matriz 5×5 estrato × plataforma,
aplicando modificador temporal de ventana electoral si aplica (off por default
para perfiles ``politico_activo`` / ``funcionario_gobierno``).

ER observado = sum(likes + comments + shares) / max(views, followers) por post,
promediado por plataforma.

Formula MASTER §3.1 #01:
    ER_esperado(dir, platform, fecha) =
        matriz_base[estrato][platform] × multiplicador_temporal(distrito, fecha)

Returns:
    {
        "status": "ok",
        "data": {
            "er_por_plataforma": {
                "TWITTER": {
                    "er_actual_pct": 4.2,
                    "er_esperado_rango_pct": [3.5, 6.0],
                    "ratio_vs_min": 1.20,  # 20% arriba del piso
                    "n_posts": 18,
                },
                ...
            },
            "estrato": "Nano",
            "estrato_inferido": true | false,
            "modificador_temporal": 1.0,  # ciclo normal (política_activo default)
            "ventana_electoral_activa": false,
        }
    }

Insufficient data cuando:
    - 0 social_profiles registrados
    - 0 posts en 90d
    - followers=0 y views=0 (ER no computable)
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.social import SocialPost, SocialProfile
from app.services.diagnostico._common import (
    ZENODO_VALIDATED_CELLS,
    MATRIZ_ER_5x5,
    build_dirigente_not_found,
    build_insufficient,
    build_ok,
    clasificar_estrato,
    load_dirigente_scoped,
    modificador_temporal,
)

BLOQUE = "B01"
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


async def compute(
    db: AsyncSession,
    dirigente_id: int,
    org_id: int | None = None,
    dias_a_comicio: int | None = None,
) -> dict:
    """Compute ER normalizado por estrato para todas las plataformas del dirigente.

    Args:
        dias_a_comicio: si ``None`` → ciclo normal (modificador 1.0). El caller
            (endpoint) decide si activa modificador temporal según perfil del
            dirigente (§1.5 MASTER — politico_activo default OFF).
    """
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

    max_followers = max((p.followers_count for p in profiles), default=0)
    estrato = dirigente.estrato_politico or clasificar_estrato(max_followers)
    estrato_inferido = dirigente.estrato_politico is None

    if estrato not in MATRIZ_ER_5x5:
        estrato = "Nano"  # fallback conservador

    multiplicador = modificador_temporal(dias_a_comicio)

    er_por_plataforma: dict[str, dict] = {}
    n_posts_total = 0

    for profile in profiles:
        posts_result = await db.execute(
            select(SocialPost).where(
                SocialPost.profile_id == profile.id,
                SocialPost.published_at >= since,
            )
        )
        posts = list(posts_result.scalars().all())
        if not posts:
            continue

        # ER observado por post: (likes + comments + shares) / max(views, followers)
        # Agregado por plataforma = promedio ponderado por ``reach_denominator``.
        sum_engagement = 0
        sum_denominator = 0
        for p in posts:
            engagement = (p.likes or 0) + (p.comments or 0) + (p.shares or 0)
            denom = max(p.views or 0, profile.followers_count or 0)
            if denom <= 0:
                continue
            sum_engagement += engagement
            sum_denominator += denom

        if sum_denominator == 0:
            continue

        er_pct = (sum_engagement / sum_denominator) * 100.0

        # Rango esperado con modificador temporal
        rango_base = MATRIZ_ER_5x5[estrato].get(profile.platform)
        if rango_base is None:
            continue
        rango_adj = (rango_base[0] * multiplicador, rango_base[1] * multiplicador)

        ratio_vs_min = er_pct / rango_adj[0] if rango_adj[0] > 0 else None
        dentro_rango = rango_adj[0] <= er_pct <= rango_adj[1]
        posicion = (
            "sobre_rango" if er_pct > rango_adj[1]
            else "bajo_rango" if er_pct < rango_adj[0]
            else "dentro_rango"
        )

        er_por_plataforma[profile.platform.value] = {
            "er_actual_pct": round(er_pct, 3),
            "er_esperado_rango_pct": [round(rango_adj[0], 3), round(rango_adj[1], 3)],
            "ratio_vs_min": round(ratio_vs_min, 3) if ratio_vs_min is not None else None,
            "posicion": posicion,
            "dentro_rango": dentro_rango,
            "n_posts": len(posts),
            "followers": profile.followers_count,
            "zenodo_validated": (estrato, profile.platform) in ZENODO_VALIDATED_CELLS,
        }
        n_posts_total += len(posts)

    if not er_por_plataforma:
        return build_insufficient(
            BLOQUE,
            missing=[
                "0 posts con denominador no-cero en últimos 90d",
                "(posts carecen de views y followers=0)",
            ],
        )

    return build_ok(
        BLOQUE,
        {
            "er_por_plataforma": er_por_plataforma,
            "estrato": estrato,
            "estrato_inferido": estrato_inferido,
            "modificador_temporal": round(multiplicador, 3),
            "ventana_electoral_activa": dias_a_comicio is not None and dias_a_comicio <= 180,
            "dias_a_comicio": dias_a_comicio,
            "ventana_dias_analizada": VENTANA_DIAS,
            "n_posts_total": n_posts_total,
            "matriz_version": "5x5-zenodo-v1-2026-04-19",
        },
    )
