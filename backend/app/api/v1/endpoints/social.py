from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import Date

from app.core.database import get_db
from app.core.security import Role, RoleChecker, get_current_user
from app.models.social import Platform, SentimentLabel, SocialPost, SocialProfile
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.social import (
    ScrapeRequest,
    SentimentTimelinePoint,
    SocialPostResponse,
)
from app.services.scraper_manager import dispatch_scrape

router = APIRouter()


@router.get("/posts", response_model=PaginatedResponse[SocialPostResponse])
async def list_posts(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
    dirigente_id: int | None = None,
    platform: str | None = None,
    sentiment: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    is_political: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[SocialPostResponse]:
    """List social posts with comprehensive filtering."""
    query = select(SocialPost).join(SocialProfile, SocialPost.profile_id == SocialProfile.id)
    count_query = (
        select(func.count(SocialPost.id))
        .join(SocialProfile, SocialPost.profile_id == SocialProfile.id)
    )

    # Normalize case-insensitive enum params
    platform_enum = Platform(platform.upper()) if platform else None
    sentiment_enum = SentimentLabel(sentiment.upper()) if sentiment else None

    filters = []
    if dirigente_id is not None:
        filters.append(SocialProfile.dirigente_id == dirigente_id)
    if platform_enum is not None:
        filters.append(SocialProfile.platform == platform_enum)
    if sentiment_enum is not None:
        filters.append(SocialPost.sentiment_label == sentiment_enum)
    if date_from is not None:
        filters.append(SocialPost.published_at >= date_from)
    if date_to is not None:
        filters.append(SocialPost.published_at <= date_to)
    if is_political is not None:
        filters.append(SocialPost.is_political == is_political)

    if filters:
        condition = and_(*filters)
        query = query.where(condition)
        count_query = count_query.where(condition)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = (
        query.order_by(SocialPost.published_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    items = list(result.scalars().all())

    return PaginatedResponse(
        items=[SocialPostResponse.model_validate(p) for p in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if total > 0 else 0,
    )


@router.get("/sentiment-timeline", response_model=list[SentimentTimelinePoint])
async def sentiment_timeline(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
    dirigente_id: int,
    platform: Platform | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[SentimentTimelinePoint]:
    """Get sentiment time series data grouped by day."""
    day_col = cast(SocialPost.published_at, Date)

    base_query = (
        select(
            day_col.label("day"),
            func.avg(SocialPost.sentiment_score).label("avg_sentiment"),
            func.count(SocialPost.id).label("post_count"),
            func.count()
            .filter(SocialPost.sentiment_label == SentimentLabel.POSITIVE)
            .label("positive"),
            func.count()
            .filter(SocialPost.sentiment_label == SentimentLabel.NEGATIVE)
            .label("negative"),
            func.count()
            .filter(SocialPost.sentiment_label == SentimentLabel.NEUTRAL)
            .label("neutral"),
        )
        .join(SocialProfile, SocialPost.profile_id == SocialProfile.id)
        .where(
            SocialProfile.dirigente_id == dirigente_id,
            SocialPost.sentiment_score.is_not(None),
        )
    )

    if platform is not None:
        base_query = base_query.where(SocialProfile.platform == platform)
    if date_from is not None:
        base_query = base_query.where(SocialPost.published_at >= date_from)
    if date_to is not None:
        base_query = base_query.where(SocialPost.published_at <= date_to)

    base_query = base_query.group_by(day_col).order_by(day_col)

    result = await db.execute(base_query)
    rows = result.all()

    timeline = []
    for row in rows:
        total = row.post_count or 1
        timeline.append(
            SentimentTimelinePoint(
                date=row.day.isoformat(),
                avg_sentiment=round(float(row.avg_sentiment or 0), 4),
                post_count=row.post_count,
                positive_pct=round(row.positive / total * 100, 1),
                negative_pct=round(row.negative / total * 100, 1),
                neutral_pct=round(row.neutral / total * 100, 1),
            )
        )
    return timeline


@router.post(
    "/scrape/{dirigente_id}",
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST]))],
)
async def trigger_scrape(
    dirigente_id: int,
    payload: ScrapeRequest | None = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,  # type: ignore[assignment]
) -> dict:
    """Trigger scraping tasks for a dirigente's social profiles."""
    platforms = payload.platforms if payload else None
    dispatched = await dispatch_scrape(db, dirigente_id, platforms)

    if not dispatched:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No social profiles found for this dirigente",
        )

    return {"status": "dispatched", "tasks": dispatched}
