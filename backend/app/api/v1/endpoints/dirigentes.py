from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import Role, RoleChecker, get_current_user
from app.models.dirigente import Dirigente
from app.models.social import SentimentLabel, SocialPost, SocialProfile
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.dirigente import (
    DiagnosticoResponse,
    DirigenteCreate,
    DirigenteResponse,
    DirigenteUpdate,
    SocialSummary,
)
from app.services.diagnostico import calculate_ipd

router = APIRouter()


@router.get("/")
async def list_dirigentes(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    estado: str | None = None,
    partido: str | None = None,
    search: str | None = None,
) -> dict:
    """List dirigentes with IPD scores and platform counts.

    If user has dirigente_id, only show their own dirigente.
    """
    query = select(Dirigente)
    count_query = select(func.count(Dirigente.id))

    # Auto-scope for dirigente users
    if current_user.dirigente_id is not None:
        query = query.where(Dirigente.id == current_user.dirigente_id)
        count_query = count_query.where(Dirigente.id == current_user.dirigente_id)

    if estado:
        query = query.where(Dirigente.estado == estado)
        count_query = count_query.where(Dirigente.estado == estado)
    if partido:
        query = query.where(Dirigente.partido == partido)
        count_query = count_query.where(Dirigente.partido == partido)
    if search:
        query = query.where(Dirigente.full_name.ilike(f"%{search}%"))
        count_query = count_query.where(Dirigente.full_name.ilike(f"%{search}%"))

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(Dirigente.full_name).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = list(result.scalars().all())

    # Enrich each dirigente with IPD and platform count
    enriched = []
    for d in items:
        base = DirigenteResponse.model_validate(d).model_dump()
        try:
            ipd = await calculate_ipd(db, d)
            base["ipd_score"] = ipd.ipd_score
            base["platform_coverage"] = ipd.platform_coverage
        except Exception:
            base["ipd_score"] = 0.0
            base["platform_coverage"] = 0.0

        # Platform count
        prof_r = await db.execute(
            select(func.count(SocialProfile.id)).where(SocialProfile.dirigente_id == d.id)
        )
        base["platform_count"] = prof_r.scalar_one()
        enriched.append(base)

    return {
        "items": enriched,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if total > 0 else 0,
    }


@router.get("/{dirigente_id}")
async def get_dirigente(
    dirigente_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Get a single dirigente by ID with enriched data for the dashboard."""
    from datetime import UTC, datetime, timedelta

    result = await db.execute(select(Dirigente).where(Dirigente.id == dirigente_id))
    dirigente = result.scalar_one_or_none()
    if dirigente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dirigente not found")

    # Base response
    base = DirigenteResponse.model_validate(dirigente).model_dump()

    # Enrich: IPD breakdown from diagnostico
    try:
        ipd = await calculate_ipd(db, dirigente)
        base["ipd_score"] = ipd.ipd_score
        base["ipd_breakdown"] = ipd.platform_scores
    except Exception:
        base["ipd_score"] = 0.0
        base["ipd_breakdown"] = {}

    # Enrich: stats (7d)
    seven_days_ago = datetime.now(UTC) - timedelta(days=7)
    thirty_days_ago = datetime.now(UTC) - timedelta(days=30)

    profiles_result = await db.execute(
        select(SocialProfile).where(SocialProfile.dirigente_id == dirigente_id)
    )
    profiles = list(profiles_result.scalars().all())
    profile_ids = [p.id for p in profiles]

    total_posts_7d = 0
    total_engagement_7d = 0.0
    sentiment_sum = 0.0
    sentiment_count = 0

    if profile_ids:
        stats_r = await db.execute(
            select(
                func.count(SocialPost.id),
                func.avg(SocialPost.engagement_rate),
                func.avg(SocialPost.sentiment_score),
            ).where(
                SocialPost.profile_id.in_(profile_ids),
                SocialPost.published_at >= seven_days_ago,
            )
        )
        row = stats_r.one()
        total_posts_7d = int(row[0])
        total_engagement_7d = float(row[1]) if row[1] else 0.0
        sentiment_sum = float(row[2]) if row[2] else 0.5
        sentiment_count = int(row[0])

    total_followers = sum(p.followers_count for p in profiles)

    base["stats"] = {
        "total_posts_7d": total_posts_7d,
        "total_engagement_7d": round(total_engagement_7d, 4),
        "sentiment_avg_7d": round(sentiment_sum, 2),
        "follower_growth_30d": 0,  # Would need historical data
    }

    # Enrich: social_accounts (what frontend expects)
    base["social_accounts"] = [
        {
            "platform": p.platform.value.lower(),
            "handle": p.handle,
            "followers": p.followers_count,
            "url": p.url,
        }
        for p in profiles
    ]

    # Enrich: recent_posts
    if profile_ids:
        posts_r = await db.execute(
            select(SocialPost)
            .where(SocialPost.profile_id.in_(profile_ids))
            .order_by(SocialPost.published_at.desc())
            .limit(10)
        )
        posts = list(posts_r.scalars().all())
        base["recent_posts"] = [
            {
                "id": post.id,
                "content": post.content,
                "platform": next(
                    (p.platform.value.lower() for p in profiles if p.id == post.profile_id),
                    "unknown",
                ),
                "published_at": post.published_at.isoformat() if post.published_at else None,
                "likes": post.likes,
                "comments": post.comments,
                "shares": post.shares,
                "engagement_rate": post.engagement_rate,
                "sentiment_score": post.sentiment_score,
                "sentiment_label": post.sentiment_label.value if post.sentiment_label else None,
            }
            for post in posts
        ]
    else:
        base["recent_posts"] = []

    base["secciones"] = []

    return base


@router.post(
    "/",
    response_model=DirigenteResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST]))],
)
async def create_dirigente(
    payload: DirigenteCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Dirigente:
    """Create a new dirigente."""
    dirigente = Dirigente(**payload.model_dump())
    db.add(dirigente)
    await db.flush()
    await db.refresh(dirigente)
    return dirigente


@router.patch(
    "/{dirigente_id}",
    response_model=DirigenteResponse,
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST]))],
)
async def update_dirigente(
    dirigente_id: int,
    payload: DirigenteUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Dirigente:
    """Update an existing dirigente."""
    result = await db.execute(select(Dirigente).where(Dirigente.id == dirigente_id))
    dirigente = result.scalar_one_or_none()
    if dirigente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dirigente not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(dirigente, field, value)

    await db.flush()
    await db.refresh(dirigente)
    return dirigente


@router.delete(
    "/{dirigente_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RoleChecker([Role.ADMIN]))],
)
async def delete_dirigente(
    dirigente_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a dirigente and all related data."""
    result = await db.execute(select(Dirigente).where(Dirigente.id == dirigente_id))
    dirigente = result.scalar_one_or_none()
    if dirigente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dirigente not found")
    await db.delete(dirigente)


@router.get("/{dirigente_id}/diagnostico", response_model=DiagnosticoResponse)
async def get_diagnostico(
    dirigente_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
) -> DiagnosticoResponse:
    """Get the aggregated digital penetration index (IPD) for a dirigente."""
    result = await db.execute(select(Dirigente).where(Dirigente.id == dirigente_id))
    dirigente = result.scalar_one_or_none()
    if dirigente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dirigente not found")
    return await calculate_ipd(db, dirigente)


@router.get("/{dirigente_id}/social-summary", response_model=SocialSummary)
async def get_social_summary(
    dirigente_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
) -> SocialSummary:
    """Get a social media summary for a dirigente across all platforms."""
    result = await db.execute(select(Dirigente).where(Dirigente.id == dirigente_id))
    dirigente = result.scalar_one_or_none()
    if dirigente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dirigente not found")

    profiles_result = await db.execute(
        select(SocialProfile).where(SocialProfile.dirigente_id == dirigente_id)
    )
    profiles = list(profiles_result.scalars().all())

    total_followers = sum(p.followers_count for p in profiles)
    total_posts = sum(p.posts_count for p in profiles)

    # Average engagement across all recent posts
    eng_result = await db.execute(
        select(func.avg(SocialPost.engagement_rate))
        .join(SocialProfile, SocialPost.profile_id == SocialProfile.id)
        .where(SocialProfile.dirigente_id == dirigente_id)
    )
    avg_engagement = float(eng_result.scalar_one() or 0.0)

    # Sentiment breakdown
    sent_result = await db.execute(
        select(SocialPost.sentiment_label, func.count(SocialPost.id))
        .join(SocialProfile, SocialPost.profile_id == SocialProfile.id)
        .where(
            SocialProfile.dirigente_id == dirigente_id,
            SocialPost.sentiment_label.is_not(None),
        )
        .group_by(SocialPost.sentiment_label)
    )
    sentiment_rows = sent_result.all()
    total_sentiment = sum(row[1] for row in sentiment_rows) or 1
    sentiment_breakdown = {
        row[0].value: round(row[1] / total_sentiment, 4) for row in sentiment_rows
    }

    # Top platforms by followers
    top_platforms = sorted(
        [
            {
                "platform": p.platform.value,
                "followers": p.followers_count,
                "posts": p.posts_count,
            }
            for p in profiles
        ],
        key=lambda x: x["followers"],
        reverse=True,
    )

    return SocialSummary(
        dirigente_id=dirigente_id,
        total_followers=total_followers,
        total_posts=total_posts,
        avg_engagement=round(avg_engagement, 4),
        sentiment_breakdown=sentiment_breakdown,
        top_platforms=top_platforms,
    )
