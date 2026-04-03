from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.core.database import get_db
from app.core.security import Role, RoleChecker, get_current_user
from app.models.dirigente import Dirigente
from app.models.plan_ia import PlanIA, TipoPlan
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.plan_ia import PlanApproveRequest, PlanGenerateRequest, PlanIAResponse
from app.services.plan_generator import generate_plan, generate_plan_stream

router = APIRouter()


@router.post(
    "/generar",
    response_model=PlanIAResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST]))],
)
async def generar_plan(
    payload: PlanGenerateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> PlanIA:
    """Generate an AI-powered plan for a dirigente."""
    result = await db.execute(select(Dirigente).where(Dirigente.id == payload.dirigente_id))
    dirigente = result.scalar_one_or_none()
    if dirigente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dirigente not found"
        )

    plan = await generate_plan(
        db=db,
        dirigente=dirigente,
        tipo=payload.tipo,
        user=current_user,
        contexto_adicional=payload.contexto_adicional,
    )
    return plan


@router.post(
    "/generar/stream",
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST]))],
)
async def generar_plan_stream(
    payload: PlanGenerateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> EventSourceResponse:
    """Generate an AI plan with Server-Sent Events streaming."""
    result = await db.execute(select(Dirigente).where(Dirigente.id == payload.dirigente_id))
    dirigente = result.scalar_one_or_none()
    if dirigente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dirigente not found"
        )

    return EventSourceResponse(
        generate_plan_stream(
            db=db,
            dirigente=dirigente,
            tipo=payload.tipo,
            user=current_user,
            contexto_adicional=payload.contexto_adicional,
        )
    )


@router.get("/", response_model=PaginatedResponse[PlanIAResponse])
async def list_planes(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
    dirigente_id: int | None = None,
    tipo: TipoPlan | None = None,
    aprobado: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[PlanIAResponse]:
    """List AI-generated plans with filtering."""
    query = select(PlanIA)
    count_query = select(func.count(PlanIA.id))

    if dirigente_id is not None:
        query = query.where(PlanIA.dirigente_id == dirigente_id)
        count_query = count_query.where(PlanIA.dirigente_id == dirigente_id)
    if tipo is not None:
        query = query.where(PlanIA.tipo == tipo)
        count_query = count_query.where(PlanIA.tipo == tipo)
    if aprobado is not None:
        query = query.where(PlanIA.aprobado == aprobado)
        count_query = count_query.where(PlanIA.aprobado == aprobado)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(PlanIA.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = list(result.scalars().all())

    return PaginatedResponse(
        items=[PlanIAResponse.model_validate(p) for p in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if total > 0 else 0,
    )


@router.get("/{plan_id}", response_model=PlanIAResponse)
async def get_plan(
    plan_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
) -> PlanIA:
    """Get a specific plan by ID."""
    result = await db.execute(select(PlanIA).where(PlanIA.id == plan_id))
    plan = result.scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    return plan


@router.patch(
    "/{plan_id}/aprobar",
    response_model=PlanIAResponse,
    dependencies=[Depends(RoleChecker([Role.ADMIN]))],
)
async def aprobar_plan(
    plan_id: int,
    payload: PlanApproveRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PlanIA:
    """Approve or reject a plan. Admin only."""
    result = await db.execute(select(PlanIA).where(PlanIA.id == plan_id))
    plan = result.scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    plan.aprobado = payload.aprobado
    await db.flush()
    await db.refresh(plan)
    return plan
