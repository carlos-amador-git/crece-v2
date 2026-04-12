from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TipoEvento(StrEnum):
    MITIN = "mitin"
    REUNION = "reunion"
    RECORRIDO = "recorrido"
    CAPACITACION = "capacitacion"
    ASAMBLEA = "asamblea"
    OTRO = "otro"


class EstadoEvento(StrEnum):
    PROGRAMADO = "programado"
    EN_CURSO = "en_curso"
    COMPLETADO = "completado"
    CANCELADO = "cancelado"


class Evento(Base):
    __tablename__ = "eventos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    titulo: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    tipo: Mapped[TipoEvento] = mapped_column(
        Enum(TipoEvento, name="tipo_evento", native_enum=True),
        nullable=False,
    )
    fecha_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fecha_fin: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lugar: Mapped[str] = mapped_column(String(500), nullable=False)
    geometry: Mapped[str | None] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326),
        nullable=True,
    )
    seccion_id: Mapped[int | None] = mapped_column(
        ForeignKey("secciones_electorales.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    dirigente_id: Mapped[int | None] = mapped_column(
        ForeignKey("dirigentes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    organizador_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    asistentes_esperados: Mapped[int | None] = mapped_column(Integer, nullable=True)
    asistentes_reales: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Logistics
    recursos: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Political tracking
    nuevos_simpatizantes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ROI calculation
    costo_total: Mapped[float | None] = mapped_column(Float, nullable=True)
    costo_por_adquisicion: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Multi-tenant
    org_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizaciones.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    estado: Mapped[EstadoEvento] = mapped_column(
        Enum(EstadoEvento, name="estado_evento", native_enum=True),
        default=EstadoEvento.PROGRAMADO,
        nullable=False,
    )
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
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

    # relationships
    seccion = relationship("SeccionElectoral", lazy="selectin")
    dirigente = relationship("Dirigente", lazy="selectin")
    organizador = relationship("User", lazy="selectin")
    organizacion = relationship("Organizacion", lazy="selectin")
    asistentes = relationship(
        "EventoAsistente",
        back_populates="evento",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )


class EventoAsistente(Base):
    __tablename__ = "evento_asistentes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    evento_id: Mapped[int] = mapped_column(
        ForeignKey("eventos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ciudadano_id: Mapped[int] = mapped_column(
        ForeignKey("ciudadanos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    confirmado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    asistio: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # relationships
    evento = relationship("Evento", back_populates="asistentes")
    ciudadano = relationship("Ciudadano", back_populates="asistencias")
