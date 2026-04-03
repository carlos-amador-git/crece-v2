from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import Role, RoleChecker, get_current_user
from app.models.ciudadano import Ciudadano
from app.models.user import User
from app.schemas.ciudadano import CiudadanoCreate, CiudadanoResponse, CiudadanoUpdate
from app.schemas.common import PaginatedResponse

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[CiudadanoResponse])
async def list_ciudadanos(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    seccion_id: int | None = None,
    es_promotor: bool | None = None,
    search: str | None = None,
) -> PaginatedResponse[CiudadanoResponse]:
    """List ciudadanos with filtering and pagination."""
    query = select(Ciudadano)
    count_query = select(func.count(Ciudadano.id))

    if seccion_id is not None:
        query = query.where(Ciudadano.seccion_id == seccion_id)
        count_query = count_query.where(Ciudadano.seccion_id == seccion_id)
    if es_promotor is not None:
        query = query.where(Ciudadano.es_promotor == es_promotor)
        count_query = count_query.where(Ciudadano.es_promotor == es_promotor)
    if search:
        pattern = f"%{search}%"
        search_filter = (
            Ciudadano.nombre.ilike(pattern)
            | Ciudadano.apellido_paterno.ilike(pattern)
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = (
        query.order_by(Ciudadano.apellido_paterno, Ciudadano.nombre)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    items = list(result.scalars().all())

    return PaginatedResponse(
        items=[CiudadanoResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if total > 0 else 0,
    )


@router.get("/promotores", response_model=PaginatedResponse[CiudadanoResponse])
async def list_promotores(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[CiudadanoResponse]:
    """List all ciudadanos marked as promotores."""
    base_filter = Ciudadano.es_promotor.is_(True)
    count_query = select(func.count(Ciudadano.id)).where(base_filter)
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = (
        select(Ciudadano)
        .where(base_filter)
        .order_by(Ciudadano.apellido_paterno, Ciudadano.nombre)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    items = list(result.scalars().all())

    return PaginatedResponse(
        items=[CiudadanoResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if total > 0 else 0,
    )


@router.get("/by-seccion/{seccion_id}", response_model=PaginatedResponse[CiudadanoResponse])
async def list_ciudadanos_by_seccion(
    seccion_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[CiudadanoResponse]:
    """List ciudadanos belonging to a specific electoral section."""
    base_filter = Ciudadano.seccion_id == seccion_id
    count_query = select(func.count(Ciudadano.id)).where(base_filter)
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = (
        select(Ciudadano)
        .where(base_filter)
        .order_by(Ciudadano.apellido_paterno, Ciudadano.nombre)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    items = list(result.scalars().all())

    return PaginatedResponse(
        items=[CiudadanoResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if total > 0 else 0,
    )


@router.get("/{ciudadano_id}", response_model=CiudadanoResponse)
async def get_ciudadano(
    ciudadano_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
) -> Ciudadano:
    """Get a single ciudadano by ID."""
    result = await db.execute(select(Ciudadano).where(Ciudadano.id == ciudadano_id))
    ciudadano = result.scalar_one_or_none()
    if ciudadano is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ciudadano not found")
    return ciudadano


@router.post(
    "/",
    response_model=CiudadanoResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST, Role.FIELD_OPERATOR]))],
)
async def create_ciudadano(
    payload: CiudadanoCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Ciudadano:
    """Create a new ciudadano. Requires at least field_operator role."""
    ciudadano = Ciudadano(
        **payload.model_dump(),
        registrado_por_id=current_user.id,
    )
    db.add(ciudadano)
    await db.flush()
    await db.refresh(ciudadano)
    return ciudadano


@router.patch(
    "/{ciudadano_id}",
    response_model=CiudadanoResponse,
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST, Role.FIELD_OPERATOR]))],
)
async def update_ciudadano(
    ciudadano_id: int,
    payload: CiudadanoUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Ciudadano:
    """Update an existing ciudadano."""
    result = await db.execute(select(Ciudadano).where(Ciudadano.id == ciudadano_id))
    ciudadano = result.scalar_one_or_none()
    if ciudadano is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ciudadano not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(ciudadano, field, value)

    await db.flush()
    await db.refresh(ciudadano)
    return ciudadano


@router.delete(
    "/{ciudadano_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RoleChecker([Role.ADMIN]))],
)
async def delete_ciudadano(
    ciudadano_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a ciudadano. Admin only."""
    result = await db.execute(select(Ciudadano).where(Ciudadano.id == ciudadano_id))
    ciudadano = result.scalar_one_or_none()
    if ciudadano is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ciudadano not found")
    await db.delete(ciudadano)
