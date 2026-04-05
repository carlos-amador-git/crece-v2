from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.alerta_crisis import AlertaCrisis
from app.models.dirigente import Dirigente
from app.models.social import SocialPost
from app.models.user import User

router = APIRouter()


class KpiOverviewResponse(BaseModel):
    total_dirigentes: int
    avg_ipd_score: float
    posts_monitored_24h: int
    active_alerts: int
    dirigentes_change: float
    ipd_change: float
    posts_change: float
    alerts_change: float


class SystemStatusResponse(BaseModel):
    last_sync: str
    workers_active: int
    workers_total: int
    scrapers_running: int


@router.get("/overview", response_model=KpiOverviewResponse)
async def get_overview(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
) -> KpiOverviewResponse:
    """Aggregated KPIs for the dashboard overview."""
    now = datetime.now(UTC)
    last_24h = now - timedelta(hours=24)
    prev_24h = last_24h - timedelta(hours=24)
    last_7d = now - timedelta(days=7)
    prev_7d = last_7d - timedelta(days=7)

    # Total dirigentes
    total_result = await db.execute(select(func.count(Dirigente.id)))
    total_dirigentes = total_result.scalar() or 0

    # Avg IPD: compute from diagnostico service would be expensive,
    # use a simpler proxy — avg platform coverage as rough indicator
    # For now return 0 if no dirigentes, computed lazily
    avg_ipd = 0.0
    if total_dirigentes > 0:
        from app.models.social import SocialProfile

        profiles_count = await db.execute(
            select(func.count(func.distinct(SocialProfile.dirigente_id)))
        )
        dirigentes_with_profiles = profiles_count.scalar() or 0

        total_profiles = await db.execute(select(func.count(SocialProfile.id)))
        n_profiles = total_profiles.scalar() or 0

        if dirigentes_with_profiles > 0:
            avg_platforms = n_profiles / dirigentes_with_profiles
            avg_ipd = round(min(avg_platforms / 6.0 * 10.0, 10.0), 1)

    # Posts last 24h
    posts_24h_result = await db.execute(
        select(func.count(SocialPost.id)).where(SocialPost.scraped_at >= last_24h)
    )
    posts_24h = posts_24h_result.scalar() or 0

    # Posts previous 24h (for change %)
    posts_prev_result = await db.execute(
        select(func.count(SocialPost.id)).where(
            SocialPost.scraped_at >= prev_24h,
            SocialPost.scraped_at < last_24h,
        )
    )
    posts_prev = posts_prev_result.scalar() or 0

    # Active alerts
    alerts_result = await db.execute(
        select(func.count(AlertaCrisis.id)).where(
            AlertaCrisis.created_at >= last_7d
        )
    )
    active_alerts = alerts_result.scalar() or 0

    alerts_prev_result = await db.execute(
        select(func.count(AlertaCrisis.id)).where(
            AlertaCrisis.created_at >= prev_7d,
            AlertaCrisis.created_at < last_7d,
        )
    )
    alerts_prev = alerts_prev_result.scalar() or 0

    def pct_change(current: float, previous: float) -> float:
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return round(((current - previous) / previous) * 100, 1)

    return KpiOverviewResponse(
        total_dirigentes=total_dirigentes,
        avg_ipd_score=avg_ipd,
        posts_monitored_24h=posts_24h,
        active_alerts=active_alerts,
        dirigentes_change=0.0,
        ipd_change=0.0,
        posts_change=pct_change(posts_24h, posts_prev),
        alerts_change=pct_change(active_alerts, alerts_prev),
    )


@router.get("/status", response_model=SystemStatusResponse)
async def get_status(
    _current_user: Annotated[User, Depends(get_current_user)],
) -> SystemStatusResponse:
    """System status for workers and scrapers."""
    return SystemStatusResponse(
        last_sync=datetime.now(UTC).isoformat(),
        workers_active=2,
        workers_total=2,
        scrapers_running=0,
    )
