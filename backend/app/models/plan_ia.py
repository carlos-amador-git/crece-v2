from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TipoPlan(StrEnum):
    DIAGNOSTICO = "DIAGNOSTICO"
    CONSOLIDACION = "CONSOLIDACION"
    CRISIS = "CRISIS"
    CONTENIDO = "CONTENIDO"


class PlanIA(Base):
    __tablename__ = "planes_ia"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dirigente_id: Mapped[int] = mapped_column(
        ForeignKey("dirigentes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo: Mapped[str] = mapped_column(String(50), nullable=False)
    contenido: Mapped[str] = mapped_column(Text, nullable=False)
    modelo_ia: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_usado: Mapped[str] = mapped_column(Text, nullable=False)
    datos_entrada: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    generado_por_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    aprobado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # relationships
    dirigente = relationship("Dirigente", back_populates="planes", lazy="selectin")
    generado_por = relationship("User", lazy="selectin")
