from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import Role, RoleChecker, get_current_user
from app.models.programa_social import NivelGobierno, ProgramaBeneficiario, ProgramaSocial
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.programa_social import (
    ProgramaBeneficiarioCreate,
    ProgramaBeneficiarioResponse,
    ProgramaConBeneficiariosResponse,
    ProgramaSocialCreate,
    ProgramaSocialResponse,
    ProgramaSocialUpdate,
)

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[ProgramaSocialResponse])
async def list_programas(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    nivel_gobierno: NivelGobierno | None = None,
    search: str | None = None,
) -> PaginatedResponse[ProgramaSocialResponse]:
    """List programas sociales with optional filtering."""
    query = select(ProgramaSocial)
    count_query = select(func.count(ProgramaSocial.id))

    if nivel_gobierno is not None:
        query = query.where(ProgramaSocial.nivel_gobierno == nivel_gobierno)
        count_query = count_query.where(ProgramaSocial.nivel_gobierno == nivel_gobierno)
    if search:
        query = query.where(ProgramaSocial.nombre.ilike(f"%{search}%"))
        count_query = count_query.where(ProgramaSocial.nombre.ilike(f"%{search}%"))

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(ProgramaSocial.nombre).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = list(result.scalars().all())

    return PaginatedResponse(
        items=[ProgramaSocialResponse.model_validate(p) for p in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if total > 0 else 0,
    )


@router.get("/by-seccion/{seccion_id}", response_model=list[ProgramaConBeneficiariosResponse])
async def list_programas_by_seccion(
    seccion_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
) -> list[ProgramaConBeneficiariosResponse]:
    """List programas with beneficiary counts for a specific electoral section."""
    query = (
        select(
            ProgramaSocial.id,
            ProgramaSocial.nombre,
            ProgramaSocial.descripcion,
            ProgramaSocial.dependencia,
            ProgramaSocial.nivel_gobierno,
            ProgramaSocial.presupuesto_anual,
            ProgramaBeneficiario.beneficiarios_count,
            ProgramaBeneficiario.periodo,
            ProgramaBeneficiario.fuente_datos,
        )
        .join(ProgramaBeneficiario, ProgramaSocial.id == ProgramaBeneficiario.programa_id)
        .where(ProgramaBeneficiario.seccion_id == seccion_id)
        .order_by(ProgramaSocial.nombre, ProgramaBeneficiario.periodo.desc())
    )
    result = await db.execute(query)
    rows = result.all()

    return [
        ProgramaConBeneficiariosResponse(
            id=row.id,
            nombre=row.nombre,
            descripcion=row.descripcion,
            dependencia=row.dependencia,
            nivel_gobierno=row.nivel_gobierno,
            presupuesto_anual=row.presupuesto_anual,
            beneficiarios_count=row.beneficiarios_count,
            periodo=row.periodo,
            fuente_datos=row.fuente_datos,
        )
        for row in rows
    ]


@router.get("/{programa_id}", response_model=ProgramaSocialResponse)
async def get_programa(
    programa_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
) -> ProgramaSocial:
    """Get a single programa social by ID."""
    result = await db.execute(select(ProgramaSocial).where(ProgramaSocial.id == programa_id))
    programa = result.scalar_one_or_none()
    if programa is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Programa social not found"
        )
    return programa


@router.post(
    "/",
    response_model=ProgramaSocialResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker([Role.ADMIN]))],
)
async def create_programa(
    payload: ProgramaSocialCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProgramaSocial:
    """Create a new programa social. Admin only (government data)."""
    programa = ProgramaSocial(**payload.model_dump())
    db.add(programa)
    await db.flush()
    await db.refresh(programa)
    return programa


@router.patch(
    "/{programa_id}",
    response_model=ProgramaSocialResponse,
    dependencies=[Depends(RoleChecker([Role.ADMIN]))],
)
async def update_programa(
    programa_id: int,
    payload: ProgramaSocialUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProgramaSocial:
    """Update a programa social. Admin only."""
    result = await db.execute(select(ProgramaSocial).where(ProgramaSocial.id == programa_id))
    programa = result.scalar_one_or_none()
    if programa is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Programa social not found"
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(programa, field, value)

    await db.flush()
    await db.refresh(programa)
    return programa


@router.delete(
    "/{programa_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RoleChecker([Role.ADMIN]))],
)
async def delete_programa(
    programa_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a programa social. Admin only."""
    result = await db.execute(select(ProgramaSocial).where(ProgramaSocial.id == programa_id))
    programa = result.scalar_one_or_none()
    if programa is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Programa social not found"
        )
    await db.delete(programa)


# ── Beneficiarios sub-resource ───────────────────────────────


@router.get(
    "/{programa_id}/beneficiarios",
    response_model=list[ProgramaBeneficiarioResponse],
)
async def list_beneficiarios(
    programa_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
) -> list[ProgramaBeneficiario]:
    """List beneficiario records for a programa."""
    result = await db.execute(
        select(ProgramaBeneficiario)
        .where(ProgramaBeneficiario.programa_id == programa_id)
        .order_by(ProgramaBeneficiario.periodo.desc())
    )
    return list(result.scalars().all())


@router.post(
    "/{programa_id}/beneficiarios",
    response_model=ProgramaBeneficiarioResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker([Role.ADMIN]))],
)
async def add_beneficiario(
    programa_id: int,
    payload: ProgramaBeneficiarioCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProgramaBeneficiario:
    """Add a beneficiario record. Admin only (government data)."""
    # Verify programa exists
    prog_result = await db.execute(select(ProgramaSocial).where(ProgramaSocial.id == programa_id))
    if prog_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Programa social not found"
        )

    beneficiario = ProgramaBeneficiario(
        programa_id=programa_id,
        seccion_id=payload.seccion_id,
        beneficiarios_count=payload.beneficiarios_count,
        periodo=payload.periodo,
        fecha_actualizacion=payload.fecha_actualizacion,
        fuente_datos=payload.fuente_datos,
    )
    db.add(beneficiario)
    await db.flush()
    await db.refresh(beneficiario)
    return beneficiario
