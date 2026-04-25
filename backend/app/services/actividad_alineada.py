"""D-23-G' · KPI Actividad Política Alineada (reemplaza flip de sentimiento).

Plan: .context/PLAN-D-23-G-actividad-alineada-2026-04-24.md

Reformulación del KPI principal de la ficha dirigente. Antes era "Sentimiento
Promedio 7d" con flip × -1 para oposición · ahora es "% de actividad alineada
a rol político" basado en clasificación 4-cat ``target_politico``.

Fórmula por rol político:

- Oposición:    (target=oficialismo + target=propio) / total_clasificado
- Oficialismo:  (target=propio + target=oposicion) / total_clasificado
- Independiente: target=propio / total_clasificado

Posts con ``target_politico`` NULL o `'no_determinado'` quedan EXCLUIDOS del
denominador (no contaminan el KPI · son señal de "aún no clasificado" o
"sin texto suficiente").

Sin flip · sin score numérico ajustado · solo conteo de actividad.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dirigente import Dirigente
from app.models.social import SocialPost, SocialProfile

# Categorías clasificadas que cuentan en el denominador del KPI.
PRODUCTIVE_TARGETS = {"oficialismo", "oposicion", "propio", "personal"}

# Para cada rol, qué targets cuentan en el numerador (alineación a rol).
NUMERATOR_BY_ROL: dict[str, set[str]] = {
    "oposicion": {"oficialismo", "propio"},
    "oficialismo": {"propio", "oposicion"},
    "independiente": {"propio"},
}


async def compute_actividad_alineada(
    db: AsyncSession,
    dirigente: Dirigente,
    *,
    days: int = 7,
) -> dict[str, Any]:
    """Computa KPI Actividad Política Alineada para un dirigente.

    Args:
        db: sesión async SQLAlchemy
        dirigente: instancia ya cargada de ``Dirigente`` (no consulta extra)
        days: ventana en días (default 7)

    Returns:
        dict con campos:
        - score: float 0..1 (proporción alineada · None si no hay clasificados)
        - score_pct: int 0..100 (presentación · None si sin datos)
        - breakdown: {oficialismo, oposicion, propio, personal} con conteos absolutos
        - total_classified: int · posts con target_politico válido (productivos)
        - total_posts_window: int · todos los posts en la ventana (incluye sin clasificar)
        - rol_politico: str · rol del dirigente (oficialismo|oposicion|independiente)
        - days: int · ventana usada
        - empty_state: str | None · 'no_classified' si no hay datos · None si OK
    """
    cutoff = datetime.now(UTC) - timedelta(days=days)

    # Profile IDs del dirigente
    prof_r = await db.execute(
        select(SocialProfile.id).where(SocialProfile.dirigente_id == dirigente.id)
    )
    profile_ids = [pid for (pid,) in prof_r.all()]

    rol = (dirigente.rol_politico or "independiente").lower()
    breakdown = {"oficialismo": 0, "oposicion": 0, "propio": 0, "personal": 0}
    total_classified = 0
    total_posts_window = 0

    if profile_ids:
        # Total posts en la ventana (incluye sin clasificar · para empty state)
        total_r = await db.execute(
            select(func.count(SocialPost.id)).where(
                SocialPost.profile_id.in_(profile_ids),
                SocialPost.published_at >= cutoff,
            )
        )
        total_posts_window = int(total_r.scalar() or 0)

        # Conteos por target_politico (solo productivos)
        breakdown_r = await db.execute(
            select(
                SocialPost.target_politico,
                func.count(SocialPost.id),
            ).where(
                SocialPost.profile_id.in_(profile_ids),
                SocialPost.published_at >= cutoff,
                SocialPost.target_politico.in_(list(PRODUCTIVE_TARGETS)),
            ).group_by(SocialPost.target_politico)
        )
        for tgt, cnt in breakdown_r.all():
            breakdown[tgt] = int(cnt)
            total_classified += int(cnt)

    # Empty state: sin posts clasificados productivos en la ventana
    if total_classified == 0:
        return {
            "score": None,
            "score_pct": None,
            "breakdown": breakdown,
            "total_classified": 0,
            "total_posts_window": total_posts_window,
            "rol_politico": rol,
            "days": days,
            "empty_state": "no_classified",
        }

    # Computar score: proporción de targets en numerador / total clasificado
    numerator_targets = NUMERATOR_BY_ROL.get(rol, NUMERATOR_BY_ROL["independiente"])
    numerator = sum(breakdown[t] for t in numerator_targets)
    score = numerator / total_classified if total_classified > 0 else 0.0

    return {
        "score": round(score, 4),
        "score_pct": round(score * 100),
        "breakdown": breakdown,
        "total_classified": total_classified,
        "total_posts_window": total_posts_window,
        "rol_politico": rol,
        "days": days,
        "empty_state": None,
    }
