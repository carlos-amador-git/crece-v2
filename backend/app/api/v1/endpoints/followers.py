"""Endpoint ``GET /dirigentes/{dirigente_id}/followers`` — lista granular paginada.

Origen: PLAN-2026-05-13-followers-oauth-pipeline.md S1b.

Scoping (igual al patrón ``dirigentes.py`` GET):
- VIEWER con ``current_user.dirigente_id`` set → solo ve su propio dirigente.
- Non-admin → solo ve dirigentes de su misma ``org_id``.
- ADMIN → bypass org check (futuro: header ``X-Org-Id`` cross-org).

Filtros aceptados: ``platform``, ``only_with_comments``, ``only_verified``,
``page``, ``page_size``. Sin OAuth conectado ni scrapers privilegiados, el
``items`` legítimo es ``[]`` — el frontend debe mostrar empty state honesto
(D-ANTI-MOCK-1).
"""
from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.dirigente import Dirigente
from app.models.follower import FollowerEngagement, SocialFollower
from app.models.user import User

router = APIRouter()

PlatformLiteral = Literal[
    "twitter",
    "instagram",
    "facebook",
    "tiktok",
    "youtube",
    "bluesky",
    "threads",
    "telegram",
]


async def _check_dirigente_access(
    db: AsyncSession, dirigente_id: int, current_user: User
) -> Dirigente:
    """Aplica scoping multi-tenant idéntico al patrón ``GET /dirigentes/{id}``."""
    if (
        current_user.dirigente_id is not None
        and current_user.dirigente_id != dirigente_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este dirigente",
        )

    dirigente = await db.get(Dirigente, dirigente_id)
    if dirigente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dirigente not found"
        )

    if (
        current_user.role != "admin"
        and dirigente.org_id is not None
        and current_user.org_id is not None
        and dirigente.org_id != current_user.org_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dirigente pertenece a otra organizacion",
        )

    return dirigente


@router.get("/{dirigente_id}/followers")
async def list_followers(
    dirigente_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    platform: PlatformLiteral | None = Query(None, description="Filtrar por plataforma"),
    only_with_comments: bool = Query(False, description="Solo seguidores que han comentado"),
    only_verified: bool = Query(False, description="Solo seguidores verificados"),
    only_real: bool = Query(
        False,
        description="Excluir seguidores marcados como bot (is_real=false) · B-FOLLOWERS-BOT-1",
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> dict[str, Any]:
    """Devuelve seguidores paginados + summary de engagement por seguidor."""
    await _check_dirigente_access(db, dirigente_id, current_user)

    base_q = select(SocialFollower).where(SocialFollower.dirigente_id == dirigente_id)
    if platform is not None:
        base_q = base_q.where(SocialFollower.platform == platform)
    if only_verified:
        base_q = base_q.where(SocialFollower.follower_is_verified.is_(True))
    if only_real:
        base_q = base_q.where(SocialFollower.is_real.is_(True))
    if only_with_comments:
        comment_followers_subq = (
            select(FollowerEngagement.follower_id)
            .where(FollowerEngagement.engagement_type == "comment")
            .subquery()
        )
        base_q = base_q.where(SocialFollower.id.in_(select(comment_followers_subq)))

    total_q = select(func.count()).select_from(base_q.subquery())
    total = (await db.execute(total_q)).scalar_one()

    items_q = (
        base_q.order_by(SocialFollower.last_seen_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items_result = await db.execute(items_q)
    followers = list(items_result.scalars().all())

    follower_ids = [f.id for f in followers]
    summaries: dict[int, dict[str, int]] = {fid: {} for fid in follower_ids}
    if follower_ids:
        eng_q = (
            select(
                FollowerEngagement.follower_id,
                FollowerEngagement.engagement_type,
                func.count().label("cnt"),
            )
            .where(FollowerEngagement.follower_id.in_(follower_ids))
            .group_by(
                FollowerEngagement.follower_id, FollowerEngagement.engagement_type
            )
        )
        for row in (await db.execute(eng_q)).all():
            summaries.setdefault(row.follower_id, {})[row.engagement_type] = row.cnt

    items = []
    for f in followers:
        by_type = summaries.get(f.id, {})
        total_eng = sum(by_type.values())
        items.append(
            {
                "id": f.id,
                "platform": f.platform,
                "follower_external_id": f.follower_external_id,
                "follower_handle": f.follower_handle,
                "follower_display_name": f.follower_display_name,
                "follower_avatar_url": f.follower_avatar_url,
                "follower_is_verified": f.follower_is_verified,
                "is_real": f.is_real,
                "bot_score": f.bot_score,
                "first_seen_at": f.first_seen_at.isoformat(),
                "last_seen_at": f.last_seen_at.isoformat(),
                "last_active_at": (
                    f.last_active_at.isoformat() if f.last_active_at else None
                ),
                "source": f.source,
                "engagement_summary": {
                    "total_engagements": total_eng,
                    "by_type": by_type,
                },
            }
        )

    return {
        "dirigente_id": dirigente_id,
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }


@router.post("/{dirigente_id}/followers/rescan-bots")
async def rescan_bot_scores(
    dirigente_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    platform: PlatformLiteral | None = Query(None, description="Limitar a una plataforma"),
    force: bool = Query(
        False, description="Re-score incluso filas que ya tienen bot_score (default: solo NULL)"
    ),
) -> dict[str, Any]:
    """Calcula `bot_score` + `is_real` para seguidores pending del dirigente.

    B-FOLLOWERS-BOT-1 (2026-05-16): el scraper inicial puede haber escrito filas
    sin scoring (campos legacy `bot_score=NULL`). Este endpoint las completa
    sin re-llamar al scraper.

    Pattern-based analysis del handle (sin requerir profile completo).
    """
    from app.services.bot_detection import score_follower

    await _check_dirigente_access(db, dirigente_id, current_user)

    q = select(SocialFollower).where(SocialFollower.dirigente_id == dirigente_id)
    if platform is not None:
        q = q.where(SocialFollower.platform == platform)
    if not force:
        q = q.where(SocialFollower.bot_score.is_(None))
    rows = list((await db.execute(q)).scalars().all())

    n_scored = 0
    n_flagged = 0
    for f in rows:
        handle = f.follower_handle or f.follower_display_name or ""
        if not handle:
            continue
        score, is_real = score_follower(handle=handle, platform=f.platform)
        f.bot_score = score
        f.is_real = is_real
        n_scored += 1
        if not is_real:
            n_flagged += 1
    await db.commit()

    return {
        "dirigente_id": dirigente_id,
        "platform_filter": platform,
        "force": force,
        "candidates": len(rows),
        "scored": n_scored,
        "flagged_as_bot": n_flagged,
    }
