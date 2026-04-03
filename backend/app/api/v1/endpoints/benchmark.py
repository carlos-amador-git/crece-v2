from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import Role, RoleChecker, get_current_user
from app.models.benchmark import Competidor, CompetidorSocialProfile
from app.models.user import User
from app.schemas.benchmark import (
    CompetidorCreate,
    CompetidorResponse,
    CompetidorUpdate,
    RankingEntry,
    RankingResponse,
)
from app.schemas.common import PaginatedResponse

router = APIRouter()


@router.get("/competidores", response_model=PaginatedResponse[CompetidorResponse])
async def list_competidores(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    partido: str | None = None,
    es_rival: bool | None = None,
) -> PaginatedResponse[CompetidorResponse]:
    """List competidores with filtering and pagination."""
    query = select(Competidor)
    count_query = select(func.count(Competidor.id))

    if partido:
        query = query.where(Competidor.partido == partido)
        count_query = count_query.where(Competidor.partido == partido)
    if es_rival is not None:
        query = query.where(Competidor.es_rival == es_rival)
        count_query = count_query.where(Competidor.es_rival == es_rival)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(Competidor.nombre).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = list(result.scalars().all())

    return PaginatedResponse(
        items=[CompetidorResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if total > 0 else 0,
    )


@router.get("/competidores/{competidor_id}", response_model=CompetidorResponse)
async def get_competidor(
    competidor_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
) -> Competidor:
    result = await db.execute(select(Competidor).where(Competidor.id == competidor_id))
    competidor = result.scalar_one_or_none()
    if competidor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Competidor not found")
    return competidor


@router.post(
    "/competidores",
    response_model=CompetidorResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST]))],
)
async def create_competidor(
    payload: CompetidorCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Competidor:
    competidor = Competidor(**payload.model_dump())
    db.add(competidor)
    await db.flush()
    await db.refresh(competidor)
    return competidor


@router.patch(
    "/competidores/{competidor_id}",
    response_model=CompetidorResponse,
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST]))],
)
async def update_competidor(
    competidor_id: int,
    payload: CompetidorUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Competidor:
    result = await db.execute(select(Competidor).where(Competidor.id == competidor_id))
    competidor = result.scalar_one_or_none()
    if competidor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Competidor not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(competidor, field, value)

    await db.flush()
    await db.refresh(competidor)
    return competidor


@router.delete(
    "/competidores/{competidor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RoleChecker([Role.ADMIN]))],
)
async def delete_competidor(
    competidor_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    result = await db.execute(select(Competidor).where(Competidor.id == competidor_id))
    competidor = result.scalar_one_or_none()
    if competidor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Competidor not found")
    await db.delete(competidor)


@router.get("/ranking", response_model=RankingResponse)
async def get_ranking(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
) -> RankingResponse:
    """Get a comparative ranking of all competidores by social media metrics."""
    result = await db.execute(
        select(
            Competidor.nombre,
            Competidor.partido,
            func.coalesce(func.sum(CompetidorSocialProfile.followers_count), 0).label(
                "total_followers"
            ),
            func.count(CompetidorSocialProfile.id).label("platform_count"),
        )
        .outerjoin(CompetidorSocialProfile)
        .group_by(Competidor.id, Competidor.nombre, Competidor.partido)
        .order_by(func.sum(CompetidorSocialProfile.followers_count).desc().nulls_last())
    )
    rows = result.all()

    entries = []
    for row in rows:
        total_followers = int(row.total_followers)
        platform_count = int(row.platform_count)
        # Simple IPD approximation for ranking
        coverage = platform_count / 6.0
        follower_score = min(total_followers / 100_000, 1.0) * 10.0
        ipd = follower_score * 0.6 + coverage * 10.0 * 0.4
        entries.append(
            RankingEntry(
                nombre=row.nombre,
                partido=row.partido,
                total_followers=total_followers,
                avg_engagement=0.0,  # would need posts table for competidores
                platform_count=platform_count,
                ipd_score=round(min(ipd, 10.0), 2),
            )
        )

    return RankingResponse(
        entries=entries,
        generated_at=datetime.now(UTC).isoformat(),
    )
