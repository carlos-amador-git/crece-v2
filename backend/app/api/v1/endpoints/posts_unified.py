"""Endpoint /api/v1/posts/unified · Content Hub F4 · 2026-05-19

BFF (Backend-For-Frontend) que consolida 4 vistas heterogéneas de posts:
- feed: posts recientes del dirigente (=useSocialPosts actual)
- comentarios: posts con top quotes embebidas (NLP polaridad)
- top: ranking por engagement_rate (=useTopPosts actual)
- fans: posts con reactors_capturados RADAR

View handlers SEPARADOS internamente (per Gemini anti-patrón "God Endpoint":
tolerable solo si capa BFF con aislamiento absoluto en controladores
de dominio subyacentes).
"""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import Date, cast, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.limiter import limiter
from app.core.scope import assert_dirigente_access
from app.core.security import get_current_user
from app.models.social import SocialPost, SocialProfile
from app.models.user import User
from app.schemas.posts_unified import (
    PostComentariosItem,
    PostFansItem,
    PostFeedItem,
    PostTopItem,
    PostsUnifiedResponse,
    QuoteSample,
)

router = APIRouter()


async def _view_feed(
    db: AsyncSession,
    dirigente_id: int,
    platform: str | None,
    date_from: date | None,
    date_to: date | None,
    page: int,
    per_page: int,
) -> tuple[list[PostFeedItem], int]:
    """Vista feed · posts recientes del dirigente."""
    q = (
        select(SocialPost, SocialProfile.handle, SocialProfile.platform.label("plat"))
        .join(SocialProfile, SocialPost.profile_id == SocialProfile.id)
        .where(SocialProfile.dirigente_id == dirigente_id)
    )
    if platform:
        q = q.where(SocialProfile.platform == platform)
    if date_from:
        q = q.where(SocialPost.published_at >= date_from)
    if date_to:
        q = q.where(SocialPost.published_at <= date_to)

    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar_one()

    q = q.order_by(SocialPost.published_at.desc()).offset((page - 1) * per_page).limit(per_page)
    rows = (await db.execute(q)).all()

    items = [
        PostFeedItem(
            id=p.id,
            published_at=p.published_at,
            platform=str(plat.value) if hasattr(plat, "value") else str(plat),
            content=p.content,
            url=None,  # se compone después si necesario
            likes_publicos=p.likes or 0,
            comments_total=p.comments or 0,
            shares=p.shares or 0,
            views=p.views,
            handle=handle,
        )
        for p, handle, plat in rows
    ]
    return items, total


async def _view_top(
    db: AsyncSession,
    dirigente_id: int,
    platform: str | None,
    date_from: date | None,
    date_to: date | None,
    page: int,
    per_page: int,
) -> tuple[list[PostTopItem], int]:
    """Vista top · ranking por engagement_rate (filtros calidad iguales a /content/top)."""
    quality_filters = [
        SocialProfile.dirigente_id == dirigente_id,
        func.length(SocialPost.content) >= 20,
        ~SocialPost.content.like("RT @%"),
        SocialPost.engagement_rate.is_not(None),
    ]
    q = (
        select(SocialPost, SocialProfile.handle, SocialProfile.platform.label("plat"))
        .join(SocialProfile, SocialPost.profile_id == SocialProfile.id)
        .where(*quality_filters)
    )
    if platform:
        q = q.where(SocialProfile.platform == platform)
    if date_from:
        q = q.where(SocialPost.published_at >= date_from)
    if date_to:
        q = q.where(SocialPost.published_at <= date_to)

    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar_one()

    q = q.order_by(SocialPost.engagement_rate.desc()).offset((page - 1) * per_page).limit(per_page)
    rows = (await db.execute(q)).all()

    items = [
        PostTopItem(
            id=p.id,
            published_at=p.published_at,
            platform=str(plat.value) if hasattr(plat, "value") else str(plat),
            content=p.content,
            url=None,
            likes_publicos=p.likes or 0,
            comments_total=p.comments or 0,
            shares=p.shares or 0,
            views=p.views,
            engagement_rate=p.engagement_rate,
            rank_position=(page - 1) * per_page + idx + 1,
            score=p.engagement_rate,
            handle=handle,
        )
        for idx, (p, handle, plat) in enumerate(rows)
    ]
    return items, total


async def _view_comentarios(
    db: AsyncSession,
    dirigente_id: int,
    platform: str | None,
    date_from: date | None,
    date_to: date | None,
    page: int,
    per_page: int,
) -> tuple[list[PostComentariosItem], int]:
    """Vista comentarios · posts con top quotes embebidas + polaridad."""
    quality_filters = [
        SocialProfile.dirigente_id == dirigente_id,
        SocialPost.comments > 0,  # solo posts con comments
    ]
    q = (
        select(SocialPost, SocialProfile.handle, SocialProfile.platform.label("plat"))
        .join(SocialProfile, SocialPost.profile_id == SocialProfile.id)
        .where(*quality_filters)
    )
    if platform:
        q = q.where(SocialProfile.platform == platform)
    if date_from:
        q = q.where(SocialPost.published_at >= date_from)
    if date_to:
        q = q.where(SocialPost.published_at <= date_to)

    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar_one()

    q = q.order_by(SocialPost.comments.desc()).offset((page - 1) * per_page).limit(per_page)
    rows = (await db.execute(q)).all()
    post_ids = [p.id for p, _, _ in rows]

    # Stats agregadas de comments por post (avg_polaridad + count clasificados + sample quotes)
    quotes_by_post: dict[int, dict] = {}
    if post_ids:
        stats_q = text("""
            SELECT
                parent_post_id,
                COUNT(*) FILTER (WHERE nlp_polaridad IS NOT NULL) AS classified,
                AVG(nlp_polaridad)::float AS avg_pol
            FROM social_comments
            WHERE parent_post_id = ANY(:ids)
            GROUP BY parent_post_id
        """)
        stats = (await db.execute(stats_q, {"ids": post_ids})).all()
        for row in stats:
            quotes_by_post[row.parent_post_id] = {
                "classified": int(row.classified or 0),
                "avg_pol": row.avg_pol,
                "samples": [],
            }
        # Top 3 quotes por polaridad absoluta
        quotes_q = text("""
            SELECT parent_post_id, content, nlp_polaridad
            FROM (
                SELECT parent_post_id, content, nlp_polaridad,
                       ROW_NUMBER() OVER (
                           PARTITION BY parent_post_id
                           ORDER BY ABS(nlp_polaridad) DESC NULLS LAST
                       ) AS rn
                FROM social_comments
                WHERE parent_post_id = ANY(:ids) AND content IS NOT NULL
                  AND nlp_polaridad IS NOT NULL
            ) t WHERE rn <= 3
        """)
        quote_rows = (await db.execute(quotes_q, {"ids": post_ids})).all()
        for qr in quote_rows:
            entry = quotes_by_post.setdefault(
                qr.parent_post_id, {"classified": 0, "avg_pol": None, "samples": []}
            )
            entry["samples"].append(
                QuoteSample(text=qr.content[:300], polaridad=float(qr.nlp_polaridad))
            )

    items = []
    for p, handle, plat in rows:
        stats = quotes_by_post.get(p.id, {"classified": 0, "avg_pol": None, "samples": []})
        items.append(
            PostComentariosItem(
                id=p.id,
                published_at=p.published_at,
                platform=str(plat.value) if hasattr(plat, "value") else str(plat),
                content=p.content,
                url=None,
                likes_publicos=p.likes or 0,
                comments_total=p.comments or 0,
                shares=p.shares or 0,
                views=p.views,
                handle=handle,
                comments_classified=stats["classified"],
                comments_classified_pct=(
                    round(100 * stats["classified"] / p.comments, 1)
                    if p.comments
                    else None
                ),
                avg_polaridad=stats["avg_pol"],
                sample_quotes=stats["samples"],
            )
        )
    return items, total


async def _view_fans(
    db: AsyncSession,
    dirigente_id: int,
    platform: str | None,
    date_from: date | None,
    date_to: date | None,
    page: int,
    per_page: int,
) -> tuple[list[PostFansItem], int]:
    """Vista fans · posts con reactors_capturados RADAR."""
    quality_filters = [
        SocialProfile.dirigente_id == dirigente_id,
    ]
    sub_reactors = text("""
        SELECT post_id, COUNT(*) AS n
        FROM watched_like_events
        GROUP BY post_id
    """).columns().subquery()

    q = (
        select(SocialPost, SocialProfile.handle, SocialProfile.platform.label("plat"))
        .join(SocialProfile, SocialPost.profile_id == SocialProfile.id)
        .where(*quality_filters)
    )
    if platform:
        q = q.where(SocialProfile.platform == platform)
    if date_from:
        q = q.where(SocialPost.published_at >= date_from)
    if date_to:
        q = q.where(SocialPost.published_at <= date_to)

    count_q = select(func.count()).select_from(q.subquery())
    total_all = (await db.execute(count_q)).scalar_one()

    # Filter solo posts con reactors capturados
    q_with_reactors = text("""
        SELECT sp.id, sp.published_at, sp.content, sp.likes, sp.comments, sp.shares, sp.views,
               spr.handle, spr.platform::text AS platform,
               (SELECT COUNT(*) FROM watched_like_events wle WHERE wle.post_id=sp.id) AS reactors
        FROM social_posts sp
        JOIN social_profiles spr ON sp.profile_id=spr.id
        WHERE spr.dirigente_id = :did
        AND EXISTS (SELECT 1 FROM watched_like_events wle WHERE wle.post_id=sp.id)
        ORDER BY sp.published_at DESC
        LIMIT :limit OFFSET :offset
    """)
    rows = (
        await db.execute(
            q_with_reactors,
            {"did": dirigente_id, "limit": per_page, "offset": (page - 1) * per_page},
        )
    ).all()

    total_q = text("""
        SELECT COUNT(*)
        FROM social_posts sp
        JOIN social_profiles spr ON sp.profile_id=spr.id
        WHERE spr.dirigente_id = :did
        AND EXISTS (SELECT 1 FROM watched_like_events wle WHERE wle.post_id=sp.id)
    """)
    total = (await db.execute(total_q, {"did": dirigente_id})).scalar_one()

    items = []
    for r in rows:
        likes_pub = r.likes or 0
        reactors = int(r.reactors or 0)
        cobertura_pct = round(100 * reactors / likes_pub, 1) if likes_pub > 0 else None
        items.append(
            PostFansItem(
                id=r.id,
                published_at=r.published_at,
                platform=r.platform,
                content=r.content,
                url=None,
                likes_publicos=likes_pub,
                reactors_capturados=reactors,
                cobertura_pct=cobertura_pct,
                comments_total=r.comments or 0,
                shares=r.shares or 0,
                views=r.views,
                handle=r.handle,
                avg_polaridad=None,  # se agrega en sprint posterior
                data_source="mixed",
            )
        )
    return items, total


@router.get("/unified", response_model=PostsUnifiedResponse)
@limiter.limit("60/minute")
async def posts_unified(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    dirigente_id: int,
    view: Literal["feed", "comentarios", "top", "fans"] = "feed",
    platform: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
) -> PostsUnifiedResponse:
    """Endpoint BFF · Content Hub Posts Workspace.

    Devuelve lista paginada de posts según `view`. Cada view tiene un
    handler interno separado (anti-patrón "God Endpoint" mitigado per
    Gemini cross-audit).
    """
    await assert_dirigente_access(db, current_user, dirigente_id)

    handlers = {
        "feed": _view_feed,
        "top": _view_top,
        "comentarios": _view_comentarios,
        "fans": _view_fans,
    }
    handler = handlers[view]
    items, total = await handler(
        db, dirigente_id, platform, date_from, date_to, page, per_page
    )

    return PostsUnifiedResponse(
        view=view,
        dirigente_id=dirigente_id,
        items=items,
        page=page,
        per_page=per_page,
        total=total,
        pages=(total + per_page - 1) // per_page if total > 0 else 0,
    )
