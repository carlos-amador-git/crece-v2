from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class VoterScoreIntegration(Base):
    """Voter score model for n8n integration layer.

    Unlike the internal VoterScore model (single composite score),
    this stores three separate probability scores used by the
    ML pipeline: favorable, persuadible, and attendance.
    """

    __tablename__ = "voter_scores_integration"
    __table_args__ = (
        UniqueConstraint("ciudadano_id", name="uq_voter_scores_integration_ciudadano_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizaciones.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ciudadano_id: Mapped[int] = mapped_column(
        ForeignKey("ciudadanos.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    score_favorable: Mapped[float] = mapped_column(Float, nullable=False)
    score_persuadible: Mapped[float] = mapped_column(Float, nullable=False)
    score_asistencia: Mapped[float] = mapped_column(Float, nullable=False)
    features: Mapped[dict] = mapped_column(JSONB, nullable=False)
    modelo_version: Mapped[str] = mapped_column(String(50), nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # ── Relationships ────────────────────────────────────
    organizacion = relationship("Organizacion", lazy="selectin")
    ciudadano = relationship("Ciudadano", lazy="selectin")
