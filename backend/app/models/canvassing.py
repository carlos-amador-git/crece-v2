"""Smart Canvassing models — route optimization for field operators."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from geoalchemy2 import Geometry
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class EstadoRuta(StrEnum):
    PENDIENTE = "pendiente"
    EN_PROGRESO = "en_progreso"
    COMPLETADA = "completada"
    CANCELADA = "cancelada"


class ResultadoVisita(StrEnum):
    ENCUESTA_COMPLETADA = "encuesta_completada"
    NO_EN_CASA = "no_en_casa"
    RECHAZO = "rechazo"
    REAGENDADO = "reagendado"
    DIRECCION_INCORRECTA = "direccion_incorrecta"


class RutaCanvassing(Base):
    __tablename__ = "rutas_canvassing"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    org_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizaciones.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    encuestador_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    seccion_id: Mapped[int | None] = mapped_column(
        ForeignKey("secciones_electorales.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    fecha_asignada: Mapped[datetime] = mapped_column(Date, nullable=False)
    estado: Mapped[EstadoRuta] = mapped_column(
        Enum(EstadoRuta, name="estado_ruta", native_enum=True),
        default=EstadoRuta.PENDIENTE,
        nullable=False,
    )
    distancia_total_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    tiempo_estimado_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    puntos_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    puntos_completados: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    geometry_ruta: Mapped[str | None] = mapped_column(
        Geometry(geometry_type="LINESTRING", srid=4326),
        nullable=True,
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
    encuestador = relationship("User", lazy="selectin")
    organizacion = relationship("Organizacion", lazy="selectin")
    seccion = relationship("SeccionElectoral", lazy="selectin")
    puntos = relationship(
        "PuntoRuta",
        back_populates="ruta",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="PuntoRuta.orden",
    )


class PuntoRuta(Base):
    __tablename__ = "puntos_ruta"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ruta_id: Mapped[int] = mapped_column(
        ForeignKey("rutas_canvassing.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ciudadano_id: Mapped[int] = mapped_column(
        ForeignKey("ciudadanos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    orden: Mapped[int] = mapped_column(Integer, nullable=False)
    ubicacion: Mapped[str | None] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326),
        nullable=True,
    )
    visitado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    visitado_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resultado: Mapped[ResultadoVisita | None] = mapped_column(
        Enum(ResultadoVisita, name="resultado_visita", native_enum=True),
        nullable=True,
    )
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)

    # relationships
    ruta = relationship("RutaCanvassing", back_populates="puntos")
    ciudadano = relationship("Ciudadano", lazy="selectin")
