from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class MetricaSocialCreate(BaseModel):
    profile_id: int
    followers_count: int = 0
    following_count: int = 0
    posts_count: int = 0
    engagement_rate_avg: float = 0.0
    followers_delta: int = 0
    posts_delta: int = 0
    periodo: str | None = None


class MetricaSocialResponse(BaseModel):
    id: int
    profile_id: int
    followers_count: int
    following_count: int
    posts_count: int
    engagement_rate_avg: float
    followers_delta: int
    posts_delta: int
    periodo: str | None
    captured_at: datetime

    model_config = {"from_attributes": True}


class MetricaSocialTrend(BaseModel):
    """Time series data point for chart rendering."""

    captured_at: datetime
    followers_count: int
    following_count: int
    posts_count: int
    engagement_rate_avg: float
    followers_delta: int
    posts_delta: int
