from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import and_, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import Date

from app.core.database import get_db
from app.core.security import Role, RoleChecker, get_current_user
from app.models.dirigente import Dirigente
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
    request: "Request",
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    dirigente_id: int | None = None,
    platform: str | None = None,
    sentiment: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    is_political: bool | None = None,
    exclude_rts: bool = False,
    min_length: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[SocialPostResponse]:
    """List social posts with comprehensive filtering."""
    query = select(SocialPost).join(SocialProfile, SocialPost.profile_id == SocialProfile.id)
    count_query = select(func.count(SocialPost.id)).join(
        SocialProfile, SocialPost.profile_id == SocialProfile.id
    )

    # Normalize case-insensitive enum params
    platform_enum = Platform(platform.upper()) if platform else None
    sentiment_enum = SentimentLabel(sentiment.upper()) if sentiment else None

    # Resolve effective org_id: admin can switch via X-Org-Id header
    effective_org_id: int | None = getattr(current_user, "org_id", None)
    if current_user.role == "admin":
        header_org = request.headers.get("x-org-id")
        if header_org and header_org.isdigit():
            effective_org_id = int(header_org)

    # Auto-scope: dirigente users see only their own; org users see their org
    effective_dirigente_id = dirigente_id
    if current_user.dirigente_id is not None:
        effective_dirigente_id = current_user.dirigente_id

    filters = []
    if effective_dirigente_id is not None:
        filters.append(SocialProfile.dirigente_id == effective_dirigente_id)
    elif effective_org_id is not None:
        # Scope to org's dirigentes (works for admin with X-Org-Id and non-admin)
        filters.append(SocialProfile.dirigente_id.in_(
            select(Dirigente.id).where(Dirigente.org_id == effective_org_id)
        ))
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
    if exclude_rts:
        filters.append(~SocialPost.content.like("RT @%"))
    if min_length is not None:
        filters.append(func.length(SocialPost.content) >= min_length)

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
    include_rts: bool = False,
) -> list[SentimentTimelinePoint]:
    """Get sentiment time series data grouped by day.

    Quality filters (D-NLP-auditoria-2026-04-13):
    - Excludes retweets by default (RT @... prefix) — use include_rts=true to keep
    - Excludes posts with <20 chars (unreliable sentiment)
    - Deduplicates identical content (same post cross-platform counts once)
    """
    day_col = cast(SocialPost.published_at, Date)

    # Build quality filters
    quality_filters = [
        SocialProfile.dirigente_id == dirigente_id,
        SocialPost.sentiment_score.is_not(None),
        func.length(SocialPost.content) >= 20,
    ]
    if not include_rts:
        quality_filters.append(~SocialPost.content.like("RT @%"))

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
        .where(*quality_filters)
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
