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
# Rangos (p25, p75) pre-modificador temporal. Unidades: porcentaje puntos.
# Fuente: bundle Zenodo v1 (backend/data/zenodo/v1/benchmarks_er_politicos_mx_v1.csv).
# Cells 🟢 VALIDATED = n≥30 posts, IC95 calculable, ≥2 dirigentes distintos.
# Cells 🟡 TBD = no hay data empírica todavía — valores extrapolados conservadoramente
# desde Nano/Micro con factor 0.5× por estrato (ver methodology.md §7).
MATRIZ_ER_5x5: dict[str, dict[Platform, tuple[float, float]]] = {
    "Nano": {
        # 🟢 VALIDATED (Zenodo v1 · p25-p75)
        Platform.TWITTER:   (0.013, 0.213),
        Platform.INSTAGRAM: (0.296, 1.134),
        Platform.FACEBOOK:  (0.094, 0.611),
        Platform.TIKTOK:    (0.318, 1.070),
        # 🟡 TBD (Zenodo n=0) · extrapolado desde TikTok Nano × 1.3
        Platform.YOUTUBE:   (0.400, 1.400),
    },
    "Micro": {
        # 🟢 VALIDATED (Zenodo v1 · p25-p75)
        Platform.TWITTER:   (0.051, 0.158),
        Platform.INSTAGRAM: (0.178, 0.501),
        Platform.FACEBOOK:  (0.023, 0.174),
        Platform.TIKTOK:    (0.593, 1.896),
        # 🟡 TBD (Zenodo n=10, todos ceros) · extrapolado
        Platform.YOUTUBE:   (0.600, 2.000),
    },
    # 🟡 TBD · extrapolado conservadoramente (sin data Zenodo v1)
    # Factor ~0.5× Micro por estrato (patrón decay audiencia↑ → ER↓)
    "Mid": {
        Platform.TWITTER:   (0.025, 0.080),
        Platform.INSTAGRAM: (0.090, 0.250),
        Platform.FACEBOOK:  (0.012, 0.087),
        Platform.TIKTOK:    (0.300, 0.950),
        Platform.YOUTUBE:   (0.300, 1.000),
    },
    "Macro": {
        Platform.TWITTER:   (0.013, 0.040),
        Platform.INSTAGRAM: (0.045, 0.125),
        Platform.FACEBOOK:  (0.006, 0.044),
        Platform.TIKTOK:    (0.150, 0.475),
        Platform.YOUTUBE:   (0.150, 0.500),
    },
    "Mega": {
        Platform.TWITTER:   (0.007, 0.020),
        Platform.INSTAGRAM: (0.023, 0.063),
        Platform.FACEBOOK:  (0.003, 0.022),
        Platform.TIKTOK:    (0.075, 0.238),
        Platform.YOUTUBE:   (0.075, 0.250),
    },
}

# Celdas con data empírica Zenodo v1 validada (n≥30, IC95, ≥2 dirigentes).
# El resto son TBD · extrapolación conservadora hasta bundle v2+.
ZENODO_VALIDATED_CELLS: set[tuple[str, Platform]] = {
    ("Nano", Platform.TWITTER),
    ("Nano", Platform.INSTAGRAM),
    ("Nano", Platform.FACEBOOK),
    ("Nano", Platform.TIKTOK),
    ("Micro", Platform.TWITTER),
    ("Micro", Platform.INSTAGRAM),
    ("Micro", Platform.FACEBOOK),
    ("Micro", Platform.TIKTOK),
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
