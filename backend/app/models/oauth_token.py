"""OAuthTokenByPlatform — tokens OAuth por dirigente × plataforma (Sprint S5 §6).

D-22 · D-23 · SPRINT-S5-SCOPING §2.2. Los endpoints MVP escriben filas con
``is_stub=True`` hasta Meta App Review (DIFERIDO-02). X NO aparece en el CHECK
(D-19 · scraping permanente).

Status values:
    active · expired · revoked_by_user · refresh_failed · pending_relink

Plataformas permitidas (CHECK constraint):
    instagram · facebook_page · tiktok · youtube
"""
from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class OAuthPlatform(StrEnum):
    INSTAGRAM = "instagram"
    FACEBOOK_PAGE = "facebook_page"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"


class OAuthTokenStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED_BY_USER = "revoked_by_user"
    REFRESH_FAILED = "refresh_failed"
    PENDING_RELINK = "pending_relink"


class OAuthTokenByPlatform(Base):
    __tablename__ = "oauth_tokens_by_platform"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
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
    token_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    platform_user_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    platform_username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    scopes: Mapped[list | None] = mapped_column(JSONB, nullable=False, default=list)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_refreshed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_stub: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
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

    dirigente = relationship("Dirigente", lazy="selectin")
