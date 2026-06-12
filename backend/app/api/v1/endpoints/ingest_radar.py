"""Handoff automatizado RADAR→CRECE (PLAN-2026-06-11-auto-radar-crece).

RADAR sube el bundle delta a MinIO y POSTea aquí SOLO el manifest (vía n8n).
La cadena pesada corre en Celery (app/workers/ingest_tasks.py).
Auth: X-API-Key (api_keys) o JWT — requiere rol ADMIN (service-to-service).
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import Role, RoleChecker
from app.models.dirigente import Dirigente
from app.models.ingest_job import IngestJob, IngestJobStatus
from app.schemas.ingest import IngestJobResponse, RadarManifest, WatermarkResponse
from app.services.radar_ingest import get_watermark

router = APIRouter()

require_admin = RoleChecker([Role.ADMIN])

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
