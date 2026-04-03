from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import Role, RoleChecker, get_current_user
from app.models.organizacion import Organizacion
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.organizacion import (
    OrganizacionCreate,
    OrganizacionResponse,
    OrganizacionUpdate,
)

router = APIRouter()


@router.get(
    "/",
    response_model=PaginatedResponse[OrganizacionResponse],
    dependencies=[Depends(RoleChecker([Role.ADMIN]))],
)
async def list_organizaciones(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_active: bool | None = None,
    search: str | None = None,
) -> PaginatedResponse[OrganizacionResponse]:
    """List organizaciones with pagination. Admin only."""
    query = select(Organizacion)
    count_query = select(func.count(Organizacion.id))

    if is_active is not None:
        query = query.where(Organizacion.is_active == is_active)
        count_query = count_query.where(Organizacion.is_active == is_active)
    if search:
        query = query.where(Organizacion.nombre.ilike(f"%{search}%"))
        count_query = count_query.where(Organizacion.nombre.ilike(f"%{search}%"))

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = (
        query.order_by(Organizacion.nombre)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    items = list(result.scalars().all())

    return PaginatedResponse(
        items=[OrganizacionResponse.model_validate(o) for o in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if total > 0 else 0,
    )


@router.get("/{organizacion_id}", response_model=OrganizacionResponse)
async def get_organizacion(
    organizacion_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
) -> Organizacion:
    """Get a single organizacion by ID."""
    result = await db.execute(
        select(Organizacion).where(Organizacion.id == organizacion_id)
    )
    org = result.scalar_one_or_none()
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organizacion not found"
        )
    return org


@router.post(
    "/",
    response_model=OrganizacionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker([Role.ADMIN]))],
)
async def create_organizacion(
    payload: OrganizacionCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Organizacion:
    """Create a new organizacion. Admin only."""
    org = Organizacion(**payload.model_dump())
    db.add(org)
    await db.flush()
    await db.refresh(org)
    return org


@router.patch(
    "/{organizacion_id}",
    response_model=OrganizacionResponse,
    dependencies=[Depends(RoleChecker([Role.ADMIN]))],
)
async def update_organizacion(
    organizacion_id: int,
    payload: OrganizacionUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Organizacion:
    """Update an organizacion. Admin only."""
    result = await db.execute(
        select(Organizacion).where(Organizacion.id == organizacion_id)
    )
    org = result.scalar_one_or_none()
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organizacion not found"
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(org, field, value)

    await db.flush()
    await db.refresh(org)
    return org


@router.delete(
    "/{organizacion_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RoleChecker([Role.ADMIN]))],
)
async def delete_organizacion(
    organizacion_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete an organizacion. Admin only."""
    result = await db.execute(
        select(Organizacion).where(Organizacion.id == organizacion_id)
    )
    org = result.scalar_one_or_none()
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organizacion not found"
        )
    await db.delete(org)
