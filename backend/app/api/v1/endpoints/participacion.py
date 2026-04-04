from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import Role, RoleChecker, get_current_user
from app.models.solicitud import (
    CanalOrigen,
    EstadoSolicitud,
    SolicitudCiudadana,
    TipoSolicitud,
)
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.solicitud import (
    ChatwootWebhookPayload,
    HeatmapPoint,
    ParticipacionDashboardStats,
    SeguimientoResponse,
    SolicitudAssign,
    SolicitudCreate,
    SolicitudListItem,
    SolicitudRespond,
    SolicitudResponse,
    SolicitudUpdate,
)
from app.services.participacion import ParticipacionService

logger = logging.getLogger(__name__)

router = APIRouter()


def _build_geometry_wkt(lat: float | None, lon: float | None) -> str | None:
    """Build a WKT POINT string from lat/lon, or return None."""
    if lat is not None and lon is not None:
        return f"SRID=4326;POINT({lon} {lat})"
    return None


def _build_seguimiento_response(seguimiento: object) -> SeguimientoResponse:
    """Build a SeguimientoResponse with usuario_nombre resolved."""
    usuario_nombre = None
    if hasattr(seguimiento, "usuario") and seguimiento.usuario is not None:
        usuario_nombre = seguimiento.usuario.full_name if hasattr(seguimiento.usuario, "full_name") else str(seguimiento.usuario.id)
    return SeguimientoResponse(
        id=seguimiento.id,
        accion=seguimiento.accion,
        detalle=seguimiento.detalle,
        estado_anterior=seguimiento.estado_anterior,
        estado_nuevo=seguimiento.estado_nuevo,
        usuario_nombre=usuario_nombre,
        created_at=seguimiento.created_at,
    )


def _build_solicitud_response(solicitud: SolicitudCiudadana) -> SolicitudResponse:
    """Build a SolicitudResponse with nested seguimientos."""
    data = SolicitudResponse.model_validate(solicitud)
    if solicitud.seguimientos:
        data.seguimientos = [
            _build_seguimiento_response(s) for s in solicitud.seguimientos
        ]
    return data


# ── Dashboard & aggregation endpoints (must be before /{id}) ──


@router.get("/dashboard", response_model=ParticipacionDashboardStats)
async def dashboard_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
    org_id: int | None = None,
) -> ParticipacionDashboardStats:
    """Aggregated statistics for participacion ciudadana dashboard."""
    return await ParticipacionService.get_dashboard_stats(db, org_id=org_id)


@router.get("/heatmap", response_model=list[HeatmapPoint])
async def heatmap_data(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
    org_id: int | None = None,
) -> list[HeatmapPoint]:
    """GeoJSON-ready points for heatmap visualization."""
    return await ParticipacionService.get_heatmap_data(db, org_id=org_id)


# ── Chatwoot webhook ─────────────────────────────────────────


@router.post(
    "/webhook/chatwoot",
    response_model=SolicitudResponse,
    status_code=status.HTTP_201_CREATED,
)
async def chatwoot_webhook(
    payload: ChatwootWebhookPayload,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SolicitudCiudadana:
    """Intake endpoint for Chatwoot-MX webhooks.

    Accepts Chatwoot webhook events and creates solicitudes from
    conversation_created or message_created events.

    This endpoint does NOT require JWT auth — it should be protected
    by a shared webhook secret header in production.
    """
    # Validate webhook event type
    event = payload.event
    if event not in ("conversation_created", "message_created"):
        raise HTTPException(
            status_code=status.HTTP_200_OK,
            detail=f"Event '{event}' ignored",
        )

    # Extract conversation data
    conversation = payload.conversation or {}
    conversation_id = str(conversation.get("id", payload.id or "unknown"))

    # For message_created, use the message content; for conversation_created,
    # use the initial message from conversation
    content = payload.content
    if not content and conversation:
        messages = conversation.get("messages", [])
        if messages:
            content = messages[0].get("content", "")

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No content found in webhook payload",
        )

    # Extract sender name
    sender = payload.sender or {}
    sender_name = sender.get("name")

    # Use system user (id=1) for webhook-created solicitudes
    # In production, map Chatwoot agents to CRECE users
    system_user_id = 1

    try:
        solicitud = await ParticipacionService.create_from_chatwoot(
            db=db,
            conversation_id=conversation_id,
            content=content,
            sender_name=sender_name,
            user_id=system_user_id,
        )
        return solicitud
    except Exception:
        logger.exception("Failed to process Chatwoot webhook")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process webhook",
        )


# ── CRUD endpoints ───────────────────────────────────────────


@router.get("/", response_model=PaginatedResponse[SolicitudListItem])
async def list_solicitudes(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tipo: TipoSolicitud | None = None,
    estado: EstadoSolicitud | None = None,
    prioridad: int | None = Query(None, ge=1, le=5),
    seccion_id: int | None = None,
    canal: CanalOrigen | None = None,
    org_id: int | None = None,
    search: str | None = None,
    categoria: str | None = None,
) -> PaginatedResponse[SolicitudListItem]:
    """List solicitudes with filtering and pagination."""
    query = select(SolicitudCiudadana)
    count_query = select(func.count(SolicitudCiudadana.id))

    # Apply filters
    if tipo is not None:
        query = query.where(SolicitudCiudadana.tipo == tipo)
        count_query = count_query.where(SolicitudCiudadana.tipo == tipo)
    if estado is not None:
        query = query.where(SolicitudCiudadana.estado == estado)
        count_query = count_query.where(SolicitudCiudadana.estado == estado)
    if prioridad is not None:
        query = query.where(SolicitudCiudadana.prioridad == prioridad)
        count_query = count_query.where(SolicitudCiudadana.prioridad == prioridad)
    if seccion_id is not None:
        query = query.where(SolicitudCiudadana.seccion_id == seccion_id)
        count_query = count_query.where(SolicitudCiudadana.seccion_id == seccion_id)
    if canal is not None:
        query = query.where(SolicitudCiudadana.canal == canal)
        count_query = count_query.where(SolicitudCiudadana.canal == canal)
    if org_id is not None:
        query = query.where(SolicitudCiudadana.org_id == org_id)
        count_query = count_query.where(SolicitudCiudadana.org_id == org_id)
    if categoria is not None:
        query = query.where(SolicitudCiudadana.categoria == categoria)
        count_query = count_query.where(SolicitudCiudadana.categoria == categoria)
    if search:
        search_filter = SolicitudCiudadana.titulo.ilike(f"%{search}%")
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = (
        query.order_by(
            SolicitudCiudadana.prioridad.asc(),
            SolicitudCiudadana.created_at.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    items = list(result.scalars().all())

    return PaginatedResponse(
        items=[SolicitudListItem.model_validate(s) for s in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if total > 0 else 0,
    )


@router.post(
    "/",
    response_model=SolicitudResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_solicitud(
    payload: SolicitudCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> SolicitudCiudadana:
    """Create a new solicitud ciudadana. Any authenticated user."""
    solicitud = await ParticipacionService.create_solicitud(
        db=db,
        data=payload,
        user_id=current_user.id,
    )
    return solicitud


@router.get("/{solicitud_id}", response_model=SolicitudResponse)
async def get_solicitud(
    solicitud_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
) -> SolicitudCiudadana:
    """Get a single solicitud by ID with its seguimientos."""
    result = await db.execute(
        select(SolicitudCiudadana).where(SolicitudCiudadana.id == solicitud_id)
    )
    solicitud = result.scalar_one_or_none()
    if solicitud is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solicitud not found",
        )
    return solicitud


@router.patch(
    "/{solicitud_id}",
    response_model=SolicitudResponse,
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST, Role.FIELD_OPERATOR]))],
)
async def update_solicitud(
    solicitud_id: int,
    payload: SolicitudUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> SolicitudCiudadana:
    """Update an existing solicitud."""
    result = await db.execute(
        select(SolicitudCiudadana).where(SolicitudCiudadana.id == solicitud_id)
    )
    solicitud = result.scalar_one_or_none()
    if solicitud is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solicitud not found",
        )

    update_data = payload.model_dump(exclude_unset=True, exclude={"latitud", "longitud"})

    # Track state changes for seguimiento
    estado_anterior = solicitud.estado.value
    new_estado = update_data.get("estado")

    # Handle geometry update
    if payload.latitud is not None or payload.longitud is not None:
        geometry_wkt = _build_geometry_wkt(payload.latitud, payload.longitud)
        if geometry_wkt:
            update_data["ubicacion"] = geometry_wkt

    for field, value in update_data.items():
        setattr(solicitud, field, value)

    # Create seguimiento if estado changed
    if new_estado is not None and new_estado != estado_anterior:
        from app.models.solicitud import SeguimientoSolicitud

        seguimiento = SeguimientoSolicitud(
            solicitud_id=solicitud.id,
            usuario_id=current_user.id,
            accion="cambio_estado",
            detalle=f"Estado cambiado de {estado_anterior} a {new_estado}",
            estado_anterior=estado_anterior,
            estado_nuevo=new_estado if isinstance(new_estado, str) else new_estado.value,
        )
        db.add(seguimiento)

    await db.flush()
    await db.refresh(solicitud)
    return solicitud


@router.post(
    "/{solicitud_id}/asignar",
    response_model=SolicitudResponse,
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST]))],
)
async def assign_solicitud(
    solicitud_id: int,
    payload: SolicitudAssign,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> SolicitudCiudadana:
    """Assign a solicitud to a user and/or dirigente."""
    if payload.asignado_a_id is None and payload.dirigente_responsable_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide asignado_a_id or dirigente_responsable_id",
        )

    try:
        solicitud = await ParticipacionService.assign_solicitud(
            db=db,
            solicitud_id=solicitud_id,
            asignado_a_id=payload.asignado_a_id,
            dirigente_responsable_id=payload.dirigente_responsable_id,
            user_id=current_user.id,
        )
        return solicitud
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.post(
    "/{solicitud_id}/responder",
    response_model=SolicitudResponse,
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST, Role.FIELD_OPERATOR]))],
)
async def respond_solicitud(
    solicitud_id: int,
    payload: SolicitudRespond,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> SolicitudCiudadana:
    """Respond to a solicitud and mark as resolved."""
    try:
        solicitud = await ParticipacionService.respond_solicitud(
            db=db,
            solicitud_id=solicitud_id,
            respuesta=payload.respuesta,
            user_id=current_user.id,
        )
        return solicitud
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
