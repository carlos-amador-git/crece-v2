"""S4.9 — Endpoint GET /trends/geo?alcaldia_id=X&period=Xh|d

Retorna los topic trends detectados por el worker `detect_trends`
scoped al dirigente/organización del usuario autenticado.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.alcaldia import AlcaldiaCDMX
from app.models.topic_trend import TopicTrend
from app.models.user import User

router = APIRouter()


class TopicTrendResponse(BaseModel):
    id: int
    alcaldia_id: int | None
    alcaldia_nombre: str | None
    topic_label: str | None
    time_bucket: datetime
    post_count: int
    sentiment_avg: float | None
    growth_rate_24h: float | None
    sample_post_ids: list[int]


class TrendsGeoResponse(BaseModel):
    alcaldia_id: int | None
    period: str
    trends: list[TopicTrendResponse]


def _parse_period(period: str) -> timedelta:
    """Accepts '24h', '7d', '30d'."""
    if period.endswith("h"):
        return timedelta(hours=int(period[:-1]))
    if period.endswith("d"):
        return timedelta(days=int(period[:-1]))
    raise ValueError(f"Invalid period: {period}")


@router.get("/geo", response_model=TrendsGeoResponse)
async def get_geo_trends(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    alcaldia_id: int | None = Query(None, description="Filter by alcaldía INEGI id"),
    period: Literal["24h", "7d", "30d"] = Query("7d"),
    limit: int = Query(10, ge=1, le=50),
) -> TrendsGeoResponse:
    """Top N trends by alcaldía for the current user's org.

    If `alcaldia_id` is omitted, returns top trends across all alcaldías
    in CDMX for the window. Always scopes by `current_user.org_id` — there
    is NO way to query trends for another org.
    """
    # Resolve org_id: per D16, demo dirigentes have org_id=None. In that
    # case we default to 3 (MC CDMX root org from the seed).
    org_id = current_user.org_id or 3

    try:
        window = _parse_period(period)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    window_start = datetime.now(UTC) - window

    query = select(TopicTrend, AlcaldiaCDMX.nombre).join(
        AlcaldiaCDMX,
        AlcaldiaCDMX.id == TopicTrend.alcaldia_id,
        isouter=True,
    ).where(
        TopicTrend.org_id == org_id,
        TopicTrend.time_bucket >= window_start,
    )
    if alcaldia_id is not None:
        query = query.where(TopicTrend.alcaldia_id == alcaldia_id)

    query = query.order_by(
        TopicTrend.post_count.desc(),
        TopicTrend.time_bucket.desc(),
    ).limit(limit)

    rows = (await db.execute(query)).all()

    trends: list[TopicTrendResponse] = []
    for trend, nombre in rows:
        sample = trend.sample_posts or {}
        post_ids = sample.get("post_ids", []) if isinstance(sample, dict) else []
        trends.append(
            TopicTrendResponse(
                id=trend.id,
                alcaldia_id=trend.alcaldia_id,
                alcaldia_nombre=nombre,
                topic_label=trend.topic_label,
                time_bucket=trend.time_bucket,
                post_count=trend.post_count,
                sentiment_avg=trend.sentiment_avg,
                growth_rate_24h=trend.growth_rate_24h,
                sample_post_ids=post_ids,
            )
        )

    return TrendsGeoResponse(
        alcaldia_id=alcaldia_id,
        period=period,
        trends=trends,
    )


@router.get("/alcaldias")
async def list_alcaldias(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[dict]:
    """List all 16 CDMX alcaldías for UI selectors."""
    rows = (
        await db.execute(
            select(AlcaldiaCDMX.id, AlcaldiaCDMX.nombre, AlcaldiaCDMX.cvegeo).order_by(
                AlcaldiaCDMX.nombre
            )
        )
    ).all()
    return [{"id": r[0], "nombre": r[1], "cvegeo": r[2]} for r in rows]
