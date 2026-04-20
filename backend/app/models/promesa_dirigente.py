"""PromesaDirigente — registro de promesas de campaña por dirigente.

MASTER §3.2 #16. Usado por B16 (Rastreador Promesas de Campaña) para medir
cumplimiento vs posts actuales.

Estados:
    pendiente    — promesa registrada, sin evidencia de cumplimiento
    cumplida     — validada contra evidencia_url o posts recientes
    contradicha  — posts recientes contradicen la promesa
"""
from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PromesaEstado(StrEnum):
    PENDIENTE = "pendiente"
    CUMPLIDA = "cumplida"
    CONTRADICHA = "contradicha"


class PromesaDirigente(Base):
    __tablename__ = "promesas_dirigente"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dirigente_id: Mapped[int] = mapped_column(
        ForeignKey("dirigentes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    texto_promesa: Mapped[str] = mapped_column(Text, nullable=False)
    fecha_compromiso: Mapped[datetime | None] = mapped_column(
        Date, nullable=True
    )
    fecha_realizada: Mapped[datetime | None] = mapped_column(
        Date, nullable=True
    )
    estado: Mapped[PromesaEstado] = mapped_column(
        Enum(
            PromesaEstado,
            name="promesa_estado",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=PromesaEstado.PENDIENTE,
    )
    evidencia_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
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
