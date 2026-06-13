"""Handoff automatizado RADAR→CRECE (PLAN-2026-06-11-auto-radar-crece).

RADAR sube el bundle delta a MinIO y POSTea aquí SOLO el manifest (vía n8n).
La cadena pesada corre en Celery (app/workers/ingest_tasks.py).
Auth: X-API-Key (api_keys) o JWT — requiere rol ADMIN (service-to-service).
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import Role, RoleChecker
from app.models.dirigente import Dirigente
from app.models.ingest_job import IngestJob, IngestJobStatus
from app.schemas.ingest import IngestJobResponse, RadarManifest, WatermarkResponse
from app.services.radar_ingest import get_watermark

router = APIRouter()

require_admin = RoleChecker([Role.ADMIN])
require_admin_or_analyst = RoleChecker([Role.ADMIN, Role.ANALYST])

# Backpressure (Gemini Q4): si hay más de N jobs encolados/corriendo → 503.
_MAX_JOBS_IN_FLIGHT = 4


@router.get("/watermark/{dirigente_id}", response_model=WatermarkResponse)
async def watermark(
    dirigente_id: int,
    current_user: Annotated[Any, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """Último timestamp ingerido por plataforma. RADAR exporta solo lo posterior."""
    dirigente = await db.get(Dirigente, dirigente_id)
    if dirigente is None:
        raise HTTPException(status_code=404, detail=f"dirigente {dirigente_id} no existe")
    return await get_watermark(db, dirigente_id)


@router.post(
    "/radar-handoff",
    response_model=IngestJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def radar_handoff(
    manifest: RadarManifest,
    current_user: Annotated[Any, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """Recibe el manifest de un handoff y encola el ingest.

    Idempotente por task_uuid: re-push del mismo uuid devuelve el job
    existente sin re-procesar (202).
    """
    dirigente = await db.get(Dirigente, manifest.dirigente_id)
    if dirigente is None:
        raise HTTPException(
            status_code=422, detail=f"dirigente {manifest.dirigente_id} no existe"
        )

    # Idempotencia de transporte (task_uuid único)
    existing = (
        await db.execute(select(IngestJob).where(IngestJob.task_uuid == manifest.task_uuid))
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    # Backpressure: con la cola saturada, 503 → n8n reintenta con backoff
    in_flight = (
        await db.execute(
            select(IngestJob).where(
                IngestJob.status.in_([IngestJobStatus.RECEIVED, IngestJobStatus.RUNNING])
            )
        )
    ).scalars().all()
    if len(in_flight) >= _MAX_JOBS_IN_FLIGHT:
        raise HTTPException(
            status_code=503,
            detail=f"{len(in_flight)} jobs en curso; reintentar después",
            headers={"Retry-After": "300"},
        )

    job = IngestJob(
        task_uuid=manifest.task_uuid,
        schema_version=manifest.schema_version,
        slug=manifest.slug,
        dirigente_id=manifest.dirigente_id,
        manifest=manifest.model_dump(mode="json", by_alias=True),
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    from app.workers.ingest_tasks import process_radar_handoff

    process_radar_handoff.delay(job.id)
    return job


@router.post("/sync/{dirigente_id}", response_model=IngestJobResponse | dict)
async def sync_trigger(
    dirigente_id: int,
    current_user: Annotated[Any, Depends(require_admin_or_analyst)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """Localiza el último bundle en MinIO y dispara ingesta si es nuevo o fallido."""
    from app.services.radar_sync import (
        discover_manifest,
        find_latest_bundle_info,
        get_dirigente_slug,
    )

    slug = await get_dirigente_slug(db, dirigente_id)
    info = await find_latest_bundle_info(slug)

    if not info:
        return {"sin_novedades": True, "reason": "No se encontraron bundles en MinIO"}

    task_uuid = info["task_uuid"]
    existing = (
        await db.execute(select(IngestJob).where(IngestJob.task_uuid == task_uuid))
    ).scalar_one_or_none()

    if existing and existing.status in (IngestJobStatus.COMPLETED, IngestJobStatus.PARTIAL):
        return {"sin_novedades": True, "task_uuid": task_uuid}

    if existing:
        # Re-encolar si no está en curso
        if existing.status in (
            IngestJobStatus.FAILED,
            IngestJobStatus.TAINTED,
            IngestJobStatus.RECEIVED,
        ):
            from app.workers.ingest_tasks import process_radar_handoff

            process_radar_handoff.delay(existing.id)
            return existing
        return existing

    # Discovery: crear job para bundle encontrado sin manifest previo
    manifest_dict = await discover_manifest(slug, task_uuid, dirigente_id)
    job = IngestJob(
        task_uuid=task_uuid,
        schema_version=manifest_dict["schema_version"],
        slug=slug,
        dirigente_id=dirigente_id,
        manifest=manifest_dict,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    from app.workers.ingest_tasks import process_radar_handoff

    process_radar_handoff.delay(job.id)
    return job


@router.get("/sync/status/{dirigente_id}", response_model=IngestJobResponse)
async def sync_status(
    dirigente_id: int,
    current_user: Annotated[Any, Depends(require_admin_or_analyst)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """Estado del proceso de sincronización más reciente para el dirigente."""
    job = (
        await db.execute(
            select(IngestJob)
            .where(IngestJob.dirigente_id == dirigente_id)
            .order_by(desc(IngestJob.created_at))
            .limit(1)
        )
    ).scalar_one_or_none()

    if job is None:
        raise HTTPException(
            status_code=404, detail="No hay procesos de sincronización para este dirigente"
        )
    return job


@router.get("/jobs/{job_id}", response_model=IngestJobResponse)
async def job_status(
    job_id: int,
    current_user: Annotated[Any, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """Status consultable del job (RADAR, n8n, humano)."""
    job = await db.get(IngestJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"job {job_id} no existe")
    return job
