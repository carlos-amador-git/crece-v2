"""Shared helpers for Sprint S2 Tier 1 diagnóstico services.

MASTER §3.1 · Sprint S2. Centraliza:

- Carga de Dirigente con RLS (org_id scoping)
- Matriz 5×5 estrato × plataforma (D-19)
- Modificador temporal rampa 180d/90d/30d/veda (D-19)
- Clasificación de estrato por followers cuando falta ``estrato_politico``
- Shape estándar de response (``ok`` / ``insufficient_data``)

Todas las celdas de la matriz 5×5 están marcadas 🟡 TBD hasta validación Zenodo
(Sprint S1 cierre). El valor medio del rango se usa como ``er_esperado_pct`` base,
y el rango completo se reporta al cliente como ``rango_estrato``.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dirigente import Dirigente
from app.models.social import Platform

# ── Matriz 5×5 estrato × plataforma (MASTER §3.1 #01 — D-19) ──────────────
# Rangos (min%, max%) pre-modificador temporal. Unidades: porcentaje puntos.
# TODAS las celdas son 🟡 TBD hasta validación Zenodo (Sprint S1).
MATRIZ_ER_5x5: dict[str, dict[Platform, tuple[float, float]]] = {
    "Nano": {
        Platform.TWITTER:   (3.5, 6.0),
        Platform.INSTAGRAM: (5.0, 9.0),
        Platform.FACEBOOK:  (4.0, 7.0),
        Platform.TIKTOK:    (6.0, 12.0),
        Platform.YOUTUBE:   (8.0, 15.0),
    },
    "Micro": {
        Platform.TWITTER:   (2.5, 4.5),
        Platform.INSTAGRAM: (3.5, 6.5),
        Platform.FACEBOOK:  (2.5, 5.0),
        Platform.TIKTOK:    (4.5, 9.0),
        Platform.YOUTUBE:   (5.0, 10.0),
    },
    "Mid": {
        Platform.TWITTER:   (1.8, 3.2),
        Platform.INSTAGRAM: (2.5, 4.5),
        Platform.FACEBOOK:  (1.8, 3.5),
        Platform.TIKTOK:    (3.0, 6.0),
        Platform.YOUTUBE:   (3.0, 6.5),
    },
    "Macro": {
        Platform.TWITTER:   (1.2, 2.2),
        Platform.INSTAGRAM: (1.8, 3.2),
        Platform.FACEBOOK:  (1.2, 2.5),
        Platform.TIKTOK:    (2.0, 4.5),
        Platform.YOUTUBE:   (2.0, 4.5),
    },
    "Mega": {
        Platform.TWITTER:   (0.8, 1.5),
        Platform.INSTAGRAM: (1.2, 2.2),
        Platform.FACEBOOK:  (0.8, 1.8),
        Platform.TIKTOK:    (1.5, 3.0),
        Platform.YOUTUBE:   (1.2, 3.0),
    },
}

ESTRATO_UMBRALES_FOLLOWERS: list[tuple[str, int]] = [
    ("Nano", 10_000),
    ("Micro", 50_000),
    ("Mid", 250_000),
    ("Macro", 1_000_000),
    ("Mega", float("inf")),  # type: ignore[list-item]
]


def clasificar_estrato(max_followers: int) -> str:
    """Infer estrato from max followers across platforms.

    Used only when ``dirigente.estrato_politico`` is NULL (MASTER §3.1 #01
    validation note). Returns one of: Nano, Micro, Mid, Macro, Mega.
    """
    for label, upper in ESTRATO_UMBRALES_FOLLOWERS:
        if max_followers < upper:
            return label
    return "Mega"


def modificador_temporal(dias_a_comicio: int | None) -> float:
    """Apply MASTER §3.1 #01 D-19 temporal ramp (180d → 90d → 30d → veda).

    Args:
        dias_a_comicio: días faltantes a la próxima elección; ``None`` si el
            distrito no tiene ventana electoral activa.

    Returns:
        Multiplicador ER esperado. 1.0 = ciclo normal, hasta 2.5× en rampa
        fuerte 30-7d, 2.3× durante veda 7d (penalización INE).
    """
    if dias_a_comicio is None or dias_a_comicio < 0 or dias_a_comicio > 180:
        return 1.0

    if 90 < dias_a_comicio <= 180:
        return 1.0 + 0.5 * (1 - (dias_a_comicio - 90) / 90)

    if 30 < dias_a_comicio <= 90:
        return 1.5 + 1.0 * (1 - (dias_a_comicio - 30) / 60)

    if 7 < dias_a_comicio <= 30:
        return 2.5

    if 0 <= dias_a_comicio <= 7:
        return 2.3

    return 1.0


async def load_dirigente_scoped(
    db: AsyncSession,
    dirigente_id: int,
    org_id: int | None,
) -> Dirigente | None:
    """Load dirigente with optional org_id RLS check.

    Returns ``None`` when the dirigente doesn't exist or doesn't belong to
    the requested org. ``org_id=None`` is treated as "no tenant scoping"
    (admin global view).
    """
    stmt = select(Dirigente).where(Dirigente.id == dirigente_id)
    if org_id is not None:
        stmt = stmt.where(
            (Dirigente.org_id == org_id) | (Dirigente.org_id.is_(None))
        )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


def build_ok(bloque: str, data: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "ok",
        "data": data,
        "bloque": bloque,
        "bloque_version": "tier1-v1",
        "computed_at": datetime.now(UTC).isoformat(),
    }


def build_insufficient(
    bloque: str, missing: list[str], extra: dict[str, Any] | None = None
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "status": "insufficient_data",
        "missing": missing,
        "bloque": bloque,
        "bloque_version": "tier1-v1",
        "computed_at": datetime.now(UTC).isoformat(),
    }
    if extra:
        payload["data"] = extra
    return payload


def build_dirigente_not_found(bloque: str, dirigente_id: int) -> dict[str, Any]:
    return build_insufficient(
        bloque, missing=[f"dirigente_id={dirigente_id} no encontrado o fuera de org"]
    )
