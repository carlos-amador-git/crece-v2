"""Bot detection service — pattern-based analysis of suspicious social media accounts.

Analyzes follower lists, post patterns, and engagement metrics to score
the probability that an account is a bot or part of a coordinated
inauthentic behavior (CIB) network.

Scoring methodology:
- Username patterns (random characters, sequential numbers)
- Posting frequency anomalies (too regular or burst patterns)
- Engagement ratios (low engagement despite high followers)
- Profile completeness (no avatar, no bio, default settings)
- Account age vs activity (new account, high volume)
- Content repetition (duplicate/near-duplicate posts)
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BotSignal:
    """A single bot indicator with a name, score contribution, and explanation."""
    name: str
    score: float  # 0.0 to 1.0 contribution
    detail: str


@dataclass
class BotAnalysisResult:
    """Result of bot analysis for a single account."""
    handle: str
    platform: str
    bot_probability: float  # 0.0 (human) to 1.0 (bot)
    classification: str  # "human", "suspicious", "likely_bot"
    signals: list[BotSignal] = field(default_factory=list)
    analyzed_at: str = ""

    def __post_init__(self) -> None:
        if not self.analyzed_at:
            self.analyzed_at = datetime.now(UTC).isoformat()

    def to_dict(self) -> dict:
        return {
            "handle": self.handle,
            "platform": self.platform,
            "bot_probability": round(self.bot_probability, 4),
            "classification": self.classification,
            "signals": [
                {"name": s.name, "score": round(s.score, 3), "detail": s.detail}
                for s in self.signals
            ],
            "analyzed_at": self.analyzed_at,
        }


def _classify(probability: float) -> str:
    if probability >= 0.70:
        return "likely_bot"
    if probability >= 0.40:
        return "suspicious"
    return "human"


# ── Username analysis ──────────────────────────────────────────────────


def _analyze_username(handle: str) -> list[BotSignal]:
    """Check username for bot-like patterns."""
    signals: list[BotSignal] = []

    # Pattern: random alphanumeric with 8+ trailing digits
    if re.search(r"\d{8,}$", handle):
        signals.append(BotSignal(
            "username_trailing_digits",
            0.3,
            f"Username '{handle}' has 8+ trailing digits",
        ))

    # Pattern: very short handle with random chars
    if len(handle) <= 5 and re.match(r"^[a-z]{2,3}\d{2,3}$", handle, re.I):
        signals.append(BotSignal(
            "username_short_random",
            0.2,
            f"Username '{handle}' looks auto-generated (short + random)",
        ))

    # Pattern: default-style names (user123456, bot_, etc.)
    if re.match(r"^(user|bot|test|fake|spam)\d+", handle, re.I):
        signals.append(BotSignal(
            "username_suspicious_prefix",
            0.4,
            f"Username '{handle}' starts with suspicious prefix",
        ))

    # Pattern: excessive underscores or dots
    special_count = handle.count("_") + handle.count(".")
    if special_count >= 4:
        signals.append(BotSignal(
            "username_excessive_separators",
            0.15,
            f"Username '{handle}' has {special_count} separators",
        ))

    return signals


# ── Profile analysis ───────────────────────────────────────────────────


def _analyze_profile(profile: dict) -> list[BotSignal]:
    """Check profile metadata for bot indicators."""
    signals: list[BotSignal] = []

    followers = profile.get("followers_count", 0)
    following = profile.get("following_count", 0)
    posts = profile.get("posts_count", 0)

    # Follower/following ratio — bots often follow many, have few followers
    if following > 0 and followers > 0:
        ratio = followers / following
        if ratio < 0.05 and following > 500:
            signals.append(BotSignal(
                "low_follower_ratio",
                0.35,
                f"Very low follower/following ratio: {ratio:.3f} ({followers}/{following})",
            ))
        elif ratio < 0.2 and following > 200:
            signals.append(BotSignal(
                "low_follower_ratio",
                0.15,
                f"Low follower/following ratio: {ratio:.3f} ({followers}/{following})",
            ))

    # Zero posts but many following — lurker bot pattern
    if posts == 0 and following > 100:
        signals.append(BotSignal(
            "zero_posts_many_following",
            0.25,
            f"No posts but following {following} accounts",
        ))

    # No avatar or bio
    if not profile.get("has_avatar", True):
        signals.append(BotSignal(
            "no_avatar",
            0.15,
            "Account has no profile picture",
        ))

    if not profile.get("bio") and not profile.get("description"):
        signals.append(BotSignal(
            "no_bio",
            0.10,
            "Account has no bio/description",
        ))

    # Account age — very new accounts with high activity
    created_at = profile.get("created_at")
    if created_at:
        try:
            if isinstance(created_at, str):
                created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            else:
                created = created_at
            age_days = (datetime.now(UTC) - created).days
            if age_days < 30 and posts > 100:
                signals.append(BotSignal(
                    "new_account_high_activity",
                    0.30,
                    f"Account is {age_days} days old with {posts} posts",
                ))
            elif age_days < 7 and following > 200:
                signals.append(BotSignal(
                    "new_account_mass_following",
                    0.35,
                    f"Account is {age_days} days old following {following} accounts",
                ))
        except (ValueError, TypeError):
            pass

    return signals


# ── Post pattern analysis ──────────────────────────────────────────────


def _analyze_posts(posts: list[dict]) -> list[BotSignal]:
    """Check posting patterns for bot behavior."""
    signals: list[BotSignal] = []

    if not posts or len(posts) < 3:
        return signals

    # Check for duplicate/near-duplicate content
    contents = [p.get("content", "").strip().lower() for p in posts if p.get("content")]
    if contents:
        counter = Counter(contents)
        duplicates = {text: count for text, count in counter.items() if count > 1}
        if duplicates:
            dup_count = sum(duplicates.values())
            dup_ratio = dup_count / len(contents)
            if dup_ratio > 0.5:
                signals.append(BotSignal(
                    "high_content_duplication",
                    0.40,
                    f"{dup_count}/{len(contents)} posts are duplicates ({dup_ratio:.0%})",
                ))
            elif dup_ratio > 0.2:
                signals.append(BotSignal(
                    "content_duplication",
                    0.20,
                    f"{dup_count}/{len(contents)} posts are duplicates ({dup_ratio:.0%})",
                ))

    # Check posting frequency — bots post at regular intervals
    timestamps = []
    for p in posts:
        ts = p.get("published_at") or p.get("timestamp") or p.get("created_at")
        if ts:
            try:
                if isinstance(ts, str):
                    timestamps.append(datetime.fromisoformat(ts.replace("Z", "+00:00")))
                elif isinstance(ts, datetime):
                    timestamps.append(ts)
            except (ValueError, TypeError):
                pass

    if len(timestamps) >= 5:
        timestamps.sort()
        intervals = [
            (timestamps[i + 1] - timestamps[i]).total_seconds()
            for i in range(len(timestamps) - 1)
        ]

        # Check for suspiciously regular intervals (std dev < 5% of mean)
        if intervals:
            mean_interval = sum(intervals) / len(intervals)
            if mean_interval > 0:
                variance = sum((x - mean_interval) ** 2 for x in intervals) / len(intervals)
                std_dev = variance ** 0.5
                cv = std_dev / mean_interval  # coefficient of variation

                if cv < 0.05 and len(intervals) >= 5:
                    signals.append(BotSignal(
                        "regular_posting_interval",
                        0.35,
                        f"Posts at suspiciously regular intervals (CV={cv:.3f}, mean={mean_interval:.0f}s)",
                    ))
                elif cv < 0.15 and len(intervals) >= 10:
                    signals.append(BotSignal(
                        "semi_regular_posting",
                        0.15,
                        f"Posts at somewhat regular intervals (CV={cv:.3f})",
                    ))

        # Check for burst posting (many posts in short window)
        burst_threshold = 60  # seconds
        burst_count = sum(1 for i in intervals if i < burst_threshold)
        if burst_count > len(intervals) * 0.5 and burst_count >= 3:
            signals.append(BotSignal(
                "burst_posting",
                0.25,
                f"{burst_count} posts within {burst_threshold}s intervals",
            ))

    # Check engagement ratio — low engagement on high-volume posting
    engagement_ratios = []
    for p in posts:
        likes = p.get("likes", 0) or 0
        comments = p.get("comments", 0) or 0
        views = p.get("views", 0) or 0
        if views > 0:
            engagement_ratios.append((likes + comments) / views)

    if engagement_ratios and len(engagement_ratios) >= 5:
        avg_engagement = sum(engagement_ratios) / len(engagement_ratios)
        if avg_engagement < 0.001:
            signals.append(BotSignal(
                "zero_engagement",
                0.20,
                f"Near-zero engagement rate: {avg_engagement:.4f}",
            ))

    return signals


# ── Main analysis function ─────────────────────────────────────────────


def analyze_account(
    handle: str,
    platform: str,
    profile: dict | None = None,
    posts: list[dict] | None = None,
    followers_sample: list[dict] | None = None,
) -> BotAnalysisResult:
    """Analyze a single account for bot indicators.

    Args:
        handle: Account handle/username
        platform: Social media platform
        profile: Profile metadata dict (followers_count, following_count, etc.)
        posts: List of post dicts (content, published_at, likes, etc.)
        followers_sample: Sample of follower profiles for bulk analysis

    Returns:
        BotAnalysisResult with probability score and signals
    """
    all_signals: list[BotSignal] = []

    # Username analysis
    all_signals.extend(_analyze_username(handle))

    # Profile analysis
    if profile:
        all_signals.extend(_analyze_profile(profile))

    # Post pattern analysis
    if posts:
        all_signals.extend(_analyze_posts(posts))

    # Calculate probability — weighted sum of signals, capped at 1.0
    if all_signals:
        raw_score = sum(s.score for s in all_signals)
        # Apply diminishing returns for multiple signals
        probability = min(1.0, 1.0 - (1.0 - min(raw_score, 1.0)) ** 0.8)
    else:
        probability = 0.05  # baseline uncertainty

    return BotAnalysisResult(
        handle=handle,
        platform=platform,
        bot_probability=probability,
        classification=_classify(probability),
        signals=all_signals,
    )


def analyze_followers_batch(
    followers: list[dict],
    platform: str,
) -> dict:
    """Analyze a batch of followers for bot presence.

    Returns summary with bot counts and individual results.
    """
    results = []
    for f in followers:
        handle = f.get("handle") or f.get("username") or f.get("screen_name", "unknown")
        result = analyze_account(
            handle=handle,
            platform=platform,
            profile=f,
        )
        results.append(result)

    classifications = Counter(r.classification for r in results)
    bot_count = classifications.get("likely_bot", 0)
    suspicious_count = classifications.get("suspicious", 0)

    return {
        "total_analyzed": len(results),
        "likely_bots": bot_count,
        "suspicious": suspicious_count,
        "humans": classifications.get("human", 0),
        "bot_percentage": round(bot_count / len(results) * 100, 1) if results else 0,
        "suspicious_percentage": round(
            (bot_count + suspicious_count) / len(results) * 100, 1
        ) if results else 0,
        "results": [r.to_dict() for r in results],
        "analyzed_at": datetime.now(UTC).isoformat(),
    }
