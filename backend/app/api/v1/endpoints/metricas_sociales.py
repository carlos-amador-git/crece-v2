from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import Role, RoleChecker, get_current_user
from app.models.metrica_social import MetricaSocial
from app.models.user import User
from app.schemas.metrica_social import (
    MetricaSocialCreate,
    MetricaSocialResponse,
    MetricaSocialTrend,
)

router = APIRouter()


@router.get("/by-profile/{profile_id}", response_model=list[MetricaSocialResponse])
async def list_metricas_by_profile(
    profile_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(50, ge=1, le=500),
) -> list[MetricaSocial]:
    """List metric snapshots for a social profile, ordered by captured_at desc."""
    query = (
        select(MetricaSocial)
        .where(MetricaSocial.profile_id == profile_id)
        .order_by(MetricaSocial.captured_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/trends/{profile_id}", response_model=list[MetricaSocialTrend])
async def trends_by_profile(
    profile_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(90, ge=1, le=365),
) -> list[MetricaSocialTrend]:
    """Return time series data for chart rendering, ordered chronologically."""
    query = (
        select(MetricaSocial)
        .where(MetricaSocial.profile_id == profile_id)
        .order_by(MetricaSocial.captured_at.asc())
        .limit(limit)
    )
    result = await db.execute(query)
    snapshots = list(result.scalars().all())

    return [
        MetricaSocialTrend(
            captured_at=s.captured_at,
            followers_count=s.followers_count,
            following_count=s.following_count,
            posts_count=s.posts_count,
            engagement_rate_avg=s.engagement_rate_avg,
            followers_delta=s.followers_delta,
            posts_delta=s.posts_delta,
        )
        for s in snapshots
    ]


@router.post(
    "/",
    response_model=MetricaSocialResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST]))],
)
async def create_metrica(
    payload: MetricaSocialCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MetricaSocial:
    """Create a new social metrics snapshot. Usually called by Celery worker."""
    metrica = MetricaSocial(**payload.model_dump())
    db.add(metrica)
    await db.flush()
    await db.refresh(metrica)
    return metrica
