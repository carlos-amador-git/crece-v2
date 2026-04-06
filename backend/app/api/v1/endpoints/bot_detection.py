"""Profile authenticity analysis — engagement health & anomaly detection."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.dirigente import Dirigente
from app.models.social import SocialPost, SocialProfile
from app.models.user import User

router = APIRouter()


def _health_level(score: float) -> str:
    """Traffic light: green >= 70, yellow >= 40, red < 40."""
    if score >= 70:
        return "green"
    if score >= 40:
        return "yellow"
    return "red"


@router.get("/analyze/{dirigente_id}")
async def analyze_dirigente_profiles(
    dirigente_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """Analyze authenticity & engagement health of a dirigente's social profiles.

    For each profile calculates:
    - Engagement rate (likes+comments / followers)
    - Comment/like ratio
    - % of posts with zero engagement
    - Engagement variance (coefficient of variation)
    - Health score 0-100 with traffic light classification
    - Anomalous posts (high shares but low likes)
    """
    result = await db.execute(select(Dirigente).where(Dirigente.id == dirigente_id))
    dirigente = result.scalar_one_or_none()
    if dirigente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dirigente not found")

    profiles_result = await db.execute(
        select(SocialProfile).where(SocialProfile.dirigente_id == dirigente_id)
    )
    profiles = list(profiles_result.scalars().all())

    if not profiles:
        return {
            "dirigente": dirigente.full_name,
            "profiles": [],
            "anomalies": [],
            "overall_health": 0,
            "overall_level": "red",
        }

    profile_analyses = []
    all_anomalies = []

    for profile in profiles:
        posts_result = await db.execute(
            select(SocialPost)
            .where(SocialPost.profile_id == profile.id)
            .order_by(SocialPost.published_at.desc())
            .limit(limit)
        )
        posts = list(posts_result.scalars().all())

        followers = profile.followers_count or 0
        following = profile.following_count or 0
        total_posts = len(posts)

        # --- Engagement metrics ---
        engagements = []
        zero_engagement_count = 0
        total_likes = 0
        total_comments = 0
        total_shares = 0

        for p in posts:
            likes = p.likes or 0
            comments = p.comments or 0
            shares = p.shares or 0
            eng = likes + comments
            engagements.append(eng)
            total_likes += likes
            total_comments += comments
            total_shares += shares

            if eng == 0:
                zero_engagement_count += 1

            # Anomaly: high shares but very low likes (artificial amplification)
            if shares > 500 and likes < 5:
                all_anomalies.append({
                    "platform": profile.platform.value.lower(),
                    "handle": profile.handle,
                    "type": "amplification",
                    "description": f"Post con {shares:,} shares pero solo {likes} likes",
                    "content_preview": (p.content or "")[:120],
                    "published_at": p.published_at.isoformat() if p.published_at else None,
                })

        # Engagement rate
        avg_engagement = sum(engagements) / total_posts if total_posts > 0 else 0
        engagement_rate = (avg_engagement / followers * 100) if followers > 0 else 0

        # Comment/like ratio (normal: 1:10 to 1:50)
        comment_like_ratio = (total_comments / total_likes) if total_likes > 0 else 0

        # Zero engagement percentage
        zero_pct = (zero_engagement_count / total_posts * 100) if total_posts > 0 else 0

        # Engagement variance (coefficient of variation)
        if total_posts >= 3 and avg_engagement > 0:
            variance = sum((e - avg_engagement) ** 2 for e in engagements) / total_posts
            std_dev = variance ** 0.5
            cv = std_dev / avg_engagement
        else:
            cv = 0

        # Followers/following ratio
        ff_ratio = (followers / following) if following > 0 else followers

        # --- Health score (0-100) ---
        score = 100.0
        signals = []

        # Low engagement with many followers = possibly bought followers
        if followers > 5000 and engagement_rate < 1.0:
            penalty = 30
            score -= penalty
            signals.append(f"Engagement {engagement_rate:.2f}% con {followers:,} seguidores — posibles seguidores comprados")
        elif followers > 1000 and engagement_rate < 0.5:
            penalty = 20
            score -= penalty
            signals.append(f"Engagement muy bajo ({engagement_rate:.2f}%) para {followers:,} seguidores")

        # Healthy engagement (2-5% for active campaigns)
        if engagement_rate >= 2.0:
            signals.append(f"Engagement saludable: {engagement_rate:.2f}%")

        # High zero-engagement posts
        if total_posts >= 5 and zero_pct > 50:
            score -= 20
            signals.append(f"{zero_pct:.0f}% de posts sin interaccion — bajo alcance organico")
        elif total_posts >= 5 and zero_pct > 30:
            score -= 10
            signals.append(f"{zero_pct:.0f}% de posts sin interaccion")

        # High engagement variance = possible spikes from paid amplification
        if cv > 3.0 and total_posts >= 5:
            score -= 20
            signals.append(f"Variacion de engagement muy alta (CV={cv:.1f}) — posible amplificacion puntual")
        elif cv > 2.0 and total_posts >= 5:
            score -= 10
            signals.append(f"Engagement irregular (CV={cv:.1f})")

        # Very few posts
        if total_posts < 3:
            score -= 15
            signals.append(f"Solo {total_posts} posts — datos insuficientes para evaluacion completa")

        # Abnormal comment/like ratio
        if total_likes > 10 and comment_like_ratio > 0.5:
            score -= 10
            signals.append(f"Ratio comentarios/likes alto ({comment_like_ratio:.2f}) — posible granja de comentarios")

        score = max(0, min(100, score))

        profile_analyses.append({
            "platform": profile.platform.value.lower(),
            "handle": profile.handle,
            "followers": followers,
            "following": following,
            "posts_analyzed": total_posts,
            "engagement_rate": round(engagement_rate, 2),
            "avg_engagement": round(avg_engagement, 1),
            "comment_like_ratio": round(comment_like_ratio, 3),
            "zero_engagement_pct": round(zero_pct, 1),
            "engagement_cv": round(cv, 2),
            "ff_ratio": round(ff_ratio, 2),
            "health_score": round(score),
            "health_level": _health_level(score),
            "signals": signals,
        })

    # Overall health = weighted average by follower count
    total_followers = sum(p["followers"] for p in profile_analyses) or 1
    overall = sum(p["health_score"] * p["followers"] / total_followers for p in profile_analyses)

    return {
        "dirigente": dirigente.full_name,
        "profiles": profile_analyses,
        "anomalies": all_anomalies,
        "overall_health": round(overall),
        "overall_level": _health_level(overall),
    }
