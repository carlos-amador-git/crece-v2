from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CrmInteraccion(Base):
    """CRM interaction tracking for ciudadanos.

    Tracks all touchpoints: door-to-door visits, WhatsApp messages,
    phone calls, event attendance, surveys, and citizen proposals.
    Uses BigInteger PK for high-volume interaction logging.
    """

    __tablename__ = "crm_interacciones"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizaciones.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ciudadano_id: Mapped[int] = mapped_column(
        ForeignKey("ciudadanos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo: Mapped[str] = mapped_column(String(50), nullable=False)
    canal: Mapped[str | None] = mapped_column(String(50), nullable=True)
    resultado: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    referencia_tipo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    referencia_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    promotor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # ── Relationships ────────────────────────────────────
    organizacion = relationship("Organizacion", lazy="selectin")
    ciudadano = relationship("Ciudadano", lazy="selectin")
    promotor = relationship("User", lazy="selectin")
