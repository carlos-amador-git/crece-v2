"""CompetitorProfile + CompetitorPost + CompetitorMetricsWeekly.

Modelo **ligero benchmark-oriented** para competencia política.

A diferencia de los `dirigentes` del cliente (Saymi, Piña, etc.) que tienen
scraping diario, OAuth, autohash de comentaristas y NLP por comment, los
competidores se modelan con granularidad reducida:

- Solo FB (donde efectivamente compiten).
- Scraping 1×/mes (no diario, no semanal).
- Posts agregados (sin tabla de comentaristas autohash).
- Sin reactions detalladas por usuario.
- NLP solo a nivel de post (no por comment).
- Métricas pre-computadas mensualmente para benchmarking side-by-side.

Origen: B-COMPETIDORES-MODELO-1. Reemplaza a `WatchedProfile.source='competidor'`
que era huérfano del pipeline.
"""
from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CompetitorProfile(Base):
    """Competidor político — perfil ligero para benchmarking."""

    __tablename__ = "competitor_profiles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizaciones.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dirigente_objetivo_id: Mapped[int] = mapped_column(
        ForeignKey("dirigentes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="A quién compite este competidor (ej: Saymi=3).",
    )

    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    partido: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cargo: Mapped[str | None] = mapped_column(String(255), nullable=True)

    platform: Mapped[str] = mapped_column(
        String(20), nullable=False, default="FACEBOOK"
    )
    profile_external_id: Mapped[str] = mapped_column(String(100), nullable=False)
    profile_handle: Mapped[str | None] = mapped_column(String(255), nullable=True)
    profile_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True si partido+cargo verificados con fuente oficial.",
    )

    last_scraped_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    posts: Mapped[list[CompetitorPost]] = relationship(
        back_populates="competitor", cascade="all, delete-orphan"
    )
    monthly_metrics: Mapped[list[CompetitorMetricsMonthly]] = relationship(
        back_populates="competitor", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "org_id",
            "platform",
            "profile_external_id",
            name="uq_competitor_org_platform_external",
        ),
        CheckConstraint(
            "platform IN ('TWITTER','INSTAGRAM','FACEBOOK','TIKTOK','YOUTUBE')",
            name="ck_competitor_platform",
        ),
    )


class CompetitorPost(Base):
    """Post de un competidor — agregado, sin comments detallados.

    NLP solo a nivel de post (sentiment_score + label). No hay tabla de
    comentaristas autohash porque no nos importa quién comenta a la competencia.
    """

    __tablename__ = "competitor_posts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    competitor_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("competitor_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    platform_post_id: Mapped[str] = mapped_column(String(255), nullable=False)
    post_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    reactions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    comments_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    shares: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    views: Mapped[int | None] = mapped_column(Integer, nullable=True)

    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    sentiment_label: Mapped[str | None] = mapped_column(String(20), nullable=True)
    nlp_model_version: Mapped[str | None] = mapped_column(String(50), nullable=True)

    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    competitor: Mapped[CompetitorProfile] = relationship(back_populates="posts")

    __table_args__ = (
        UniqueConstraint(
            "competitor_id", "platform_post_id", name="uq_competitor_post_id"
        ),
        Index("ix_competitor_posts_published", "competitor_id", "published_at"),
    )


class CompetitorMetricsMonthly(Base):
    """Métricas mensuales pre-computadas para benchmarking rápido.

    month_start = primer día del mes (YYYY-MM-01). Permite query side-by-side
    Saymi vs Ivette vs Susana sin escanear tabla de posts.
    """

    __tablename__ = "competitor_metrics_monthly"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    competitor_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("competitor_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    month_start: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    posts_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_reactions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_comments: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_shares: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    engagement_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    sentiment_avg: Mapped[float | None] = mapped_column(Float, nullable=True)
    sentiment_label_modal: Mapped[str | None] = mapped_column(String(20), nullable=True)

    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    competitor: Mapped[CompetitorProfile] = relationship(back_populates="monthly_metrics")

    __table_args__ = (
        UniqueConstraint(
            "competitor_id", "month_start", name="uq_competitor_month"
        ),
    )
