"""Diagnóstico Tier 2 endpoints (Sprint S3 · MASTER §3.2 #11-#18).

8 bloques diferenciadores defensibles + 1 endpoint agregado.

El endpoint agregado soporta ``?recompute_tier1=true`` que correlaciona con
servicios Tier 1 pasando la lista de ``author_hash`` CIB a excluir — demo del
valor de Filtro de Realidad.

Auth JWT + org_id scoping idéntico a ``diagnostico.py`` Tier 1.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.diagnostico_tier2 import (
    cib_detector_service,
    cross_partisan_service,
    filtro_realidad_service,
    promesas_service,
    rage_click_service,
    topic_drift_service,
    veda_compliance_service,
    violencia_politica_service,
)

router = APIRouter()


def _resolve_org_id(current_user: User, request: Request) -> int | None:
    """Admin puede sobrescribir org_id con header X-Org-Id (igual tier1)."""
    org_id = getattr(current_user, "org_id", None)
    if current_user.role == "admin":
        override = request.headers.get("x-org-id")
        if override and override.isdigit():
            return int(override)
    return org_id


@router.get("/{dirigente_id}/cross_partisan")
async def get_cross_partisan(
    dirigente_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """B11 Cross-Partisan Validation Score."""
    org_id = _resolve_org_id(current_user, request)
    return await cross_partisan_service.compute(db, dirigente_id, org_id)


@router.get("/{dirigente_id}/cib_detector")
async def get_cib_detector(
    dirigente_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """B12 CIB Detector multinivel (ITESO/DFRLab)."""
    org_id = _resolve_org_id(current_user, request)
    return await cib_detector_service.compute(db, dirigente_id, org_id)


@router.get("/{dirigente_id}/filtro_realidad")
async def get_filtro_realidad(
    dirigente_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """B13 Filtro de Realidad (ER orgánico sin CIB)."""
    org_id = _resolve_org_id(current_user, request)
    return await filtro_realidad_service.compute(db, dirigente_id, org_id)


@router.get("/{dirigente_id}/topic_drift")
async def get_topic_drift(
    dirigente_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """B14 Topic Drift Detector (caption vs comments)."""
    org_id = _resolve_org_id(current_user, request)
    return await topic_drift_service.compute(db, dirigente_id, org_id)


@router.get("/{dirigente_id}/rage_click")
async def get_rage_click(
    dirigente_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """B15 Rage Click Flag (outrage engagement)."""
    org_id = _resolve_org_id(current_user, request)
    return await rage_click_service.compute(db, dirigente_id, org_id)


@router.get("/{dirigente_id}/promesas")
async def get_promesas(
    dirigente_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """B16 Rastreador Promesas de Campaña."""
    org_id = _resolve_org_id(current_user, request)
    return await promesas_service.compute(db, dirigente_id, org_id)


@router.get("/{dirigente_id}/veda_compliance")
async def get_veda_compliance(
    dirigente_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    en_veda: bool = Query(False, description="Flag externo ventana veda INE activa"),
) -> dict:
    """B17 Veda INE Compliance."""
    org_id = _resolve_org_id(current_user, request)
    return await veda_compliance_service.compute(db, dirigente_id, org_id, en_veda=en_veda)


@router.get("/{dirigente_id}/violencia_politica")
async def get_violencia_politica(
    dirigente_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """B18 Escaneo Violencia Política."""
    org_id = _resolve_org_id(current_user, request)
    return await violencia_politica_service.compute(db, dirigente_id, org_id)


@router.get("/{dirigente_id}")
async def get_diagnostico_tier2_completo(
    dirigente_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    recompute_tier1: bool = Query(
        False,
        description=(
            "Si True, recalcula servicios Tier 1 (B01 ER en particular) "
            "excluyendo comments de authors CIB — demo del valor del Filtro de Realidad."
        ),
    ),
    en_veda: bool = Query(False, description="Flag ventana veda INE para B17"),
) -> dict:
    """Endpoint agregado — 8 bloques Tier 2 + opcional recompute Tier 1 filtrado."""
    org_id = _resolve_org_id(current_user, request)

    # Ejecutar B12 primero (varios bloques dependen de sus flagged_hashes)
    cib_result = await cib_detector_service.compute(db, dirigente_id, org_id)
    filtro = await filtro_realidad_service.compute(
        db, dirigente_id, org_id, cib_result=cib_result
    )

    bloques = {
        "B11_cross_partisan": await cross_partisan_service.compute(db, dirigente_id, org_id),
        "B12_cib_detector": cib_result,
        "B13_filtro_realidad": filtro,
        "B14_topic_drift": await topic_drift_service.compute(db, dirigente_id, org_id),
        "B15_rage_click": await rage_click_service.compute(db, dirigente_id, org_id),
        "B16_promesas": await promesas_service.compute(db, dirigente_id, org_id),
        "B17_veda_compliance": await veda_compliance_service.compute(
            db, dirigente_id, org_id, en_veda=en_veda
        ),
        "B18_violencia_politica": await violencia_politica_service.compute(
            db, dirigente_id, org_id
        ),
    }

    tier1_recomputed: dict | None = None
    if recompute_tier1 and filtro.get("status") == "ok":
        # Recompute B01 ER — demo del valor del Filtro de Realidad
        # (otros bloques tier1 que usan comments también podrían reprocesarse,
        #  pero B01 es el KPI headline del dashboard)
        from app.services.diagnostico import er_service

        er_baseline = await er_service.compute(db, dirigente_id, org_id)
        flagged_hashes = filtro["data"].get("flagged_hashes_para_exclusion", [])
        tier1_recomputed = {
            "er_tier1_baseline": er_baseline,
            "cib_hashes_excluidos": flagged_hashes,
            "note": (
                "B01 ER se computa sobre social_posts (no comments); el filtro "
                "afecta primariamente métricas basadas en comments — ver "
                "delta_comments_cib en B13. Recompute real de B01 requiere "
                "desacoplar engagement por author_hash (Sprint S4+)."
            ),
        }

    ok_count = sum(1 for v in bloques.values() if v.get("status") == "ok")
    insufficient_count = sum(
        1 for v in bloques.values() if v.get("status") == "insufficient_data"
    )

    return {
        "dirigente_id": dirigente_id,
        "bloques": bloques,
        "tier1_recomputed": tier1_recomputed,
        "resumen": {
            "ok": ok_count,
            "insufficient_data": insufficient_count,
            "total": len(bloques),
        },
        "bloque_version": "tier2-v1",
    }
