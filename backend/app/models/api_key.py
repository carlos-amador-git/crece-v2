from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ApiKey(Base):
    """API Key model for authenticating external integrations (n8n, webhooks).

    Keys are stored as SHA-256 hashes. The raw key is only returned once
    at creation time and cannot be recovered. The key_prefix field stores
    the first 12 characters for identification in listings.
    """

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizaciones.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    key_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    key_prefix: Mapped[str] = mapped_column(String(12), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    permissions: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # ── Relationships ────────────────────────────────────
    organizacion = relationship("Organizacion", lazy="selectin")
    user = relationship("User", lazy="selectin")


def generate_api_key() -> tuple[str, str]:
    """Generate a Stripe-style API key.

    Returns:
        Tuple of (raw_key, key_hash). The raw key should only be shown once
        to the user and never stored in plaintext.
    """
    raw = "crece_live_" + secrets.token_urlsafe(32)
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    return raw, hashed
