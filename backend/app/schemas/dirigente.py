from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

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


class FlashAnalysisResponse(BaseModel):
    """Quick 5-minute analysis of a dirigente from existing DB data."""

    dirigente_name: str
    periodo: str  # "Ultimos 7 dias"
    total_posts: int
    avg_sentiment: float  # -1 to 1
    sentiment_label: str  # "Positivo" / "Negativo" / "Neutral"
    engagement_avg: float  # percentage
    engagement_delta: float  # vs previous period %
    top_post_content: str | None  # most liked post
    top_post_likes: int
    followers_total: int
    platforms_active: int
    suggested_action: str  # computed from data patterns


class SocialSummary(BaseModel):
    dirigente_id: int
    total_followers: int
    total_posts: int
    avg_engagement: float
    sentiment_breakdown: dict[str, float]
    top_platforms: list[dict[str, object]]


# ─────────────────────────────────────────────────────────────
# S5 — Onboarding wizard schemas
# ─────────────────────────────────────────────────────────────


class OnboardingHandle(BaseModel):
    """Un handle de red social provisto en el wizard."""

    platform: Literal["TWITTER", "INSTAGRAM", "FACEBOOK", "TIKTOK", "YOUTUBE"]
    handle: str = Field(min_length=1, max_length=255)
    url: str | None = None


class OnboardingRequest(BaseModel):
    """Payload del wizard admin para dar de alta un nuevo dirigente.

    Step 1 datos básicos + Step 2 handles → un solo POST transaccional.
    """

    full_name: str = Field(min_length=3, max_length=255)
    cargo: str = Field(min_length=2, max_length=255)
    partido: str = Field(default="MC", max_length=50)
    estado: str = Field(default="Ciudad de México", max_length=100)
    municipio: str | None = Field(default=None, max_length=200)
    seccion_electoral: str | None = Field(default=None, max_length=10)
    org_id: int | None = None

    # User auto-creado para login del dirigente
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    # Handles iniciales (al menos 1 requerido)
    handles: list[OnboardingHandle] = Field(min_length=1)


class OnboardingResponse(BaseModel):
    """Respuesta inmediata del POST /dirigentes/onboard.

    El endpoint retorna 201 sin esperar al Celery chain — la UI consume
    el `task_id` para hacer polling vía `/onboarding-progress`.
    """

    dirigente_id: int
    user_id: int
    sync_status: str
    task_id: str | None
    profiles_created: int
    message: str = "Dirigente creado. Scraping inicial en curso."


class OnboardingProgressStep(BaseModel):
    name: Literal["scraping", "analyzing", "calculating_ipd", "ready"]
    status: Literal["pending", "running", "done", "error"]
    started_at: datetime | None = None
    finished_at: datetime | None = None
    detail: str | None = None


class OnboardingProgressResponse(BaseModel):
    dirigente_id: int
    sync_status: str
    task_id: str | None
    error: str | None
    progress_pct: int  # 0-100
    steps: list[OnboardingProgressStep]
    updated_at: datetime | None
