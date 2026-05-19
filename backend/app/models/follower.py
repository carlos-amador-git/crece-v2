"""SocialFollower + FollowerEngagement — lista granular de seguidores.

Origen: PLAN-2026-05-13-followers-oauth-pipeline.md S1.

A diferencia de ``SocialProfile.followers_count`` (agregado), estas tablas
guardan **cada seguidor individualmente** + su engagement (qué post comentó,
qué likeó, etc). Alimentado por:

- ``YouTubePrivilegedScraper`` (S3) cuando dirigente conecta OAuth real
- Futuro: scrapers privilegiados IG/FB (gateado por Meta App Review)
- Futuro: scrapers públicos que parseen listas accesibles sin auth

Columnas clave:
- ``follower_external_id`` — id estable de la plataforma (canal YT, user IG, etc.)
- ``is_real`` — bandera de bot detection (default true · hook a bot_detection.py
  diferido a B-FOLLOWERS-BOT-1)
- ``source`` — trazabilidad: 'oauth' | 'scraper_auth' | 'public_scraper'
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SocialFollower(Base):
    __tablename__ = "social_followers"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    dirigente_id: Mapped[int] = mapped_column(
        ForeignKey("dirigentes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    org_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizaciones.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    follower_external_id: Mapped[str] = mapped_column(String(100), nullable=False)
    follower_handle: Mapped[str | None] = mapped_column(String(100), nullable=True)
    follower_display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    follower_avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    follower_is_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    is_real: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    bot_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    last_active_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    raw_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    __table_args__ = (
        UniqueConstraint(
            "dirigente_id",
            "platform",
            "follower_external_id",
            name="uq_followers_dirigente_platform_external",
        ),
        CheckConstraint(
            "source IN ('oauth','scraper_auth','public_scraper')",
            name="ck_followers_source",
        ),
        CheckConstraint(
            "platform IN ("
            "'twitter','instagram','facebook','tiktok','youtube',"
            "'bluesky','threads','telegram')",
            name="ck_followers_platform",
        ),
    )

    dirigente = relationship("Dirigente", lazy="selectin")
    engagements = relationship(
        "FollowerEngagement",
        back_populates="follower",
        cascade="all, delete-orphan",
        lazy="select",
    )


class FollowerEngagement(Base):
    __tablename__ = "follower_engagement"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    follower_id: Mapped[int] = mapped_column(
        ForeignKey("social_followers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    post_id: Mapped[int] = mapped_column(
        ForeignKey("social_posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    engagement_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # FK a social_comments declarado solo a nivel DB (migration) porque
    # social_comments no tiene modelo SQLAlchemy registrado en Base.metadata.
    # ON DELETE SET NULL preservado en la migración.
    comment_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    engaged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    raw_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    __table_args__ = (
        UniqueConstraint(
            "follower_id",
            "post_id",
            "engagement_type",
            "comment_id",
            name="uq_engagement_follower_post_type_comment",
        ),
        CheckConstraint(
            "engagement_type IN ('comment','like','share','repost','reaction')",
            name="ck_engagement_type",
        ),
    )

    follower = relationship("SocialFollower", back_populates="engagements", lazy="selectin")
