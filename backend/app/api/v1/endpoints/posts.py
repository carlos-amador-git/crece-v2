"""Endpoint `/api/v1/posts` — Sprint S1 T5.

Por ahora expone un único endpoint: `GET /posts/{id}/topics` que devuelve el
JSON ya persistido en `social_posts.topics_extracted` más un metadata liviano
(platform, post_type, published_at). El endpoint NO dispara inferencia en vivo;
eso lo hace el batch `scripts/run_topic_extraction.py`.

Contrato de respuesta:
    {
        "post_id": int,
        "platform": "TWITTER" | ...,
        "published_at": ISO-8601 | null,
        "topics_extracted": dict | null,   # shape de TopicExtractor.extract()
        "has_extraction": bool
    }

Si el post no tiene `topics_extracted`, se devuelve 200 con `has_extraction=false`
y `topics_extracted=null` — así el frontend puede decidir si invitar al batch
manual sin romper su flujo.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.dirigente import Dirigente
from app.models.social import SocialPost, SocialProfile
from app.models.user import User

router = APIRouter()


@router.get("/{post_id}/topics")
async def get_post_topics(
    post_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    """Devuelve el `topics_extracted` persistido del post + metadata básica.

    Respeta el scoping de multi-tenant: un usuario solo puede ver topics de
    posts cuyos dirigentes pertenecen a su org (o al dirigente asociado si
    el user es de tipo dirigente).
    """
    stmt = (
        select(SocialPost)
        .join(SocialProfile, SocialPost.profile_id == SocialProfile.id)
        .join(Dirigente, SocialProfile.dirigente_id == Dirigente.id)
        .options(selectinload(SocialPost.profile))
        .where(SocialPost.id == post_id)
    )

    # Scoping por dirigente o por org del user
    if current_user.dirigente_id is not None:
        stmt = stmt.where(SocialProfile.dirigente_id == current_user.dirigente_id)
    elif getattr(current_user, "org_id", None) is not None and current_user.role != "admin":
        stmt = stmt.where(Dirigente.org_id == current_user.org_id)

    result = await db.execute(stmt)
    post = result.scalar_one_or_none()

    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post no encontrado o sin acceso",
        )

    topics = post.topics_extracted
    return {
        "post_id": post.id,
        "platform": post.profile.platform.value if post.profile else None,
        "published_at": post.published_at.isoformat() if post.published_at else None,
        "topics_extracted": topics,
        "has_extraction": bool(topics) and "_err" not in (topics or {}),
    }
