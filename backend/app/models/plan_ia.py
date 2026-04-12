from __future__ import annotations

import enum
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TipoPlan(str, enum.Enum):
    DIAGNOSTICO = "DIAGNOSTICO"
    CONSOLIDACION = "CONSOLIDACION"
    CRISIS = "CRISIS"
    CONTENIDO = "CONTENIDO"


class EstadoTarea(str, enum.Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"


class PlanIA(Base):
    __tablename__ = "planes_ia"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dirigente_id: Mapped[int] = mapped_column(
        ForeignKey("dirigentes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo: Mapped[TipoPlan] = mapped_column(
        Enum(TipoPlan, name="tipo_plan_enum", create_type=False),
        nullable=False,
    )
    contenido: Mapped[str] = mapped_column(Text, nullable=False)
    modelo_ia: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_usado: Mapped[str] = mapped_column(Text, nullable=False)
    datos_entrada: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    generado_por_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    aprobado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Sprint 3: estructura tipada del plan (reemplaza gradualmente el campo `contenido` libre)
    estructura_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    dirigente = relationship("Dirigente", back_populates="planes")
    generado_por = relationship("User")
    tareas: Mapped[list[PlanTarea]] = relationship(
        "PlanTarea",
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="PlanTarea.orden",
    )


class PlanTarea(Base):
    """Tarea estructurada de un plan IA. Editable por humano, con trazabilidad."""

    __tablename__ = "plan_tareas"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("planes_ia.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    plataforma: Mapped[str | None] = mapped_column(String(50), nullable=True)
    formato: Mapped[str | None] = mapped_column(String(100), nullable=True)
    frecuencia: Mapped[str | None] = mapped_column(String(100), nullable=True)
    responsable: Mapped[str | None] = mapped_column(String(100), nullable=True)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metrica_objetivo: Mapped[str | None] = mapped_column(String(200), nullable=True)
    metrica_valor_objetivo: Mapped[float | None] = mapped_column(nullable=True)
    metrica_valor_real: Mapped[float | None] = mapped_column(nullable=True)
    estado: Mapped[EstadoTarea] = mapped_column(
        Enum(EstadoTarea, name="estado_tarea_enum", create_type=False),
        nullable=False,
        default=EstadoTarea.TODO,
    )
    cambios_historial: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    completado_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
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

    plan: Mapped[PlanIA] = relationship("PlanIA", back_populates="tareas")
