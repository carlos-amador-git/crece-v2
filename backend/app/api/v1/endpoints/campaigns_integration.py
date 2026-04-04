from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_or_api_key
from app.models.ciudadano import Ciudadano
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.integration import (
    CampaignCreateRequest,
    CampaignResponse,
    CampaignSegmentRequest,
    CampaignSegmentResponse,
    CiudadanoSegmentado,
)

router = APIRouter()


@router.post("/segment", response_model=CampaignSegmentResponse)
async def segment_ciudadanos(
    payload: CampaignSegmentRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user_or_api_key)],
) -> CampaignSegmentResponse:
    """Segment ciudadanos by multiple criteria for campaign targeting.

    Always filters by org_id and excludes ciudadanos without telefono.
    """
    query = select(Ciudadano).where(
        Ciudadano.org_id == current_user.org_id,
        Ciudadano.telefono.is_not(None),
        Ciudadano.telefono != "",
    )

    # Dynamic WHERE clauses
    if payload.secciones:
        query = query.where(Ciudadano.seccion_id.in_(payload.secciones))

    if payload.intencion_voto:
        query = query.where(Ciudadano.intencion_voto.in_(payload.intencion_voto))

    if payload.rango_edad:
        query = query.where(Ciudadano.edad_rango.in_(payload.rango_edad))

    if payload.genero:
        query = query.where(Ciudadano.genero.in_(payload.genero))

    if payload.programa_social:
        # JSONB contains check — programas_sociales is a JSONB column
        query = query.where(
            Ciudadano.programas_sociales.op("?")(payload.programa_social)
        )

    if payload.excluir_contactados_dias:
        # Exclude ciudadanos with recent CRM interactions
        try:
            from app.models.crm_interaccion import CrmInteraccion

            cutoff = datetime.now(UTC) - timedelta(days=payload.excluir_contactados_dias)
            recently_contacted = (
                select(CrmInteraccion.ciudadano_id)
                .where(CrmInteraccion.created_at >= cutoff)
                .distinct()
            )
            query = query.where(Ciudadano.id.not_in(recently_contacted))
        except ImportError:
            pass  # CrmInteraccion model not available yet

    # Count total matching
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Apply limit
    query = query.limit(payload.limit)
    result = await db.execute(query)
    ciudadanos = list(result.scalars().all())

    return CampaignSegmentResponse(
        total=total,
        ciudadanos=[
            CiudadanoSegmentado(
                id=c.id,
                nombre=c.nombre,
                apellido_paterno=c.apellido_paterno,
                telefono=c.telefono,  # type: ignore[arg-type]
                colonia=c.colonia,
                seccion_id=c.seccion_id,
                intencion_voto=c.intencion_voto.value if c.intencion_voto else None,
            )
            for c in ciudadanos
        ],
    )


@router.post("/", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    payload: CampaignCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user_or_api_key)],
) -> CampaignResponse:
    """Create a new campaign."""
    from app.models.campaign_integration import Campaign

    campaign = Campaign(
        nombre=payload.nombre,
        tipo=payload.tipo,
        segmentacion=payload.segmentacion,
        tipo_nudge=payload.tipo_nudge,
        programado_para=payload.programado_para,
        estado="borrador",
        total_destinatarios=0,
        enviados=0,
        entregados=0,
        leidos=0,
        respondidos=0,
        creado_por_id=current_user.id,
        org_id=current_user.org_id,
    )
    db.add(campaign)
    await db.flush()
    await db.refresh(campaign)

    return CampaignResponse(
        id=str(campaign.id),
        nombre=campaign.nombre,
        tipo=campaign.tipo,
        segmentacion=campaign.segmentacion or {},
        tipo_nudge=campaign.tipo_nudge,
        total_destinatarios=campaign.total_destinatarios,
        enviados=campaign.enviados,
        entregados=campaign.entregados,
        leidos=campaign.leidos,
        respondidos=campaign.respondidos,
        estado=campaign.estado,
        created_at=campaign.created_at,
    )


@router.get("/", response_model=PaginatedResponse[CampaignResponse])
async def list_campaigns(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user_or_api_key)],
    estado: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[CampaignResponse]:
    """List campaigns filtered by org_id and optional estado."""
    from app.models.campaign_integration import Campaign

    query = select(Campaign).where(Campaign.org_id == current_user.org_id)
    count_query = select(func.count(Campaign.id)).where(
        Campaign.org_id == current_user.org_id
    )

    if estado:
        query = query.where(Campaign.estado == estado)
        count_query = count_query.where(Campaign.estado == estado)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = (
        query.order_by(Campaign.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    items = list(result.scalars().all())

    return PaginatedResponse(
        items=[CampaignResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if total > 0 else 0,
    )


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user_or_api_key)],
) -> CampaignResponse:
    """Get a single campaign by UUID."""
    from uuid import UUID

    from app.models.campaign_integration import Campaign

    try:
        uuid_val = UUID(campaign_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid campaign ID format",
        )

    result = await db.execute(
        select(Campaign).where(
            Campaign.id == uuid_val,
            Campaign.org_id == current_user.org_id,
        )
    )
    campaign = result.scalar_one_or_none()
    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found"
        )

    return CampaignResponse.model_validate(campaign)
