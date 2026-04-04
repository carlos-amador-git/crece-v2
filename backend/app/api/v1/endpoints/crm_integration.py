from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_or_api_key
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.integration import (
    InteraccionCreateRequest,
    InteraccionResponse,
    VoterScoreResponse,
)

router = APIRouter()


@router.post(
    "/interactions",
    response_model=InteraccionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_interaction(
    payload: InteraccionCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user_or_api_key)],
) -> InteraccionResponse:
    """Create a CRM interaction record."""
    from app.models.crm_interaccion import CrmInteraccion

    interaccion = CrmInteraccion(
        ciudadano_id=payload.ciudadano_id,
        tipo=payload.tipo,
        canal=payload.canal,
        resultado=payload.resultado,
        notas=payload.notas,
        referencia_tipo=payload.referencia_tipo,
        referencia_id=payload.referencia_id,
        registrado_por_id=current_user.id,
        org_id=current_user.org_id,
    )
    db.add(interaccion)
    await db.flush()
    await db.refresh(interaccion)

    return InteraccionResponse.model_validate(interaccion)


@router.get("/interactions", response_model=PaginatedResponse[InteraccionResponse])
async def list_interactions(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user_or_api_key)],
    ciudadano_id: int | None = None,
    tipo: str | None = None,
    canal: str | None = None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[InteraccionResponse]:
    """List CRM interactions with filters."""
    from app.models.crm_interaccion import CrmInteraccion

    query = select(CrmInteraccion).where(CrmInteraccion.org_id == current_user.org_id)
    count_query = select(func.count(CrmInteraccion.id)).where(
        CrmInteraccion.org_id == current_user.org_id
    )

    if ciudadano_id is not None:
        query = query.where(CrmInteraccion.ciudadano_id == ciudadano_id)
        count_query = count_query.where(CrmInteraccion.ciudadano_id == ciudadano_id)
    if tipo:
        query = query.where(CrmInteraccion.tipo == tipo)
        count_query = count_query.where(CrmInteraccion.tipo == tipo)
    if canal:
        query = query.where(CrmInteraccion.canal == canal)
        count_query = count_query.where(CrmInteraccion.canal == canal)
    if desde:
        query = query.where(CrmInteraccion.created_at >= desde)
        count_query = count_query.where(CrmInteraccion.created_at >= desde)
    if hasta:
        query = query.where(CrmInteraccion.created_at <= hasta)
        count_query = count_query.where(CrmInteraccion.created_at <= hasta)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = (
        query.order_by(CrmInteraccion.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    items = list(result.scalars().all())

    return PaginatedResponse(
        items=[InteraccionResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if total > 0 else 0,
    )


@router.get("/scores/{ciudadano_id}", response_model=VoterScoreResponse)
async def get_voter_score(
    ciudadano_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user_or_api_key)],
) -> VoterScoreResponse:
    """Get the voter score for a specific ciudadano. 404 if not calculated."""
    from app.models.voter_score_integration import VoterScoreIntegration

    result = await db.execute(
        select(VoterScoreIntegration).where(
            VoterScoreIntegration.ciudadano_id == ciudadano_id
        )
    )
    score = result.scalar_one_or_none()
    if score is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Voter score not calculated for ciudadano {ciudadano_id}",
        )

    return VoterScoreResponse.model_validate(score)


@router.get("/scores", response_model=PaginatedResponse[VoterScoreResponse])
async def list_voter_scores(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user_or_api_key)],
    score_favorable_min: float | None = None,
    score_persuadible_min: float | None = None,
    order_by: str = "score_favorable",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[VoterScoreResponse]:
    """List voter scores with optional minimum filters and ordering."""
    from app.models.voter_score_integration import VoterScoreIntegration

    query = select(VoterScoreIntegration)
    count_query = select(func.count(VoterScoreIntegration.id))

    if score_favorable_min is not None:
        query = query.where(
            VoterScoreIntegration.score_favorable >= score_favorable_min
        )
        count_query = count_query.where(
            VoterScoreIntegration.score_favorable >= score_favorable_min
        )
    if score_persuadible_min is not None:
        query = query.where(
            VoterScoreIntegration.score_persuadible >= score_persuadible_min
        )
        count_query = count_query.where(
            VoterScoreIntegration.score_persuadible >= score_persuadible_min
        )

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Dynamic ordering
    order_col = getattr(VoterScoreIntegration, order_by, None)
    if order_col is None:
        order_col = VoterScoreIntegration.score_favorable
    query = query.order_by(order_col.desc()).offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    items = list(result.scalars().all())

    return PaginatedResponse(
        items=[VoterScoreResponse.model_validate(s) for s in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if total > 0 else 0,
    )
