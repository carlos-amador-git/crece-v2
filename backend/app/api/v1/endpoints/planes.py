from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.core.database import get_db
from app.core.limiter import limiter
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


# ── 2026-04-25 audit IA H-01 · org_id scoping helpers ────────────────


async def _get_dirigente_with_org_check(
    db: AsyncSession, dirigente_id: int, current_user: User
) -> Dirigente:
    """Fetch dirigente · verifica que pertenezca al org del caller (admin bypass)."""
    result = await db.execute(select(Dirigente).where(Dirigente.id == dirigente_id))
    dirigente = result.scalar_one_or_none()
    if dirigente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dirigente not found")
    if current_user.role != Role.ADMIN.value and dirigente.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dirigente fuera de tu organización",
        )
    return dirigente


async def _get_plan_with_org_check(
    db: AsyncSession, plan_id: int, current_user: User
) -> PlanIA:
    """Fetch plan + verifica que el dirigente asociado pertenezca al org del caller."""
    result = await db.execute(
        select(PlanIA, Dirigente)
        .join(Dirigente, PlanIA.dirigente_id == Dirigente.id)
        .where(PlanIA.id == plan_id)
    )
    row = result.first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    plan, dirigente = row
    if current_user.role != Role.ADMIN.value and dirigente.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Plan fuera de tu organización",
        )
    return plan


@router.post(
    "/generar",
    response_model=PlanIAResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST]))],
)
@limiter.limit("5/hour")
async def generar_plan(
    request: Request,
    payload: PlanGenerateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> PlanIA:
    """Generate an AI-powered plan for a dirigente."""
    dirigente = await _get_dirigente_with_org_check(db, payload.dirigente_id, current_user)

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
@limiter.limit("5/hour")
async def generar_plan_stream(
    request: Request,
    payload: PlanGenerateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> EventSourceResponse:
    """Generate an AI plan with Server-Sent Events streaming."""
    dirigente = await _get_dirigente_with_org_check(db, payload.dirigente_id, current_user)

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
    # 2026-04-25 audit IA H-01 · scope cross-tenant via org_id en JOIN
    query = select(PlanIA).join(Dirigente, PlanIA.dirigente_id == Dirigente.id)
    count_query = select(func.count(PlanIA.id)).join(
        Dirigente, PlanIA.dirigente_id == Dirigente.id
    )
    if current_user.role != Role.ADMIN.value:
        query = query.where(Dirigente.org_id == current_user.org_id)
        count_query = count_query.where(Dirigente.org_id == current_user.org_id)

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
    current_user: Annotated[User, Depends(get_current_user)],
) -> PlanIA:
    """Get a specific plan by ID."""
    return await _get_plan_with_org_check(db, plan_id, current_user)


@router.patch(
    "/{plan_id}/aprobar",
    response_model=PlanIAResponse,
    dependencies=[Depends(RoleChecker([Role.ADMIN]))],
)
async def aprobar_plan(
    plan_id: int,
    payload: PlanApproveRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> PlanIA:
    """Approve or reject a plan. Admin only."""
    plan = await _get_plan_with_org_check(db, plan_id, current_user)
    plan.aprobado = payload.aprobado
    await db.flush()
    await db.refresh(plan)
    return plan


# ── Sprint 3: tareas editables de un plan ────────────────────────────


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
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[PlanTarea]:
    await _get_plan_with_org_check(db, plan_id, current_user)
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
    await _get_plan_with_org_check(db, plan_id, current_user)
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

    await _get_plan_with_org_check(db, plan_id, current_user)
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
    current_user: Annotated[User, Depends(get_current_user)],
) -> PlanProgresoResponse:
    await _get_plan_with_org_check(db, plan_id, current_user)
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
