"""Diagnóstico Tier 1 endpoints (Sprint S2 · MASTER §3.1 #01-#10).

Cada bloque expone un GET individual + un endpoint agregado que regresa los 10
en una sola llamada para consumo del dashboard de diagnóstico.

Auth: JWT obligatoria. ``org_id`` se extrae del user del JWT (admin puede
sobrescribir con header ``X-Org-Id``). No-admins solo ven dirigentes de su org.
"""
from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.diagnostico import (
    benchmark_service,
    breakout_service,
    crisis_spike_service,
    er_service,
    growth_attribution_service,
    humanizacion_service,
    matrix_2x2_service,
    sentiment_plutchik_service,
    share_like_ratio_service,
    sov_service,
)

router = APIRouter()


def _resolve_org_id(current_user: User, request: Request) -> int | None:
    """Return effective org_id. Admin can override via X-Org-Id header."""
    org_id = getattr(current_user, "org_id", None)
    if current_user.role == "admin":
        override = request.headers.get("x-org-id")
        if override and override.isdigit():
            return int(override)
    return org_id


@router.get("/{dirigente_id}/er_normalizado")
async def get_er_normalizado(
    dirigente_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    dias_a_comicio: int | None = Query(None, ge=0, description="Días a próxima elección (activa modificador temporal D-19)"),
) -> dict:
    """B01 ER normalizado por estrato (matriz 5×5 + modificador temporal D-19)."""
    org_id = _resolve_org_id(current_user, request)
    return await er_service.compute(db, dirigente_id, org_id, dias_a_comicio=dias_a_comicio)


@router.get("/{dirigente_id}/breakout_scale")
async def get_breakout_scale(
    dirigente_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """B02 Breakout Scale Brookings (Cat 1-6)."""
    org_id = _resolve_org_id(current_user, request)
    return await breakout_service.compute(db, dirigente_id, org_id)


@router.get("/{dirigente_id}/matriz_2x2")
async def get_matriz_2x2(
    dirigente_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """B03 Matriz 2×2 de contenido (Insignia/Crisis/Vanidad/Muerta)."""
    org_id = _resolve_org_id(current_user, request)
    return await matrix_2x2_service.compute(db, dirigente_id, org_id)


@router.get("/{dirigente_id}/benchmark")
async def get_benchmark(
    dirigente_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """B04 Benchmark vs competidores directos (proxies D-22 en S2)."""
    org_id = _resolve_org_id(current_user, request)
    return await benchmark_service.compute(db, dirigente_id, org_id)


@router.get("/{dirigente_id}/sentiment_plutchik")
async def get_sentiment_plutchik(
    dirigente_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """B05 Sentiment Plutchik 6 emociones."""
    org_id = _resolve_org_id(current_user, request)
    return await sentiment_plutchik_service.compute(db, dirigente_id, org_id)


@router.get("/{dirigente_id}/crisis_spike")
async def get_crisis_spike(
    dirigente_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """B06 Crisis Spike detector (ventana móvil 2h vs baseline 7d)."""
    org_id = _resolve_org_id(current_user, request)
    return await crisis_spike_service.compute(db, dirigente_id, org_id)


@router.get("/{dirigente_id}/growth_attribution")
async def get_growth_attribution(
    dirigente_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """B07 Growth attribution Time-Decay (half-life 7d · ventana 14d)."""
    org_id = _resolve_org_id(current_user, request)
    return await growth_attribution_service.compute(db, dirigente_id, org_id)


@router.get("/{dirigente_id}/sov")
async def get_sov(
    dirigente_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    topics: Annotated[list[str] | None, Query()] = None,
) -> dict:
    """B08 Share of Voice por tema clave (topics opcionales como filtro)."""
    org_id = _resolve_org_id(current_user, request)
    return await sov_service.compute(db, dirigente_id, org_id, topics=topics)


@router.get("/{dirigente_id}/share_like_ratio")
async def get_share_like_ratio(
    dirigente_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """B09 Share-to-Like Ratio (movilización profunda)."""
    org_id = _resolve_org_id(current_user, request)
    return await share_like_ratio_service.compute(db, dirigente_id, org_id)


@router.get("/{dirigente_id}/humanizacion")
async def get_humanizacion(
    dirigente_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """B10 Humanización Score (léxica 0-100)."""
    org_id = _resolve_org_id(current_user, request)
    return await humanizacion_service.compute(db, dirigente_id, org_id)


@router.get("/{dirigente_id}")
async def get_diagnostico_completo(
    dirigente_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    dias_a_comicio: int | None = Query(None, ge=0),
) -> dict:
    """Endpoint agregado — devuelve los 10 bloques Tier 1 en 1 request.

    Ejecuta los 10 services en paralelo usando ``asyncio.gather`` sobre sesiones
    independientes NO, por simplicidad S2 se ejecutan secuencialmente sobre la
    misma session (cada service es I/O bound con la misma DB).
    """
    org_id = _resolve_org_id(current_user, request)

    # Secuencial — los services comparten session y son cortos. Evita contention DB.
    bloques = {
        "B01_er_normalizado": await er_service.compute(db, dirigente_id, org_id, dias_a_comicio=dias_a_comicio),
        "B02_breakout_scale": await breakout_service.compute(db, dirigente_id, org_id),
        "B03_matriz_2x2": await matrix_2x2_service.compute(db, dirigente_id, org_id),
        "B04_benchmark": await benchmark_service.compute(db, dirigente_id, org_id),
        "B05_sentiment_plutchik": await sentiment_plutchik_service.compute(db, dirigente_id, org_id),
        "B06_crisis_spike": await crisis_spike_service.compute(db, dirigente_id, org_id),
        "B07_growth_attribution": await growth_attribution_service.compute(db, dirigente_id, org_id),
        "B08_sov": await sov_service.compute(db, dirigente_id, org_id),
        "B09_share_like_ratio": await share_like_ratio_service.compute(db, dirigente_id, org_id),
        "B10_humanizacion": await humanizacion_service.compute(db, dirigente_id, org_id),
    }

    ok_count = sum(1 for v in bloques.values() if v.get("status") == "ok")
    insufficient_count = sum(1 for v in bloques.values() if v.get("status") == "insufficient_data")

    return {
        "dirigente_id": dirigente_id,
        "bloques": bloques,
        "resumen": {
            "ok": ok_count,
            "insufficient_data": insufficient_count,
            "total": len(bloques),
        },
        "bloque_version": "tier1-v1",
    }
