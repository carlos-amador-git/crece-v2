from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.social import SocialProfileResponse


class DirigenteCreate(BaseModel):
    full_name: str
    cargo: str
    partido: str = "MC"
    estado: str
    municipio: str | None = None
    seccion_electoral: str | None = None


class DirigenteUpdate(BaseModel):
    full_name: str | None = None
    cargo: str | None = None
    partido: str | None = None
    estado: str | None = None
    municipio: str | None = None
    seccion_electoral: str | None = None


class DirigenteResponse(BaseModel):
    id: int
    full_name: str
    cargo: str
    partido: str
    estado: str
    municipio: str | None
    seccion_electoral: str | None
    created_at: datetime
    updated_at: datetime
    social_profiles: list[SocialProfileResponse] = []

    model_config = {"from_attributes": True}


class DiagnosticoResponse(BaseModel):
    """Aggregated digital penetration index for a dirigente."""

    dirigente_id: int
    full_name: str
    ipd_score: float  # 0-10
    platform_scores: dict[str, float]
    total_followers: int
    avg_engagement_rate: float
    posting_frequency: float  # posts per day
    platform_coverage: float  # % of platforms with active profiles
    recommendations: list[str]


class SocialSummary(BaseModel):
    dirigente_id: int
    total_followers: int
    total_posts: int
    avg_engagement: float
    sentiment_breakdown: dict[str, float]
    top_platforms: list[dict[str, object]]
