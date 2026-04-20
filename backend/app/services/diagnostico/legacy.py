from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dirigente import Dirigente
from app.models.social import Platform, SocialPost, SocialProfile
from app.schemas.dirigente import DiagnosticoResponse

# ── Platform weights for IPD calculation ──────────────────
# Weight reflects political relevance in Mexico's digital landscape
PLATFORM_WEIGHTS: dict[Platform, float] = {
    Platform.TWITTER: 0.30,
    Platform.FACEBOOK: 0.25,
    Platform.INSTAGRAM: 0.20,
    Platform.TIKTOK: 0.10,
    Platform.YOUTUBE: 0.10,
    Platform.BLUESKY: 0.05,
}

# Reference benchmarks for scoring normalization (Mexican political figures)
FOLLOWER_BENCHMARKS: dict[Platform, int] = {
    Platform.TWITTER: 50_000,
    Platform.FACEBOOK: 100_000,
    Platform.INSTAGRAM: 50_000,
    Platform.TIKTOK: 30_000,
    Platform.YOUTUBE: 20_000,
    Platform.BLUESKY: 5_000,
}

ENGAGEMENT_BENCHMARKS: dict[Platform, float] = {
    Platform.TWITTER: 0.02,
    Platform.FACEBOOK: 0.03,
    Platform.INSTAGRAM: 0.04,
    Platform.TIKTOK: 0.06,
    Platform.YOUTUBE: 0.03,
    Platform.BLUESKY: 0.03,
}


async def calculate_ipd(
    db: AsyncSession,
    dirigente: Dirigente,
) -> DiagnosticoResponse:
    """Calculate the Indice de Penetracion Digital (IPD) — scale 0 to 10.

    Components:
    - Follower reach (normalized per platform)         — 30%
    - Engagement rate (vs benchmark)                   — 30%
    - Posting frequency (consistency)                   — 20%
    - Platform coverage (breadth of presence)            — 20%
    """
    profiles_result = await db.execute(
        select(SocialProfile).where(SocialProfile.dirigente_id == dirigente.id)
    )
    profiles = list(profiles_result.scalars().all())

    if not profiles:
        return DiagnosticoResponse(
            dirigente_id=dirigente.id,
            full_name=dirigente.full_name,
            ipd_score=0.0,
            platform_scores={},
            total_followers=0,
            avg_engagement_rate=0.0,
            posting_frequency=0.0,
            platform_coverage=0.0,
            recommendations=["No social profiles registered. Add profiles to begin tracking."],
        )

    total_followers = 0
    platform_scores: dict[str, float] = {}
    weighted_engagement_sum = 0.0
    weighted_engagement_weight = 0.0
    total_posts_30d = 0
    recommendations: list[str] = []

    thirty_days_ago = datetime.now(UTC) - timedelta(days=30)

    for profile in profiles:
        platform = profile.platform
        weight = PLATFORM_WEIGHTS.get(platform, 0.05)

        # Follower component
        benchmark = FOLLOWER_BENCHMARKS.get(platform, 50_000)
        follower_score = min(profile.followers_count / benchmark, 1.0) * 10.0

        # Engagement component — average from last 30 days of posts
        eng_result = await db.execute(
            select(func.avg(SocialPost.engagement_rate), func.count(SocialPost.id)).where(
                SocialPost.profile_id == profile.id,
                SocialPost.published_at >= thirty_days_ago,
            )
        )
        row = eng_result.one()
        avg_eng = float(row[0]) if row[0] is not None else 0.0
        post_count = int(row[1])

        eng_benchmark = ENGAGEMENT_BENCHMARKS.get(platform, 0.03)
        engagement_score = min(avg_eng / eng_benchmark, 1.0) * 10.0

        # Posting frequency component
        frequency = post_count / 30.0  # posts per day
        # Ideal: 1-3 posts/day → score 10; less than 0.1 → score ~1
        freq_score = min(frequency / 1.0, 1.0) * 10.0

        # Weighted platform score
        platform_total = follower_score * 0.30 + engagement_score * 0.30 + freq_score * 0.40
        platform_scores[platform.value.lower()] = round(platform_total, 2)

        total_followers += profile.followers_count
        weighted_engagement_sum += avg_eng * weight
        weighted_engagement_weight += weight
        total_posts_30d += post_count

        # Generate recommendations
        if profile.followers_count < benchmark * 0.1:
            recommendations.append(
                f"Low follower count on {platform.value}. "
                f"Current: {profile.followers_count:,}, target: {benchmark:,}."
            )
        if avg_eng < eng_benchmark * 0.5:
            recommendations.append(
                f"Engagement on {platform.value} is below 50% of benchmark. "
                f"Focus on interactive content."
            )
        if frequency < 0.3:
            recommendations.append(
                f"Posting frequency on {platform.value} is very low ({frequency:.1f}/day). "
                f"Aim for at least 1 post per day."
            )

    # Platform coverage: fraction of 6 platforms with active profiles
    active_platforms = len(profiles)
    total_platforms = len(Platform)
    coverage = active_platforms / total_platforms

    # Final IPD: weighted average of platform scores + coverage bonus
    if platform_scores:
        # Weight each platform score by its political relevance weight
        weighted_sum = 0.0
        weight_total = 0.0
        for plat_str, score in platform_scores.items():
            plat = Platform(plat_str.upper())
            w = PLATFORM_WEIGHTS.get(plat, 0.05)
            weighted_sum += score * w
            weight_total += w
        base_score = weighted_sum / weight_total if weight_total > 0 else 0.0
    else:
        base_score = 0.0

    # Coverage bonus: up to 2 points extra for having all platforms
    ipd_score = base_score * 0.80 + coverage * 10.0 * 0.20
    ipd_score = round(min(ipd_score, 10.0), 2)

    avg_engagement = (
        weighted_engagement_sum / weighted_engagement_weight
        if weighted_engagement_weight > 0
        else 0.0
    )

    if coverage < 0.5:
        missing = [p.value.lower() for p in Platform if p not in {pr.platform for pr in profiles}]
        recommendations.append(
            f"Low platform coverage ({coverage:.0%}). Missing: {', '.join(missing)}."
        )

    return DiagnosticoResponse(
        dirigente_id=dirigente.id,
        full_name=dirigente.full_name,
        ipd_score=ipd_score,
        platform_scores=platform_scores,
        total_followers=total_followers,
        avg_engagement_rate=round(avg_engagement, 4),
        posting_frequency=round(total_posts_30d / 30.0, 2),
        platform_coverage=round(coverage, 2),
        recommendations=recommendations[:10],  # cap at 10
    )
