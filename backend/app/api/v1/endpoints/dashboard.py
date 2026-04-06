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
from app.services.diagnostico import calculate_ipd

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
    current_user: Annotated[User, Depends(get_current_user)],
) -> KpiOverviewResponse:
    """Aggregated KPIs for the dashboard overview.

    If the user has a dirigente_id, scopes data to their dirigente only.
    """
    # Auto-scope for dirigente users
    user_dirigente_id = getattr(current_user, "dirigente_id", None)
    now = datetime.now(UTC)
    last_24h = now - timedelta(hours=24)
    prev_24h = last_24h - timedelta(hours=24)
    last_7d = now - timedelta(days=7)
    prev_7d = last_7d - timedelta(days=7)

    from app.models.social import SocialProfile

    # Total dirigentes (scoped if user is a dirigente)
    if user_dirigente_id:
        total_dirigentes = 1
    else:
        total_result = await db.execute(select(func.count(Dirigente.id)))
        total_dirigentes = total_result.scalar() or 0

    # Avg IPD — real calculation via diagnostico service
    avg_ipd = 0.0
    if total_dirigentes > 0:
        dirigente_query = select(Dirigente)
        if user_dirigente_id:
            dirigente_query = dirigente_query.where(Dirigente.id == user_dirigente_id)
        dirigentes_result = await db.execute(dirigente_query)
        dirigentes_list = list(dirigentes_result.scalars().all())
        if dirigentes_list:
            ipd_sum = 0.0
            for d in dirigentes_list:
                diag = await calculate_ipd(db, d)
                ipd_sum += diag.ipd_score
            avg_ipd = round(ipd_sum / len(dirigentes_list), 1)

    # Posts last 24h (scoped)
    posts_query = select(func.count(SocialPost.id)).where(SocialPost.scraped_at >= last_24h)
    if user_dirigente_id:
        posts_query = posts_query.join(SocialProfile, SocialPost.profile_id == SocialProfile.id).where(
            SocialProfile.dirigente_id == user_dirigente_id
        )
    posts_24h_result = await db.execute(posts_query)
    posts_24h = posts_24h_result.scalar() or 0

    # Posts previous 24h
    posts_prev_query = select(func.count(SocialPost.id)).where(
        SocialPost.scraped_at >= prev_24h,
        SocialPost.scraped_at < last_24h,
    )
    if user_dirigente_id:
        posts_prev_query = posts_prev_query.join(SocialProfile, SocialPost.profile_id == SocialProfile.id).where(
            SocialProfile.dirigente_id == user_dirigente_id
        )
    posts_prev_result = await db.execute(posts_prev_query)
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
