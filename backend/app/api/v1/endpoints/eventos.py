from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.scope import assert_dirigente_access
from app.core.security import Role, RoleChecker, get_current_user
from app.models.evento import EstadoEvento, Evento, EventoAsistente
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.evento import (
    EventoAsistenteCreate,
    EventoAsistenteResponse,
    EventoCompletarPayload,
    EventoCreate,
    EventoResponse,
    EventoROIResponse,
    EventoUpdate,
)

router = APIRouter()


def _build_geometry_wkt(lat: float | None, lon: float | None) -> str | None:
    """Build a WKT POINT string from lat/lon, or return None."""
    if lat is not None and lon is not None:
        return f"SRID=4326;POINT({lon} {lat})"
    return None


@router.get("/", response_model=PaginatedResponse[EventoResponse])
async def list_eventos(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    estado: EstadoEvento | None = None,
    tipo: str | None = None,
    search: str | None = None,
    org_id: int | None = None,
) -> PaginatedResponse[EventoResponse]:
    """List eventos with filtering and pagination."""
    query = select(Evento)
    count_query = select(func.count(Evento.id))

    # Multi-tenant scope: viewer users see only their org.
    if current_user.role != "admin":
        query = query.where(Evento.org_id == current_user.org_id)
        count_query = count_query.where(Evento.org_id == current_user.org_id)

    if estado is not None:
        query = query.where(Evento.estado == estado)
        count_query = count_query.where(Evento.estado == estado)
    if tipo is not None:
        query = query.where(Evento.tipo == tipo)
        count_query = count_query.where(Evento.tipo == tipo)
    if org_id is not None and current_user.role == "admin":
        query = query.where(Evento.org_id == org_id)
        count_query = count_query.where(Evento.org_id == org_id)
    if search:
        query = query.where(Evento.titulo.ilike(f"%{search}%"))
        count_query = count_query.where(Evento.titulo.ilike(f"%{search}%"))

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = (
        query.order_by(Evento.fecha_inicio.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    result = await db.execute(query)
    items = list(result.scalars().all())

    return PaginatedResponse(
        items=[EventoResponse.model_validate(e) for e in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if total > 0 else 0,
    )


@router.get("/upcoming", response_model=PaginatedResponse[EventoResponse])
async def list_upcoming_eventos(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[EventoResponse]:
    """List upcoming (programado or en_curso) eventos sorted by fecha_inicio."""
    now = datetime.now(UTC)
    base_filter = Evento.estado.in_([EstadoEvento.PROGRAMADO, EstadoEvento.EN_CURSO]) & (
        Evento.fecha_inicio >= now
    )
    count_query = select(func.count(Evento.id)).where(base_filter)
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = (
        select(Evento)
        .where(base_filter)
        .order_by(Evento.fecha_inicio.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    items = list(result.scalars().all())

    return PaginatedResponse(
        items=[EventoResponse.model_validate(e) for e in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if total > 0 else 0,
    )


@router.get("/stats/roi", response_model=EventoROIResponse)
async def stats_roi(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
    org_id: int | None = None,
) -> EventoROIResponse:
    """Return ROI metrics for events that have costo_total data."""
    base_filter = Evento.costo_total.isnot(None)
    if org_id is not None:
        base_filter = base_filter & (Evento.org_id == org_id)

    query = select(
        func.count(Evento.id).label("total_eventos"),
        func.coalesce(func.sum(Evento.costo_total), 0).label("costo_total_sum"),
        func.coalesce(func.sum(Evento.asistentes_reales), 0).label("asistentes_reales_sum"),
        func.coalesce(func.sum(Evento.nuevos_simpatizantes), 0).label("nuevos_simpatizantes_sum"),
    ).where(base_filter)

    result = await db.execute(query)
    row = result.one()

    total_eventos = row.total_eventos
    costo_total_sum = float(row.costo_total_sum)
    asistentes_sum = int(row.asistentes_reales_sum)
    simpatizantes_sum = int(row.nuevos_simpatizantes_sum)

    return EventoROIResponse(
        total_eventos=total_eventos,
        costo_total_sum=costo_total_sum,
        asistentes_reales_sum=asistentes_sum,
        nuevos_simpatizantes_sum=simpatizantes_sum,
        costo_promedio_por_evento=costo_total_sum / total_eventos if total_eventos > 0 else 0,
        costo_promedio_por_asistente=costo_total_sum / asistentes_sum
        if asistentes_sum > 0
        else None,
        costo_promedio_por_simpatizante=costo_total_sum / simpatizantes_sum
        if simpatizantes_sum > 0
        else None,
    )


@router.get("/by-dirigente/{dirigente_id}", response_model=PaginatedResponse[EventoResponse])
async def list_eventos_by_dirigente(
    dirigente_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[EventoResponse]:
    """List eventos assigned to a specific dirigente."""
    await assert_dirigente_access(db, current_user, dirigente_id)
    base_filter = Evento.dirigente_id == dirigente_id
    count_query = select(func.count(Evento.id)).where(base_filter)
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = (
        select(Evento)
        .where(base_filter)
        .order_by(Evento.fecha_inicio.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    items = list(result.scalars().all())

    return PaginatedResponse(
        items=[EventoResponse.model_validate(e) for e in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if total > 0 else 0,
    )


@router.get("/{evento_id}", response_model=EventoResponse)
async def get_evento(
    evento_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
) -> Evento:
    """Get a single evento by ID."""
    result = await db.execute(select(Evento).where(Evento.id == evento_id))
    evento = result.scalar_one_or_none()
    if evento is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento not found")
    return evento


@router.post(
    "/",
    response_model=EventoResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST, Role.FIELD_OPERATOR]))],
)
async def create_evento(
    payload: EventoCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Evento:
    """Create a new evento."""
    data = payload.model_dump(exclude={"latitud", "longitud"})
    data["organizador_id"] = current_user.id
    geometry_wkt = _build_geometry_wkt(payload.latitud, payload.longitud)
    if geometry_wkt:
        data["geometry"] = geometry_wkt

    evento = Evento(**data)
    db.add(evento)
    await db.flush()
    await db.refresh(evento)
    return evento


@router.patch(
    "/{evento_id}",
    response_model=EventoResponse,
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST, Role.FIELD_OPERATOR]))],
)
async def update_evento(
    evento_id: int,
    payload: EventoUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Evento:
    """Update an existing evento."""
    result = await db.execute(select(Evento).where(Evento.id == evento_id))
    evento = result.scalar_one_or_none()
    if evento is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento not found")

    update_data = payload.model_dump(exclude_unset=True, exclude={"latitud", "longitud"})

    # Handle geometry update if lat/lon provided
    if payload.latitud is not None or payload.longitud is not None:
        geometry_wkt = _build_geometry_wkt(payload.latitud, payload.longitud)
        if geometry_wkt:
            update_data["geometry"] = geometry_wkt

    for field, value in update_data.items():
        setattr(evento, field, value)

    await db.flush()
    await db.refresh(evento)
    return evento


@router.patch(
    "/{evento_id}/completar",
    response_model=EventoResponse,
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST, Role.FIELD_OPERATOR]))],
)
async def completar_evento(
    evento_id: int,
    payload: EventoCompletarPayload,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Evento:
    """Mark an evento as completed with optional attendance count."""
    result = await db.execute(select(Evento).where(Evento.id == evento_id))
    evento = result.scalar_one_or_none()
    if evento is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento not found")

    if evento.estado == EstadoEvento.CANCELADO:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot complete a cancelled evento",
        )

    evento.estado = EstadoEvento.COMPLETADO
    if payload.asistentes_reales is not None:
        evento.asistentes_reales = payload.asistentes_reales
    if payload.notas is not None:
        evento.notas = payload.notas

    await db.flush()
    await db.refresh(evento)
    return evento


@router.delete(
    "/{evento_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RoleChecker([Role.ADMIN]))],
)
async def delete_evento(
    evento_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete an evento. Admin only."""
    result = await db.execute(select(Evento).where(Evento.id == evento_id))
    evento = result.scalar_one_or_none()
    if evento is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento not found")
    await db.delete(evento)


# ── Asistentes sub-resource ──────────────────────────────────


@router.get("/{evento_id}/asistentes", response_model=list[EventoAsistenteResponse])
async def list_asistentes(
    evento_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
) -> list[EventoAsistente]:
    """List asistentes for a given evento."""
    result = await db.execute(select(EventoAsistente).where(EventoAsistente.evento_id == evento_id))
    return list(result.scalars().all())


@router.post(
    "/{evento_id}/asistentes",
    response_model=EventoAsistenteResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST, Role.FIELD_OPERATOR]))],
)
async def add_asistente(
    evento_id: int,
    payload: EventoAsistenteCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EventoAsistente:
    """Add a ciudadano as asistente to an evento."""
    # Verify evento exists
    ev_result = await db.execute(select(Evento).where(Evento.id == evento_id))
    if ev_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento not found")

    # Check for duplicate
    dup_result = await db.execute(
        select(EventoAsistente).where(
            EventoAsistente.evento_id == evento_id,
            EventoAsistente.ciudadano_id == payload.ciudadano_id,
        )
    )
    if dup_result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ciudadano already registered for this evento",
        )

    asistente = EventoAsistente(
        evento_id=evento_id,
        ciudadano_id=payload.ciudadano_id,
        confirmado=payload.confirmado,
    )
    db.add(asistente)
    await db.flush()
    await db.refresh(asistente)
    return asistente
