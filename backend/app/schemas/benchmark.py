from __future__ import annotations

from pydantic import BaseModel

from app.models.social import Platform


class CompetidorCreate(BaseModel):
    nombre: str
    partido: str
    cargo: str
    es_rival: bool = True


class CompetidorUpdate(BaseModel):
    nombre: str | None = None
    partido: str | None = None
    cargo: str | None = None
    es_rival: bool | None = None


class CompetidorSocialProfileCreate(BaseModel):
    competidor_id: int
    platform: Platform
    handle: str
    url: str | None = None


class CompetidorSocialProfileResponse(BaseModel):
    id: int
    competidor_id: int
    platform: Platform
    handle: str
    url: str | None
    followers_count: int
    following_count: int
    posts_count: int

    model_config = {"from_attributes": True}


class CompetidorResponse(BaseModel):
    id: int
    nombre: str
    partido: str
    cargo: str
    es_rival: bool
    social_profiles: list[CompetidorSocialProfileResponse] = []

    model_config = {"from_attributes": True}


class RankingEntry(BaseModel):
    nombre: str
    partido: str
    total_followers: int
    avg_engagement: float
    platform_count: int
    ipd_score: float


class RankingResponse(BaseModel):
    entries: list[RankingEntry]
    generated_at: str
