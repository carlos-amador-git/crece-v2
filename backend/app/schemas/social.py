from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.social import Platform, PostType, SentimentLabel


class SocialProfileCreate(BaseModel):
    dirigente_id: int
    platform: Platform
    handle: str
    url: str | None = None


class SocialProfileUpdate(BaseModel):
    handle: str | None = None
    url: str | None = None
    followers_count: int | None = None
    following_count: int | None = None
    posts_count: int | None = None


class SocialProfileResponse(BaseModel):
    id: int
    dirigente_id: int
    platform: Platform
    handle: str
    url: str | None
    followers_count: int
    following_count: int
    posts_count: int
    last_scraped_at: datetime | None

    model_config = {"from_attributes": True}


class SocialPostResponse(BaseModel):
    id: int
    profile_id: int
    platform_post_id: str
    content: str | None
    post_type: PostType
    published_at: datetime
    likes: int
    comments: int
    shares: int
    views: int
    engagement_rate: float
    sentiment_score: float | None
    sentiment_label: SentimentLabel | None
    emotions: dict | None
    is_political: bool
    scraped_at: datetime
    platform: str | None = None
    url: str | None = None
    dirigente_nombre: str | None = None

    model_config = {"from_attributes": True}


class SentimentAnalysisResponse(BaseModel):
    id: int
    post_id: int
    model_used: str
    sentiment_score: float
    sentiment_label: SentimentLabel
    emotions: dict | None
    topics: dict | None
    is_toxic: bool
    toxicity_score: float
    propaganda_labels: dict | None
    analyzed_at: datetime

    model_config = {"from_attributes": True}


class SentimentTimelinePoint(BaseModel):
    date: str
    avg_sentiment: float
    post_count: int
    positive_pct: float
    negative_pct: float
    neutral_pct: float


class ScrapeRequest(BaseModel):
    platforms: list[Platform] | None = None  # None = all platforms
