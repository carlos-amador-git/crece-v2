from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import Role, RoleChecker, get_current_user
from app.models.campana import Campana, CampanaMensaje, EstadoCampana, EstadoMensaje
from app.models.user import User
from app.schemas.campana import (
    CampanaAnalytics,
    CampanaCreate,
    CampanaPreviewResponse,
    CampanaResponse,
    CampanaSegmentoCreate,
    CampanaSegmentoResponse,
    CampanaUpdate,
    DeliveryWebhookPayload,
)
from app.schemas.common import MessageResponse, PaginatedResponse
from app.services.campaign_manager import CampaignManager

logger = logging.getLogger(__name__)

router = APIRouter()


# ── List campaigns (paginated) ───────────────────────────


@router.get("/", response_model=PaginatedResponse[CampanaResponse])
async def list_campanas(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    estado: EstadoCampana | None = None,
    org_id: int | None = None,
    search: str | None = None,
) -> PaginatedResponse[CampanaResponse]:
    """List campaigns with optional filtering and pagination."""
    query = select(Campana)
    count_query = select(func.count(Campana.id))

    if estado is not None:
        query = query.where(Campana.estado == estado)
        count_query = count_query.where(Campana.estado == estado)
    if org_id is not None:
        query = query.where(Campana.org_id == org_id)
        count_query = count_query.where(Campana.org_id == org_id)
    if search:
        pattern = f"%{search}%"
        search_filter = Campana.nombre.ilike(pattern)
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = (
        query.order_by(Campana.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    result = await db.execute(query)
    items = list(result.scalars().all())

    return PaginatedResponse(
        items=[CampanaResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if total > 0 else 0,
    )


# ── Create campaign ──────────────────────────────────────


@router.post(
    "/",
    response_model=CampanaResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST]))],
)
async def create_campana(
    payload: CampanaCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Campana:
    """Create a new WhatsApp campaign. Requires admin or analyst role."""
    campana = Campana(
        **payload.model_dump(),
        creado_por_id=current_user.id,
        estado=EstadoCampana.BORRADOR,
    )
    db.add(campana)
    await db.flush()
    await db.refresh(campana)
    return campana


# ── Get campaign detail ──────────────────────────────────


@router.get("/{campana_id}", response_model=CampanaResponse)
async def get_campana(
    campana_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
) -> Campana:
    """Get campaign detail including segments."""
    result = await db.execute(select(Campana).where(Campana.id == campana_id))
    campana = result.scalar_one_or_none()
    if campana is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return campana


# ── Update campaign ──────────────────────────────────────


@router.patch(
    "/{campana_id}",
    response_model=CampanaResponse,
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST]))],
)
async def update_campana(
    campana_id: int,
    payload: CampanaUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Campana:
    """Update a campaign. Only BORRADOR campaigns can be fully edited."""
    result = await db.execute(select(Campana).where(Campana.id == campana_id))
    campana = result.scalar_one_or_none()
    if campana is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

    if campana.estado not in (EstadoCampana.BORRADOR, EstadoCampana.PROGRAMADA):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot update campaign in state: {campana.estado}",
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(campana, field, value)

    await db.flush()
    await db.refresh(campana)
    return campana


# ── Add segment filter ───────────────────────────────────


@router.post(
    "/{campana_id}/segmentos",
    response_model=CampanaSegmentoResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST]))],
)
async def add_segmento(
    campana_id: int,
    payload: CampanaSegmentoCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Add a segment filter to a campaign and return the matching count."""
    result = await db.execute(select(Campana).where(Campana.id == campana_id))
    campana = result.scalar_one_or_none()
    if campana is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

    if campana.estado != EstadoCampana.BORRADOR:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Segments can only be added to campaigns in BORRADOR state",
        )

    await CampaignManager.build_segment(db, campana_id, payload)

    # Return the last inserted segment
    from sqlalchemy import desc

    from app.models.campana import CampanaSegmento

    seg_result = await db.execute(
        select(CampanaSegmento)
        .where(CampanaSegmento.campana_id == campana_id)
        .order_by(desc(CampanaSegmento.id))
        .limit(1)
    )
    segmento = seg_result.scalar_one()
    return CampanaSegmentoResponse.model_validate(segmento)


# ── Prepare campaign (resolve citizens) ──────────────────


@router.post(
    "/{campana_id}/preparar",
    response_model=CampanaPreviewResponse,
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST]))],
)
async def preparar_campana(
    campana_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CampanaPreviewResponse:
    """Resolve segment filters into message records.

    Creates a CampanaMensaje for each matching ciudadano with a phone number.
    Returns a preview with sample messages.
    """
    try:
        total = await CampaignManager.prepare_campaign(db, campana_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    # Fetch a sample of prepared messages
    sample_result = await db.execute(
        select(CampanaMensaje).where(CampanaMensaje.campana_id == campana_id).limit(5)
    )
    sample_msgs = list(sample_result.scalars().all())

    campana = await db.get(Campana, campana_id)

    return CampanaPreviewResponse(
        campana_id=campana_id,
        total_destinatarios=total,
        sample_mensajes=[
            {
                "ciudadano_id": m.ciudadano_id,
                "telefono": m.telefono,
                "mensaje": campana.plantilla_mensaje if campana else "",
            }
            for m in sample_msgs
        ],
    )


# ── Send campaign (mark as sending) ─────────────────────


@router.post(
    "/{campana_id}/enviar",
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST]))],
)
async def enviar_campana(
    campana_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Mark campaign as sending and return the payload for Chatwoot-MX.

    This endpoint does NOT deliver messages directly. It:
    1. Changes campaign state to ENVIANDO
    2. Returns the payload that Chatwoot-MX will consume via its webhook

    Actual WhatsApp delivery is handled entirely by Chatwoot-MX.
    """
    result = await db.execute(select(Campana).where(Campana.id == campana_id))
    campana = result.scalar_one_or_none()
    if campana is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

    if campana.estado != EstadoCampana.PROGRAMADA:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Campaign must be PROGRAMADA to send, current: {campana.estado}",
        )

    # Check that there are pending messages
    pending_count = await db.execute(
        select(func.count(CampanaMensaje.id)).where(
            CampanaMensaje.campana_id == campana_id,
            CampanaMensaje.estado == EstadoMensaje.PENDIENTE,
        )
    )
    pending = pending_count.scalar_one()
    if pending == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No pending messages to send. Run /preparar first.",
        )

    # Transition state
    campana.estado = EstadoCampana.ENVIANDO
    campana.fecha_envio = datetime.now(UTC)
    await db.flush()

    # Build payload for Chatwoot-MX
    payload = await CampaignManager.get_campaign_payload(db, campana_id)

    # Trigger n8n webhook if configured (D.1 — campaign dispatch via n8n)
    n8n_execution_id = None
    if settings.N8N_CAMPAIGN_WEBHOOK_URL:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    settings.N8N_CAMPAIGN_WEBHOOK_URL,
                    json={
                        "campana_id": campana_id,
                        "total_mensajes": len(payload),
                        "payload": payload,
                    },
                    headers={"X-CRECE-Token": settings.N8N_CRECE_TOKEN},
                )
                if resp.status_code < 300:
                    resp_data = (
                        resp.json()
                        if resp.headers.get("content-type", "").startswith("application/json")
                        else {}
                    )
                    n8n_execution_id = resp_data.get("executionId")
                    logger.info(
                        "n8n campaign webhook triggered: campana=%d, execution=%s",
                        campana_id,
                        n8n_execution_id,
                    )
                else:
                    logger.warning(
                        "n8n webhook returned %d for campana %d",
                        resp.status_code,
                        campana_id,
                    )
        except httpx.HTTPError as exc:
            logger.error("n8n webhook failed for campana %d: %s", campana_id, exc)

    return {
        "campana_id": campana_id,
        "estado": EstadoCampana.ENVIANDO,
        "total_mensajes": len(payload),
        "n8n_execution_id": n8n_execution_id,
        "payload": payload,
    }


# ── Campaign analytics ───────────────────────────────────


@router.get("/{campana_id}/analytics", response_model=CampanaAnalytics)
async def get_analytics(
    campana_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
) -> CampanaAnalytics:
    """Get delivery funnel analytics for a campaign."""
    try:
        analytics = await CampaignManager.get_campaign_analytics(db, campana_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    return CampanaAnalytics(**analytics)


# ── Chatwoot-MX delivery webhook ─────────────────────────


@router.post("/webhook/delivery", response_model=MessageResponse)
async def webhook_delivery(
    payload: DeliveryWebhookPayload,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    """Receive delivery status updates from Chatwoot-MX.

    This endpoint is called by Chatwoot-MX whenever a WhatsApp message
    status changes (sent, delivered, read, replied, failed).

    NOTE: This endpoint intentionally has no auth dependency because
    Chatwoot-MX calls it as a webhook. In production, validate the
    webhook signature via a shared secret (configured in Settings).
    """
    try:
        await CampaignManager.update_delivery_status(
            db=db,
            mensaje_id=payload.mensaje_id,
            status=payload.status,
            chatwoot_id=payload.chatwoot_message_id,
            error=payload.error,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e

    # Check if all messages have been processed, mark campaign as completed
    mensaje = await db.get(CampanaMensaje, payload.mensaje_id)
    if mensaje:
        pending_result = await db.execute(
            select(func.count(CampanaMensaje.id)).where(
                CampanaMensaje.campana_id == mensaje.campana_id,
                CampanaMensaje.estado == EstadoMensaje.PENDIENTE,
            )
        )
        pending = pending_result.scalar_one()
        if pending == 0:
            campana = await db.get(Campana, mensaje.campana_id)
            if campana and campana.estado == EstadoCampana.ENVIANDO:
                campana.estado = EstadoCampana.COMPLETADA
                campana.fecha_completada = datetime.now(UTC)

    return MessageResponse(message="Delivery status updated")


# ── Delete / cancel campaign ─────────────────────────────


@router.delete(
    "/{campana_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RoleChecker([Role.ADMIN]))],
)
async def delete_campana(
    campana_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Cancel and delete a campaign. Admin only.

    If the campaign is in ENVIANDO state, it is cancelled instead of deleted
    to preserve delivery records.
    """
    result = await db.execute(select(Campana).where(Campana.id == campana_id))
    campana = result.scalar_one_or_none()
    if campana is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

    if campana.estado == EstadoCampana.ENVIANDO:
        # Cancel rather than delete to preserve delivery audit trail
        campana.estado = EstadoCampana.CANCELADA
        await db.flush()
        return

    await db.delete(campana)
