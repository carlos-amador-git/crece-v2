from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import Role, RoleChecker, get_current_user
from app.models.ciudadano import IntencionVotoCiudadano
from app.models.encuesta import Encuesta
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.encuesta import (
    EncuestaCreate,
    EncuestaResponse,
    EncuestaResumen,
    EncuestaUpdate,
)

router = APIRouter()


def _build_geometry_wkt(lat: float | None, lon: float | None) -> str | None:
    """Build a WKT POINT string from lat/lon, or return None."""
    if lat is not None and lon is not None:
        return f"SRID=4326;POINT({lon} {lat})"
    return None


@router.get("/", response_model=PaginatedResponse[EncuestaResponse])
async def list_encuestas(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    seccion_id: int | None = None,
    encuestador_id: int | None = None,
    intencion_voto: IntencionVotoCiudadano | None = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
) -> PaginatedResponse[EncuestaResponse]:
    """List encuestas with filtering and pagination."""
    query = select(Encuesta)
    count_query = select(func.count(Encuesta.id))

    if seccion_id is not None:
        query = query.where(Encuesta.seccion_id == seccion_id)
        count_query = count_query.where(Encuesta.seccion_id == seccion_id)
    if encuestador_id is not None:
        query = query.where(Encuesta.encuestador_id == encuestador_id)
        count_query = count_query.where(Encuesta.encuestador_id == encuestador_id)
    if intencion_voto is not None:
        query = query.where(Encuesta.intencion_voto == intencion_voto)
        count_query = count_query.where(Encuesta.intencion_voto == intencion_voto)
    if fecha_desde is not None:
        query = query.where(Encuesta.fecha_encuesta >= fecha_desde)
        count_query = count_query.where(Encuesta.fecha_encuesta >= fecha_desde)
    if fecha_hasta is not None:
        query = query.where(Encuesta.fecha_encuesta <= fecha_hasta)
        count_query = count_query.where(Encuesta.fecha_encuesta <= fecha_hasta)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = (
        query.order_by(Encuesta.fecha_encuesta.desc(), Encuesta.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    items = list(result.scalars().all())

    return PaginatedResponse(
        items=[EncuestaResponse.model_validate(e) for e in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if total > 0 else 0,
    )


@router.get("/resumen/by-seccion/{seccion_id}", response_model=EncuestaResumen)
async def resumen_by_seccion(
    seccion_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
) -> EncuestaResumen:
    """Return aggregated vote intention stats for a section."""
    query = (
        select(
            Encuesta.intencion_voto,
            func.count(Encuesta.id).label("cnt"),
        )
        .where(Encuesta.seccion_id == seccion_id)
        .group_by(Encuesta.intencion_voto)
    )
    result = await db.execute(query)
    rows = result.all()

    breakdown: dict[str, int] = {}
    total = 0
    for row in rows:
        key = row.intencion_voto.value if row.intencion_voto else "sin_dato"
        breakdown[key] = row.cnt
        total += row.cnt

    return EncuestaResumen(
        seccion_id=seccion_id,
        total_encuestas=total,
        intencion_voto_breakdown=breakdown,
    )


@router.get("/resumen/by-periodo/{periodo}", response_model=EncuestaResumen)
async def resumen_by_periodo(
    periodo: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
) -> EncuestaResumen:
    """Return aggregated vote intention stats for a time period.

    Periodo format examples: '2026-Q1', '2026-03', '2026-W14'.
    Matches encuestas where fecha_encuesta falls within the period.
    For simplicity, this filters by the stored periodo or by date prefix matching.
    """
    # Try to parse periodo as YYYY-MM for date range filtering
    query = (
        select(
            Encuesta.intencion_voto,
            func.count(Encuesta.id).label("cnt"),
        )
        .where(func.to_char(Encuesta.fecha_encuesta, "YYYY-MM").like(f"{periodo}%"))
        .group_by(Encuesta.intencion_voto)
    )
    result = await db.execute(query)
    rows = result.all()

    breakdown: dict[str, int] = {}
    total = 0
    for row in rows:
        key = row.intencion_voto.value if row.intencion_voto else "sin_dato"
        breakdown[key] = row.cnt
        total += row.cnt

    return EncuestaResumen(
        total_encuestas=total,
        intencion_voto_breakdown=breakdown,
        periodo=periodo,
    )


@router.get("/{encuesta_id}", response_model=EncuestaResponse)
async def get_encuesta(
    encuesta_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
) -> Encuesta:
    """Get a single encuesta by ID."""
    result = await db.execute(select(Encuesta).where(Encuesta.id == encuesta_id))
    encuesta = result.scalar_one_or_none()
    if encuesta is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Encuesta not found")
    return encuesta


@router.post(
    "/",
    response_model=EncuestaResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST, Role.FIELD_OPERATOR]))],
)
async def create_encuesta(
    payload: EncuestaCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Encuesta:
    """Create a new field survey encuesta. Auto-sets encuestador_id from current user."""
    data = payload.model_dump(exclude={"latitud", "longitud"})
    data["encuestador_id"] = current_user.id

    # Set org_id from the current user if available
    if hasattr(current_user, "org_id") and current_user.org_id is not None:
        data["org_id"] = current_user.org_id

    geometry_wkt = _build_geometry_wkt(payload.latitud, payload.longitud)
    if geometry_wkt:
        data["ubicacion_captura"] = geometry_wkt

    encuesta = Encuesta(**data)
    db.add(encuesta)
    await db.flush()
    await db.refresh(encuesta)
    return encuesta


@router.patch(
    "/{encuesta_id}",
    response_model=EncuestaResponse,
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST]))],
)
async def update_encuesta(
    encuesta_id: int,
    payload: EncuestaUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Encuesta:
    """Update an encuesta. Admin and analyst only."""
    result = await db.execute(select(Encuesta).where(Encuesta.id == encuesta_id))
    encuesta = result.scalar_one_or_none()
    if encuesta is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Encuesta not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(encuesta, field, value)

    await db.flush()
    await db.refresh(encuesta)
    return encuesta
