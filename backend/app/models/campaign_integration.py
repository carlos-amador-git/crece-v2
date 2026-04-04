from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Campaign(Base):
    """Campaign model for n8n integration layer.

    Uses UUID primary key (different from internal Campana model which uses serial PK).
    Designed for external integration via API keys.
    """

    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizaciones.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    tipo: Mapped[str] = mapped_column(String(50), default="whatsapp", nullable=False)
    segmentacion: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    tipo_nudge: Mapped[str | None] = mapped_column(String(50), nullable=True)
    total_destinatarios: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    enviados: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    entregados: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    leidos: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    respondidos: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estado: Mapped[str] = mapped_column(String(50), default="borrador", nullable=False)
    chatwoot_campaign_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    programado_para: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    creado_por_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # ── Relationships ────────────────────────────────────
    organizacion = relationship("Organizacion", lazy="selectin")
    creado_por = relationship("User", lazy="selectin")
