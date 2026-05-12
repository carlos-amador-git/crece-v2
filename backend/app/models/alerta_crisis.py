from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AlertaCrisis(Base):
    """Crisis alert detected by the monitoring pipeline.

    Types: toxicity_spike, negative_trend, coordinated_attack, viral_negative.
    Severity levels: baja, media, alta, critica.
    """

    __tablename__ = "alertas_crisis"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizaciones.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    perfil_id: Mapped[int | None] = mapped_column(
        ForeignKey("social_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    tipo: Mapped[str] = mapped_column(String(100), nullable=False)
    severidad: Mapped[str] = mapped_column(String(20), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    post_ids: Mapped[list | None] = mapped_column(JSONB, default=list)
    estado: Mapped[str] = mapped_column(String(50), default="nueva", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # ── Relationships ────────────────────────────────────
    organizacion = relationship("Organizacion", lazy="selectin")
    perfil = relationship("SocialProfile", lazy="selectin")
