"""Bot detection API endpoints — analyze followers and post patterns."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.dirigente import Dirigente
from app.models.social import SocialPost, SocialProfile
from app.models.user import User
from app.services.bot_detection import analyze_account, analyze_followers_batch

router = APIRouter()


@router.get("/analyze/{dirigente_id}")
async def analyze_dirigente_followers(
    dirigente_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """Analyze social interactions for bot patterns on a dirigente's profiles.

    Analyzes the posts on the dirigente's social profiles for:
    - Suspicious engagement patterns (very low engagement on high-share posts)
    - Content duplication across posts
    - Posting frequency anomalies
    - Profile metadata indicators
    """
    # Verify dirigente exists
    result = await db.execute(select(Dirigente).where(Dirigente.id == dirigente_id))
    dirigente = result.scalar_one_or_none()
    if dirigente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dirigente not found")

    # Get all social profiles for this dirigente
    profiles_result = await db.execute(
        select(SocialProfile).where(SocialProfile.dirigente_id == dirigente_id)
    )
    profiles = list(profiles_result.scalars().all())

    if not profiles:
        return {
            "dirigente": dirigente.full_name,
            "total_analyzed": 0,
            "likely_bots": 0,
            "suspicious": 0,
            "humans": 0,
            "bot_percentage": 0,
            "suspicious_percentage": 0,
            "results": [],
        }

    all_results = []

    for profile in profiles:
        # Get posts for this profile
        posts_result = await db.execute(
            select(SocialPost)
            .where(SocialPost.profile_id == profile.id)
            .order_by(SocialPost.published_at.desc())
            .limit(limit)
        )
        posts = list(posts_result.scalars().all())

        # Analyze the profile itself
        profile_data = {
            "followers_count": profile.followers_count,
            "following_count": profile.following_count,
            "posts_count": profile.posts_count,
            "has_avatar": True,
            "bio": profile.handle,
        }

        posts_data = [
            {
                "content": p.content or "",
                "published_at": p.published_at.isoformat() if p.published_at else None,
                "likes": p.likes or 0,
                "comments": p.comments or 0,
                "shares": p.shares or 0,
                "views": p.views or 0,
            }
            for p in posts
        ]

        # Analyze the dirigente's own profile (should be human)
        own_result = analyze_account(
            handle=profile.handle,
            platform=profile.platform.value.lower(),
            profile=profile_data,
            posts=posts_data,
        )
        all_results.append(own_result.to_dict())

        # Analyze interaction patterns from posts to detect bot-like engagement
        # Look for suspicious patterns in the post data itself
        for post in posts:
            if post.shares and post.shares > 1000 and (post.likes or 0) < 5:
                # High shares but no likes — suspicious amplification
                bot_result = analyze_account(
                    handle=f"amplifier_{post.platform_post_id[:8]}",
                    platform=profile.platform.value.lower(),
                    profile={
                        "followers_count": 0,
                        "following_count": 0,
                        "posts_count": 0,
                    },
                    posts=[],
                )
                if bot_result.bot_probability > 0.3:
                    all_results.append(bot_result.to_dict())

    # Sort by probability descending
    all_results.sort(key=lambda r: r["bot_probability"], reverse=True)

    # Count classifications
    likely_bots = sum(1 for r in all_results if r["classification"] == "likely_bot")
    suspicious = sum(1 for r in all_results if r["classification"] == "suspicious")
    humans = sum(1 for r in all_results if r["classification"] == "human")
    total = len(all_results)

    return {
        "dirigente": dirigente.full_name,
        "total_analyzed": total,
        "likely_bots": likely_bots,
        "suspicious": suspicious,
        "humans": humans,
        "bot_percentage": round(likely_bots / total * 100, 1) if total > 0 else 0,
        "suspicious_percentage": round((likely_bots + suspicious) / total * 100, 1) if total > 0 else 0,
        "results": all_results[:limit],
    }
