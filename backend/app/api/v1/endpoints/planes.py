from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.core.database import get_db
from app.core.security import Role, RoleChecker, get_current_user
from app.models.dirigente import Dirigente
from app.models.plan_ia import EstadoTarea, PlanIA, PlanTarea, TipoPlan
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.plan_ia import (
    PlanApproveRequest,
    PlanGenerateRequest,
    PlanIAResponse,
    PlanProgresoResponse,
    PlanTareaCompleteRequest,
    PlanTareaResponse,
    PlanTareaUpdate,
)
from app.services.plan_generator import generate_plan, generate_plan_stream
from app.services.plan_structured import generate_structured_plan, record_task_change

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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dirigente not found")

    if payload.estructurado:
        plan = await generate_structured_plan(
            db=db,
            dirigente=dirigente,
            tipo=payload.tipo,
            user=current_user,
            contexto_adicional=payload.contexto_adicional,
        )
    else:
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dirigente not found")

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
    current_user: Annotated[User, Depends(get_current_user)],
    dirigente_id: int | None = None,
    tipo: TipoPlan | None = None,
    aprobado: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[PlanIAResponse]:
    """List AI-generated plans with filtering.

    If the user has a dirigente_id, auto-filter to their dirigente only.
    """
    query = select(PlanIA)
    count_query = select(func.count(PlanIA.id))

    # Auto-filter for dirigente users
    effective_dirigente_id = dirigente_id
    if current_user.dirigente_id is not None:
        effective_dirigente_id = current_user.dirigente_id

    if effective_dirigente_id is not None:
        query = query.where(PlanIA.dirigente_id == effective_dirigente_id)
        count_query = count_query.where(PlanIA.dirigente_id == effective_dirigente_id)
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


# ── Sprint 3: tareas editables de un plan ────────────────────────────


async def _get_plan_or_404(db: AsyncSession, plan_id: int) -> PlanIA:
    result = await db.execute(select(PlanIA).where(PlanIA.id == plan_id))
    plan = result.scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    return plan


async def _get_tarea_or_404(db: AsyncSession, plan_id: int, task_id: int) -> PlanTarea:
    result = await db.execute(
        select(PlanTarea).where(PlanTarea.id == task_id, PlanTarea.plan_id == plan_id)
    )
    tarea = result.scalar_one_or_none()
    if tarea is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarea not found")
    return tarea


@router.get("/{plan_id}/tareas", response_model=list[PlanTareaResponse])
async def list_tareas(
    plan_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
) -> list[PlanTarea]:
    await _get_plan_or_404(db, plan_id)
    result = await db.execute(
        select(PlanTarea).where(PlanTarea.plan_id == plan_id).order_by(PlanTarea.orden)
    )
    return list(result.scalars().all())


@router.patch(
    "/{plan_id}/tareas/{task_id}",
    response_model=PlanTareaResponse,
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST]))],
)
async def update_tarea(
    plan_id: int,
    task_id: int,
    payload: PlanTareaUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> PlanTarea:
    tarea = await _get_tarea_or_404(db, plan_id, task_id)

    updates = payload.model_dump(exclude_unset=True)
    history = list(tarea.cambios_historial or [])
    for field, new_value in updates.items():
        old_value = getattr(tarea, field)
        if old_value == new_value:
            continue
        history = record_task_change(
            history,
            change_type="edited",
            by_user_id=current_user.id,
            field=field,
            old_value=str(old_value) if old_value is not None else None,
            new_value=str(new_value) if new_value is not None else None,
        )
        setattr(tarea, field, new_value)

    tarea.cambios_historial = history
    await db.flush()
    await db.refresh(tarea)
    return tarea


@router.post(
    "/{plan_id}/tareas/{task_id}/complete",
    response_model=PlanTareaResponse,
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST]))],
)
async def complete_tarea(
    plan_id: int,
    task_id: int,
    payload: PlanTareaCompleteRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> PlanTarea:
    from datetime import UTC, datetime

    tarea = await _get_tarea_or_404(db, plan_id, task_id)
    tarea.estado = EstadoTarea.DONE
    tarea.metrica_valor_real = payload.metrica_valor_real
    tarea.completado_at = datetime.now(UTC)
    tarea.cambios_historial = record_task_change(
        tarea.cambios_historial,
        change_type="completed",
        by_user_id=current_user.id,
        field="metrica_valor_real",
        new_value=payload.metrica_valor_real,
    )
    if payload.nota:
        tarea.cambios_historial = record_task_change(
            tarea.cambios_historial,
            change_type="note",
            by_user_id=current_user.id,
            new_value=payload.nota,
        )
    await db.flush()
    await db.refresh(tarea)
    return tarea


@router.get("/{plan_id}/progreso", response_model=PlanProgresoResponse)
async def get_progreso(
    plan_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
) -> PlanProgresoResponse:
    await _get_plan_or_404(db, plan_id)
    result = await db.execute(select(PlanTarea).where(PlanTarea.plan_id == plan_id))
    tareas = list(result.scalars().all())

    counts = {EstadoTarea.TODO: 0, EstadoTarea.IN_PROGRESS: 0, EstadoTarea.DONE: 0}
    impacto: dict[str, float] = {}
    for t in tareas:
        counts[t.estado] += 1
        if t.metrica_objetivo and t.metrica_valor_real is not None:
            impacto[t.metrica_objetivo] = (
                impacto.get(t.metrica_objetivo, 0.0) + t.metrica_valor_real
            )

    total = len(tareas)
    pct = (counts[EstadoTarea.DONE] / total * 100) if total else 0.0

    return PlanProgresoResponse(
        plan_id=plan_id,
        total_tareas=total,
        tareas_todo=counts[EstadoTarea.TODO],
        tareas_in_progress=counts[EstadoTarea.IN_PROGRESS],
        tareas_done=counts[EstadoTarea.DONE],
        porcentaje_ejecutado=round(pct, 1),
        impacto_acumulado=impacto,
    )
