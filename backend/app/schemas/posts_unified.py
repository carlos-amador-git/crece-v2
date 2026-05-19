"""Schemas Content Hub F4 · 2026-05-19

PostUnifiedItem es el modelo canónico que el endpoint /api/v1/posts/unified
devuelve. Usa discriminador `view` para soportar polimorfismo entre las 4
vistas (feed/comentarios/top/fans) per Gemini cross-audit concern.

Cada view tiene un shape ligeramente distinto:
- feed: post regular del dirigente (Apify snapshot)
- comentarios: post con top quotes embebidas (NLP polaridad)
- top: post con engagement_rate calculado + ranking score
- fans: post con reactors_capturados (RADAR) + cobertura_pct
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class QuoteSample(BaseModel):
    text: str
    polaridad: float


class PostUnifiedBase(BaseModel):
    """Campos comunes a las 4 vistas."""
    id: int
    published_at: datetime
    platform: str
    content: str | None
    url: str | None
    likes_publicos: int = Field(0, description="Snapshot público Apify")
    comments_total: int = Field(0)
    shares: int = Field(0)
    views: int | None = None
    handle: str | None = None
    dirigente_nombre: str | None = None


class PostFeedItem(PostUnifiedBase):
    """Vista feed · posts recientes del dirigente."""
    view: Literal["feed"] = "feed"
    data_source: Literal["apify"] = "apify"


class PostComentariosItem(PostUnifiedBase):
    """Vista comentarios · post con top quotes."""
    view: Literal["comentarios"] = "comentarios"
    data_source: Literal["mixed"] = "mixed"
    comments_classified: int = 0
    comments_classified_pct: float | None = None
    avg_polaridad: float | None = None
    sample_quotes: list[QuoteSample] = Field(default_factory=list)


class PostTopItem(PostUnifiedBase):
    """Vista top · ranking por métrica."""
    view: Literal["top"] = "top"
    data_source: Literal["apify"] = "apify"
    engagement_rate: float | None = None
    rank_position: int | None = None
    score: float | None = None


class PostFansItem(PostUnifiedBase):
    """Vista fans · posts con reactors individuales capturados."""
    view: Literal["fans"] = "fans"
    data_source: Literal["mixed", "radar"] = "mixed"
    reactors_capturados: int = 0
    cobertura_pct: float | None = None
    avg_polaridad: float | None = None


# Union discriminada · Pydantic v2 valida automáticamente
PostUnifiedItem = (
    PostFeedItem | PostComentariosItem | PostTopItem | PostFansItem
)


class PostsUnifiedResponse(BaseModel):
    """Response paginada del endpoint /posts/unified."""
    view: Literal["feed", "comentarios", "top", "fans"]
    dirigente_id: int
    items: list[PostUnifiedItem]
    page: int
    per_page: int
    total: int
    pages: int
