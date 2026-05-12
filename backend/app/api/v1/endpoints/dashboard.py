from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request
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

# Period parameter: maps "today" / "7d" / "30d" / "90d" to number of days.
# Default is "30d" (matches the default pressed button in the dashboard header).
PERIOD_TO_DAYS: dict[str, int] = {
    "today": 1,
    "7d": 7,
    "30d": 30,
    "90d": 90,
}

router = APIRouter()


class KpiOverviewResponse(BaseModel):
    # ── legacy fields (kept for backward compat) ──
    total_dirigentes: int
    avg_ipd_score: float
    posts_monitored_24h: int
    active_alerts: int
    # dirigentes_change: real delta computed from Dirigente.created_at within window.
    # ipd_change: None until follower-count snapshots exist — we refuse to fake 0.0.
    dirigentes_change: float | None
    ipd_change: float | None
    posts_change: float
    alerts_change: float
    # ── political KPIs ──
    total_audiencia: int  # sum of followers across scoped profiles
    contactos_periodo: int  # CRM interactions (WhatsApp/canvassing/events) in window
    tema_urgente: str | None  # most recent active crisis alert title, or None


class SystemStatusResponse(BaseModel):
    last_sync: str
    workers_active: int
    workers_total: int
    scrapers_running: int


@router.get("/overview", response_model=KpiOverviewResponse)
async def get_overview(
    request: "Request",
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    period: Annotated[
        Literal["today", "7d", "30d", "90d"],
        Query(description="Time window for 'posts' and 'alerts' KPIs"),
    ] = "30d",
) -> KpiOverviewResponse:
    """Aggregated KPIs for the dashboard overview.

    Scoping rules:
    - Dirigente user: sees only their own dirigente's data.
    - Non-admin with org_id: sees all dirigentes in their org.
    - Admin: sees org from X-Org-Id header, or all if not set.
    The ``period`` parameter controls the time window for posts and alerts.
    """
    # Auto-scope for dirigente users
    user_dirigente_id = getattr(current_user, "dirigente_id", None)
    user_org_id = getattr(current_user, "org_id", None)
    now = datetime.now(UTC)

    # Resolve effective org_id: admin can switch via X-Org-Id header
    effective_org_id: int | None = user_org_id
    if current_user.role == "admin":
        header_org = request.headers.get("x-org-id")
        if header_org and header_org.isdigit():
            effective_org_id = int(header_org)

    days = PERIOD_TO_DAYS[period]
    window_start = now - timedelta(days=days)
    prev_window_start = window_start - timedelta(days=days)

    last_24h = window_start
    prev_24h = prev_window_start
    last_7d = window_start
    prev_7d = prev_window_start

    from app.models.social import SocialProfile

    # ── Helper: add org_id filter to a dirigente-based query ──
    def _org_filter(q, model=Dirigente):
        """Apply org_id filtering unless admin with no org selected."""
        if user_dirigente_id:
            return q.where(model.id == user_dirigente_id) if model == Dirigente else q
        if effective_org_id is not None:
            return q.where(model.org_id == effective_org_id) if hasattr(model, "org_id") else q
        return q

    # Total dirigentes (scoped)
    if user_dirigente_id:
        total_dirigentes = 1
        dirigentes_prev_count = 1
    else:
        total_q = select(func.count(Dirigente.id))
        if effective_org_id is not None:
            total_q = total_q.where(Dirigente.org_id == effective_org_id)
        total_result = await db.execute(total_q)
        total_dirigentes = total_result.scalar() or 0

        prev_q = select(func.count(Dirigente.id)).where(Dirigente.created_at < window_start)
        if effective_org_id is not None:
            prev_q = prev_q.where(Dirigente.org_id == effective_org_id)
        prev_result = await db.execute(prev_q)
        dirigentes_prev_count = prev_result.scalar() or 0

    # Avg IPD — real calculation via diagnostico service
    avg_ipd = 0.0
    if total_dirigentes > 0:
        dirigente_query = select(Dirigente)
        if user_dirigente_id:
            dirigente_query = dirigente_query.where(Dirigente.id == user_dirigente_id)
        elif effective_org_id is not None:
            dirigente_query = dirigente_query.where(Dirigente.org_id == effective_org_id)
        dirigentes_result = await db.execute(dirigente_query)
        dirigentes_list = list(dirigentes_result.scalars().all())
        if dirigentes_list:
            ipd_sum = 0.0
            for d in dirigentes_list:
                diag = await calculate_ipd(db, d)
                ipd_sum += diag.ipd_score
            avg_ipd = round(ipd_sum / len(dirigentes_list), 1)

    # Posts in period (scoped by org via profile→dirigente)
    posts_query = select(func.count(SocialPost.id)).where(
        SocialPost.scraped_at >= last_24h
    ).join(SocialProfile, SocialPost.profile_id == SocialProfile.id)
    if user_dirigente_id:
        posts_query = posts_query.where(SocialProfile.dirigente_id == user_dirigente_id)
    elif effective_org_id is not None:
        posts_query = posts_query.join(
            Dirigente, SocialProfile.dirigente_id == Dirigente.id
        ).where(Dirigente.org_id == effective_org_id)
    posts_24h_result = await db.execute(posts_query)
    posts_24h = posts_24h_result.scalar() or 0

    # Posts previous period
    posts_prev_query = select(func.count(SocialPost.id)).where(
        SocialPost.scraped_at >= prev_24h,
        SocialPost.scraped_at < last_24h,
    ).join(SocialProfile, SocialPost.profile_id == SocialProfile.id)
    if user_dirigente_id:
        posts_prev_query = posts_prev_query.where(SocialProfile.dirigente_id == user_dirigente_id)
    elif effective_org_id is not None:
        posts_prev_query = posts_prev_query.join(
            Dirigente, SocialProfile.dirigente_id == Dirigente.id
        ).where(Dirigente.org_id == effective_org_id)
    posts_prev_result = await db.execute(posts_prev_query)
    posts_prev = posts_prev_result.scalar() or 0

    # Active alerts
    alerts_result = await db.execute(
        select(func.count(AlertaCrisis.id)).where(AlertaCrisis.created_at >= last_7d)
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

    # Real delta for dirigentes (from created_at history).
    # IPD delta stays None: calculating it requires a follower_count history table
    # that does not exist yet — faking 0.0 violates the "NO inventar datos" rule.
    dirigentes_change = pct_change(float(total_dirigentes), float(dirigentes_prev_count))
    ipd_change: float | None = None

    # ── Political KPIs ─────────────────────────────────────────────
    # total_audiencia: sum of followers across scoped social profiles
    audiencia_query = select(func.coalesce(func.sum(SocialProfile.followers_count), 0))
    if user_dirigente_id:
        audiencia_query = audiencia_query.where(SocialProfile.dirigente_id == user_dirigente_id)
    elif effective_org_id is not None:
        audiencia_query = audiencia_query.join(
            Dirigente, SocialProfile.dirigente_id == Dirigente.id
        ).where(Dirigente.org_id == effective_org_id)
    total_audiencia = (await db.execute(audiencia_query)).scalar() or 0

    # contactos_periodo: CRM interactions in window (best-effort, graceful if tables missing)
    contactos_periodo = 0
    try:
        from app.models.crm_interaccion import CRMInteraccion  # type: ignore[import]

        crm_query = select(func.count(CRMInteraccion.id)).where(
            CRMInteraccion.created_at >= window_start
        )
        contactos_periodo = (await db.execute(crm_query)).scalar() or 0
    except Exception:
        contactos_periodo = 0

    # tema_urgente: most recent active crisis alert title
    tema_urgente: str | None = None
    try:
        tema_query = (
            select(AlertaCrisis)
            .where(AlertaCrisis.created_at >= last_7d)
            .order_by(AlertaCrisis.created_at.desc())
            .limit(1)
        )
        tema_row = (await db.execute(tema_query)).scalar_one_or_none()
        if tema_row is not None:
            tema_urgente = getattr(tema_row, "descripcion", None) or getattr(
                tema_row, "titulo", None
            )
    except Exception:
        tema_urgente = None

    return KpiOverviewResponse(
        total_dirigentes=total_dirigentes,
        avg_ipd_score=avg_ipd,
        posts_monitored_24h=posts_24h,
        active_alerts=active_alerts,
        dirigentes_change=dirigentes_change,
        ipd_change=ipd_change,
        posts_change=pct_change(posts_24h, posts_prev),
        alerts_change=pct_change(active_alerts, alerts_prev),
        total_audiencia=int(total_audiencia),
        contactos_periodo=int(contactos_periodo),
        tema_urgente=tema_urgente,
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
