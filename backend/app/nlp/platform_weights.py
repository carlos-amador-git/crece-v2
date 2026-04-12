from __future__ import annotations

"""Platform-specific sentiment normalization coefficients.

Research findings on platform sentiment bias:
- Twitter/X tends to skew negative due to outrage amplification algorithms
  and character limits that strip nuance.
- Instagram skews positive due to visual-first content, aspirational culture,
  and algorithm favoring engagement on positive content.
- Facebook skews slightly positive for public pages (community reinforcement).
- TikTok is more neutral but trending content can skew either direction.
- YouTube comments skew slightly negative but video sentiment varies.
- Bluesky is too new for robust bias measurement; treated as neutral.

These coefficients are ADDITIVE corrections applied to raw sentiment scores
to normalize cross-platform comparisons. A score of 0 means no correction.
"""

# Additive correction to raw sentiment score (-1.0 to 1.0 scale)
SENTIMENT_BIAS_CORRECTION: dict[str, float] = {
    "twitter": +0.08,  # counteract negative skew
    "instagram": -0.06,  # counteract positive skew
    "facebook": -0.04,  # counteract slight positive skew
    "tiktok": 0.00,  # relatively neutral
    "youtube": +0.03,  # slight negative skew in comments
    "bluesky": 0.00,  # insufficient data, no correction
}

# Multiplicative weight: how much to trust sentiment from each platform
# (1.0 = full trust, lower = noisier platform)
SENTIMENT_CONFIDENCE_WEIGHT: dict[str, float] = {
    "twitter": 0.85,
    "instagram": 0.70,  # captions are short, less text signal
    "facebook": 0.90,  # longer posts, more reliable text
    "tiktok": 0.60,  # very short captions, mostly visual
    "youtube": 0.80,  # descriptions are reliable
    "bluesky": 0.75,
}

# Engagement normalization: multiplier to make engagement rates comparable
# across platforms (base: Twitter = 1.0)
ENGAGEMENT_NORMALIZATION: dict[str, float] = {
    "twitter": 1.00,
    "instagram": 0.60,  # higher raw rates, normalize down
    "facebook": 0.80,
    "tiktok": 0.40,  # very high raw rates
    "youtube": 1.20,  # lower raw rates, normalize up
    "bluesky": 1.00,
}


def normalize_sentiment(raw_score: float, platform: str) -> float:
    """Apply platform-specific bias correction to a raw sentiment score.

    Args:
        raw_score: Raw sentiment score in range [-1.0, 1.0]
        platform: Platform identifier string

    Returns:
        Corrected score clamped to [-1.0, 1.0]
    """
    correction = SENTIMENT_BIAS_CORRECTION.get(platform, 0.0)
    corrected = raw_score + correction
    return max(-1.0, min(1.0, corrected))


def weighted_sentiment(raw_score: float, platform: str) -> tuple[float, float]:
    """Return (corrected_score, confidence_weight) for cross-platform aggregation."""
    corrected = normalize_sentiment(raw_score, platform)
    weight = SENTIMENT_CONFIDENCE_WEIGHT.get(platform, 0.75)
    return corrected, weight


def normalize_engagement(raw_rate: float, platform: str) -> float:
    """Normalize engagement rate to be comparable across platforms."""
    multiplier = ENGAGEMENT_NORMALIZATION.get(platform, 1.0)
    return raw_rate * multiplier
