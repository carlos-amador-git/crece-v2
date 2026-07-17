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

# Pesos neutros · KPI default (sin ajuste del dirigente).
DEFAULT_PESOS: dict[str, float] = {
    "oficialismo": 1.0,
    "oposicion": 1.0,
    "propio": 1.0,
    "personal": 1.0,
}


async def compute_actividad_alineada(
    db: AsyncSession,
    dirigente: Dirigente,
    *,
    days: int = 7,
    modo: str = "default",
) -> dict[str, Any]:
    """Computa KPI Actividad Política Alineada para un dirigente.

    Args:
        db: sesión async SQLAlchemy
        dirigente: instancia ya cargada de ``Dirigente`` (no consulta extra)
        days: ventana en días (default 7)
        modo: "default" (pesos=1.0 · KPI IA pura · usado en comparativas) o
              "ajustado" (usa ``dirigente.pesos_target_politico`` · vista personal)

    Returns:
        dict con campos:
        - score: float 0..1 (proporción alineada · None si no hay clasificados)
        - score_pct: int 0..100 (presentación · None si sin datos)
        - breakdown: {oficialismo, oposicion, propio, personal} con conteos absolutos
        - total_classified: int · posts con target_politico válido (productivos)
        - total_posts_window: int · todos los posts en la ventana (incluye sin clasificar)
        - rol_politico: str · rol del dirigente (oficialismo|oposicion|independiente)
        - days: int · ventana usada
        - modo: str · "default" o "ajustado"
        - pesos: dict · pesos efectivamente usados en el cálculo
        - empty_state: str | None · 'no_classified' si no hay datos · None si OK
    """
    cutoff = datetime.now(UTC) - timedelta(days=days)

    # Profile IDs del dirigente
    prof_r = await db.execute(
        select(SocialProfile.id).where(SocialProfile.dirigente_id == dirigente.id)
    )
    profile_ids = [pid for (pid,) in prof_r.all()]

    # DISENO-actores-politicos-2026-07-16: rol NULL NO cae en silencio a
    # "independiente" — la fórmula del KPI depende del rol (D-23-H) y un
    # fallback silencioso produce números con apariencia válida pero fórmula
    # equivocada. Fallo VISIBLE: empty_state explícito, score None.
    if not dirigente.rol_politico:
        return {
            "score": None,
            "score_pct": None,
            "breakdown": {"oficialismo": 0, "oposicion": 0, "propio": 0, "personal": 0},
            "total_classified": 0,
            "total_posts_window": 0,
            "rol_politico": None,
            "days": days,
            "modo": modo,
            "pesos": dict(DEFAULT_PESOS),
            "empty_state": "rol_sin_clasificar",
        }
    rol = dirigente.rol_politico.lower()
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

    # Pesos efectivos según modo. modo="default" mantiene la fórmula original
    # (KPI IA pura · usada en comparativas inter-dirigentes). modo="ajustado"
    # aplica los pesos personales del dirigente · vista personal.
    if modo == "ajustado":
        raw = dirigente.pesos_target_politico or DEFAULT_PESOS
        pesos = {k: float(raw.get(k, 1.0)) for k in DEFAULT_PESOS}
    else:
        pesos = dict(DEFAULT_PESOS)

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
            "modo": modo,
            "pesos": pesos,
            "empty_state": "no_classified",
        }

    # Computar score ponderado:
    #   numerador = sum(pesos[t] * count[t]) para t en NUMERATOR_BY_ROL[rol]
    #   denominador = sum(pesos[t] * count[t]) para t en PRODUCTIVE_TARGETS
    #   score = numerador / denominador
    numerator_targets = NUMERATOR_BY_ROL.get(rol, NUMERATOR_BY_ROL["independiente"])
    weighted_num = sum(pesos[t] * breakdown[t] for t in numerator_targets)
    weighted_den = sum(pesos[t] * breakdown[t] for t in PRODUCTIVE_TARGETS)
    score = weighted_num / weighted_den if weighted_den > 0 else 0.0

    return {
        "score": round(score, 4),
        "score_pct": round(score * 100),
        "breakdown": breakdown,
        "total_classified": total_classified,
        "total_posts_window": total_posts_window,
        "rol_politico": rol,
        "days": days,
        "modo": modo,
        "pesos": pesos,
        "empty_state": None,
    }
