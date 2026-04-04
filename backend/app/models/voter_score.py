from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SegmentoVotante(StrEnum):
    PROMOTABLE = "promotable"
    PERSUADIBLE = "persuadible"
    INDECISO = "indeciso"
    OPOSITOR = "opositor"


class VoterScore(Base):
    __tablename__ = "voter_scores"
    __table_args__ = (
        UniqueConstraint("ciudadano_id", name="uq_voter_scores_ciudadano_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ciudadano_id: Mapped[int] = mapped_column(
        ForeignKey("ciudadanos.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    probabilidad_mc: Mapped[float] = mapped_column(Float, nullable=False)
    segmento: Mapped[SegmentoVotante] = mapped_column(
        Enum(SegmentoVotante, name="segmento_votante", native_enum=True),
        nullable=False,
    )
    features: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    modelo_version: Mapped[str | None] = mapped_column(String(50), nullable=True)

    scored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    org_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizaciones.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # relationships
    ciudadano = relationship("Ciudadano", lazy="selectin")
    organizacion = relationship("Organizacion", lazy="selectin")
