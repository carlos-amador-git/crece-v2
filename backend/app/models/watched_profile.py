"""WatchedProfile + WatchedLikeEvent — perfiles bajo observación.

Origen: PLAN-2026-05-14-watchlist-saymi.md · Fase 2.

A diferencia de ``SocialFollower`` (lista exhaustiva de seguidores capturados
por scraper privilegiado), ``WatchedProfile`` es una **watchlist nominada**:
perfiles específicos que el cliente quiere monitorear independientemente de si
siguen al dirigente o no.

Uso típico:
- Cliente entrega lista (Excel) de personas a observar → source='cliente_seed'
- CEO marca un comentarista frecuente → source='manual'
- Sistema sugiere comentarista no-watchlisted con ≥N comments → source='auto_suggested'
- Competencia conocida del dirigente → source='competidor'

El campo ``author_hash`` es **precomputado** = SHA256(f"{platform}:{external_id}:{SALT}")
para JOIN eficiente con ``social_comments.author_hash`` (que ya está hasheado por
LFPDPPP). Permite listar comentarios del watched sin re-hashear en runtime.
"""
from __future__ import annotations

import hashlib
import os
from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
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


def compute_watched_hash(platform: str, external_id: str) -> str:
    """SHA256 idéntico al usado por scrapers para social_comments.author_hash.

    Se usa el mismo SALT (env COMMENT_AUTHOR_SALT) para que un INNER JOIN
    entre ``watched_profiles.author_hash`` y ``social_comments.author_hash``
    devuelva los comments del watched sin re-hashing.
    """
    salt = os.environ.get("COMMENT_AUTHOR_SALT", "crece-v2-lfpdppp-salt-2026")
    return hashlib.sha256(f"{platform}:{external_id}:{salt}".encode("utf-8")).hexdigest()


class WatchedProfile(Base):
    __tablename__ = "watched_profiles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    dirigente_observador_id: Mapped[int] = mapped_column(
        ForeignKey("dirigentes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    org_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizaciones.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Identidad del perfil observado
    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    profile_external_id: Mapped[str] = mapped_column(String(100), nullable=False)
    profile_handle: Mapped[str | None] = mapped_column(String(255), nullable=True)
    profile_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Categorización
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Estado
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Hash precomputado para JOIN eficiente con social_comments
    author_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # Auditoría
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

    # Relaciones
    like_events: Mapped[list[WatchedLikeEvent]] = relationship(
        back_populates="watched", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "dirigente_observador_id",
            "platform",
            "profile_external_id",
            name="uq_watched_dirigente_platform_external",
        ),
        Index("ix_watched_author_hash", "author_hash"),
        Index("ix_watched_obs_source", "dirigente_observador_id", "source"),
        CheckConstraint(
            "platform IN ('TWITTER','INSTAGRAM','FACEBOOK','TIKTOK','YOUTUBE','BLUESKY','THREADS','TELEGRAM')",
            name="ck_watched_platform",
        ),
        CheckConstraint(
            "source IN ('cliente_seed','manual','auto_suggested','competidor')",
            name="ck_watched_source",
        ),
    )


class WatchedLikeEvent(Base):
    """Like/reaction detectada de un watched_profile en un post del observador.

    Necesaria porque ``social_posts.likes`` es solo agregado y no existe tabla
    ``social_reactions`` (ver B-COMPETIDORES-MODELO-1 para historia).

    Source posibles:
    - ``apify_reactions`` — capturado por scraper_one/facebook-reactions-scraper
    - ``visual_evidence`` — confirmado manualmente por CEO via screenshot
    - ``oauth_api`` — futuro, vía Graph API si hubiera permisos
    """
    __tablename__ = "watched_like_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    watched_profile_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("watched_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    post_id: Mapped[int] = mapped_column(
        ForeignKey("social_posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reaction_type: Mapped[str] = mapped_column(String(20), nullable=False, default="like")
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(String(20), nullable=False)

    watched: Mapped[WatchedProfile] = relationship(back_populates="like_events")

    __table_args__ = (
        UniqueConstraint(
            "watched_profile_id", "post_id", "reaction_type",
            name="uq_watched_like_post_type",
        ),
        CheckConstraint(
            "source IN ('apify_reactions','visual_evidence','oauth_api','other_scraper')",
            name="ck_watched_like_source",
        ),
        CheckConstraint(
            "reaction_type IN ('like','love','wow','haha','sad','angry','support','care')",
            name="ck_watched_reaction_type",
        ),
    )
