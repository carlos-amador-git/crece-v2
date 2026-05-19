"""Content intelligence endpoints — minimal MVP.

Origen: CEO 2026-05-15 — quiere dashboard de top posts/reels por
dirigente × plataforma para alimentar conversación de plan semanal
con Claude Code + Gemini CLI (proceso manual, no automatizado).

Scope deliberadamente acotado:
- SQL plano sobre `social_posts` JOIN `social_profiles`.
- Sin pipeline ML, sin BERTopic, sin LightGBM. Eso fue descartado por
  CEO como sobre-ingeniería para escala actual (6-10 clientes/mes).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, UTC
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.scope import assert_dirigente_access
from app.core.security import get_current_user
from app.models.social import Platform, SocialPost, SocialProfile
from app.models.user import User
from app.utils.social_urls import compose_post_url

router = APIRouter()


class TopPostItem(BaseModel):
    post_id: int
    platform: str
    handle: str | None
    platform_post_id: str
    url: str | None
    snippet: str  # primeros 200 chars de content
    published_at: datetime
    hour: int  # 0-23, útil para detectar patrón horario
    weekday: int  # 0=lunes 6=domingo
    likes: int
    shares: int
    comments: int
    views: int | None
    engagement_rate: float | None
    sentiment_label: str | None
    target_politico: str | None  # oficialismo|oposicion|propio|personal|no_determinado
    topics: list[str] | None  # extraído de topics_extracted JSONB si está poblado
    media_urls: list[str] | None
    score: float  # valor del campo elegido para ranking, normalizado a float


class TopPostsResponse(BaseModel):
    dirigente_id: int
    window_days: int
    metric: str
    total_candidates: int  # cuántos posts pasaron filtros antes de LIMIT
    items: list[TopPostItem]


_METRIC_COLUMN = {
    "engagement_rate": SocialPost.engagement_rate,
    "likes": SocialPost.likes,
    "shares": SocialPost.shares,
    "comments": SocialPost.comments,
    "views": SocialPost.views,
}


@router.get("/top-posts", response_model=TopPostsResponse)
async def get_top_posts(
    dirigente_id: Annotated[int, Query(description="Dirigente cuyos top posts queremos")],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    platform: str | None = Query(None, description="TWITTER, INSTAGRAM, FACEBOOK, TIKTOK, YOUTUBE"),
    metric: Literal["engagement_rate", "likes", "shares", "comments", "views"] = "engagement_rate",
    window_days: int = Query(90, ge=1, le=365),
    limit: int = Query(20, ge=1, le=50),
) -> TopPostsResponse:
    """Top posts del dirigente ordenados por la métrica elegida en la ventana.

    Scope: enforce assert_dirigente_access. Admin bypass automático.

    Filtros mínimos de calidad:
    - published_at >= NOW() - window_days
    - métrica > 0 (ignora posts sin engagement)
    """
    await assert_dirigente_access(db, current_user, dirigente_id)

    since = datetime.now(UTC) - timedelta(days=window_days)
    metric_col = _METRIC_COLUMN[metric]

    filters = [
        SocialProfile.dirigente_id == dirigente_id,
        SocialPost.published_at >= since,
        metric_col.is_not(None),
        metric_col > 0,
    ]
    if platform:
        try:
            filters.append(SocialProfile.platform == Platform(platform.upper()))
        except ValueError:
            pass

    base = (
        select(SocialPost, SocialProfile)
        .join(SocialProfile, SocialPost.profile_id == SocialProfile.id)
        .where(and_(*filters))
    )

    count_q = (
        select(func.count(SocialPost.id))
        .join(SocialProfile, SocialPost.profile_id == SocialProfile.id)
        .where(and_(*filters))
    )
    total = (await db.execute(count_q)).scalar_one() or 0

    rows = (
        await db.execute(
            base.order_by(metric_col.desc().nulls_last()).limit(limit)
        )
    ).all()

    items: list[TopPostItem] = []
    for post, profile in rows:
        score_raw = getattr(post, metric)
        # topics_extracted en BD es JSONB; soporta varios formatos legacy.
        topics: list[str] | None = None
        if post.topics_extracted:
            if isinstance(post.topics_extracted, dict):
                topics_raw = post.topics_extracted.get("topics") or post.topics_extracted.get("labels")
                if isinstance(topics_raw, list):
                    topics = [str(t) for t in topics_raw][:5]
            elif isinstance(post.topics_extracted, list):
                topics = [str(t) for t in post.topics_extracted][:5]
        items.append(
            TopPostItem(
                post_id=post.id,
                platform=profile.platform.value,
                handle=profile.handle,
                platform_post_id=post.platform_post_id,
                url=compose_post_url(profile.platform, profile.handle, post.platform_post_id),
                snippet=(post.content or "")[:200],
                published_at=post.published_at,
                hour=post.published_at.hour,
                weekday=post.published_at.weekday(),
                likes=post.likes or 0,
                shares=post.shares or 0,
                comments=post.comments or 0,
                views=post.views,
                engagement_rate=float(post.engagement_rate) if post.engagement_rate is not None else None,
                sentiment_label=post.sentiment_label.value if post.sentiment_label else None,
                target_politico=post.target_politico,
                topics=topics,
                media_urls=post.media_urls if post.media_urls else None,
                score=float(score_raw) if score_raw is not None else 0.0,
            )
        )

    return TopPostsResponse(
        dirigente_id=dirigente_id,
        window_days=window_days,
        metric=metric,
        total_candidates=total,
        items=items,
    )
