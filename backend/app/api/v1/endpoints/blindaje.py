from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import Role, RoleChecker, get_current_user
from app.models.gasto_electoral import (
    AlertaCompliance,
    CategoriaGastoINE,
    GastoElectoral,
    SeveridadAlerta,
    TipoAlertaCompliance,
)
from app.models.social import SocialPost
from app.models.user import User
from app.schemas.blindaje import (
    AlertaComplianceResponse,
    BotAnalysisResult,
    ComplianceReportResponse,
    GastoElectoralCreate,
    GastoElectoralResponse,
    GastoElectoralUpdate,
)
from app.schemas.common import PaginatedResponse
from app.services.blindaje import BlindajeService

router = APIRouter()


# ── Gastos Electorales ───────────────────────────────────────


@router.get("/gastos", response_model=PaginatedResponse[GastoElectoralResponse])
async def list_gastos(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    org_id: int | None = None,
    categoria: CategoriaGastoINE | None = None,
    fecha_inicio: date | None = None,
    fecha_fin: date | None = None,
) -> PaginatedResponse[GastoElectoralResponse]:
    """List gastos electorales with pagination and filtering."""
    query = select(GastoElectoral)
    count_query = select(func.count(GastoElectoral.id))

    if org_id is not None:
        query = query.where(GastoElectoral.org_id == org_id)
        count_query = count_query.where(GastoElectoral.org_id == org_id)
    if categoria is not None:
        query = query.where(GastoElectoral.categoria == categoria)
        count_query = count_query.where(GastoElectoral.categoria == categoria)
    if fecha_inicio is not None:
        query = query.where(GastoElectoral.fecha_gasto >= fecha_inicio)
        count_query = count_query.where(GastoElectoral.fecha_gasto >= fecha_inicio)
    if fecha_fin is not None:
        query = query.where(GastoElectoral.fecha_gasto <= fecha_fin)
        count_query = count_query.where(GastoElectoral.fecha_gasto <= fecha_fin)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = (
        query.order_by(GastoElectoral.fecha_gasto.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    items = list(result.scalars().all())

    return PaginatedResponse(
        items=[GastoElectoralResponse.model_validate(g) for g in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if total > 0 else 0,
    )


@router.post(
    "/gastos",
    response_model=GastoElectoralResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST]))],
)
async def create_gasto(
    payload: GastoElectoralCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GastoElectoral:
    """Create a new gasto electoral record."""
    gasto = GastoElectoral(**payload.model_dump())
    db.add(gasto)
    await db.flush()
    await db.refresh(gasto)
    return gasto


@router.patch(
    "/gastos/{gasto_id}",
    response_model=GastoElectoralResponse,
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST]))],
)
async def update_gasto(
    gasto_id: int,
    payload: GastoElectoralUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GastoElectoral:
    """Update an existing gasto electoral."""
    result = await db.execute(
        select(GastoElectoral).where(GastoElectoral.id == gasto_id)
    )
    gasto = result.scalar_one_or_none()
    if gasto is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gasto electoral not found",
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(gasto, field, value)

    await db.flush()
    await db.refresh(gasto)
    return gasto


@router.patch(
    "/gastos/{gasto_id}/aprobar",
    response_model=GastoElectoralResponse,
    dependencies=[Depends(RoleChecker([Role.ADMIN]))],
)
async def aprobar_gasto(
    gasto_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> GastoElectoral:
    """Approve a gasto electoral. Admin only."""
    result = await db.execute(
        select(GastoElectoral).where(GastoElectoral.id == gasto_id)
    )
    gasto = result.scalar_one_or_none()
    if gasto is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gasto electoral not found",
        )

    gasto.aprobado = True
    gasto.aprobado_por_id = current_user.id

    await db.flush()
    await db.refresh(gasto)
    return gasto


# ── Alertas Compliance ───────────────────────────────────────


@router.get("/alertas", response_model=PaginatedResponse[AlertaComplianceResponse])
async def list_alertas(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    org_id: int | None = None,
    tipo: TipoAlertaCompliance | None = None,
    severidad: SeveridadAlerta | None = None,
    resuelta: bool | None = False,
) -> PaginatedResponse[AlertaComplianceResponse]:
    """List compliance alerts with filtering and pagination."""
    query = select(AlertaCompliance)
    count_query = select(func.count(AlertaCompliance.id))

    if org_id is not None:
        query = query.where(AlertaCompliance.org_id == org_id)
        count_query = count_query.where(AlertaCompliance.org_id == org_id)
    if tipo is not None:
        query = query.where(AlertaCompliance.tipo == tipo)
        count_query = count_query.where(AlertaCompliance.tipo == tipo)
    if severidad is not None:
        query = query.where(AlertaCompliance.severidad == severidad)
        count_query = count_query.where(AlertaCompliance.severidad == severidad)
    if resuelta is not None:
        query = query.where(AlertaCompliance.resuelta == resuelta)
        count_query = count_query.where(AlertaCompliance.resuelta == resuelta)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = (
        query.order_by(AlertaCompliance.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    items = list(result.scalars().all())

    return PaginatedResponse(
        items=[AlertaComplianceResponse.model_validate(a) for a in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if total > 0 else 0,
    )


@router.patch(
    "/alertas/{alerta_id}/resolver",
    response_model=AlertaComplianceResponse,
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST]))],
)
async def resolver_alerta(
    alerta_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AlertaCompliance:
    """Mark a compliance alert as resolved."""
    result = await db.execute(
        select(AlertaCompliance).where(AlertaCompliance.id == alerta_id)
    )
    alerta = result.scalar_one_or_none()
    if alerta is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alerta not found",
        )

    if alerta.resuelta:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Alerta already resolved",
        )

    alerta.resuelta = True
    alerta.resuelta_por_id = current_user.id
    alerta.resuelta_at = datetime.now(UTC)

    await db.flush()
    await db.refresh(alerta)
    return alerta


# ── Audit & Reports ──────────────────────────────────────────


@router.post(
    "/audit",
    response_model=list[AlertaComplianceResponse],
    dependencies=[Depends(RoleChecker([Role.ADMIN]))],
)
async def run_audit(
    db: Annotated[AsyncSession, Depends(get_db)],
    org_id: int = Query(...),
) -> list[AlertaCompliance]:
    """Run a full compliance audit for an organization. Admin only.

    Executes all compliance checks and persists any violations found
    as AlertaCompliance records.
    """
    alertas = await BlindajeService.run_full_audit(db, org_id)
    return alertas


@router.get("/reporte/{org_id}", response_model=ComplianceReportResponse)
async def get_compliance_report(
    org_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
    periodo_inicio: date | None = None,
    periodo_fin: date | None = None,
) -> ComplianceReportResponse:
    """Get a compliance report for an organization.

    Includes spending by SIF category, alert summary, and bot detection stats.
    """
    return await BlindajeService.generate_compliance_report(
        db, org_id, periodo_inicio, periodo_fin
    )


@router.post("/bot-check/{post_id}", response_model=BotAnalysisResult)
async def check_bot(
    post_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
) -> BotAnalysisResult:
    """Check a specific social post for bot-like behavior indicators."""
    result = await db.execute(
        select(SocialPost).where(SocialPost.id == post_id)
    )
    post = result.scalar_one_or_none()
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Social post not found",
        )

    return await BlindajeService.check_bot_indicators(db, post)
