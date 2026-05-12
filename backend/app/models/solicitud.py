from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TipoSolicitud(StrEnum):
    QUEJA = "queja"
    PROPUESTA = "propuesta"
    SOLICITUD_INFO = "solicitud_info"
    REPORTE_PROBLEMA = "reporte_problema"
    DENUNCIA = "denuncia"
    AGRADECIMIENTO = "agradecimiento"


class EstadoSolicitud(StrEnum):
    RECIBIDA = "recibida"
    EN_PROCESO = "en_proceso"
    ASIGNADA = "asignada"
    RESUELTA = "resuelta"
    CERRADA = "cerrada"
    RECHAZADA = "rechazada"


class CanalOrigen(StrEnum):
    WHATSAPP = "whatsapp"
    WEB = "web"
    PRESENCIAL = "presencial"
    TELEFONO = "telefono"


class SolicitudCiudadana(Base):
    __tablename__ = "solicitudes_ciudadanas"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    org_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizaciones.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    ciudadano_id: Mapped[int | None] = mapped_column(
        ForeignKey("ciudadanos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    seccion_id: Mapped[int | None] = mapped_column(
        ForeignKey("secciones_electorales.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Request details
    tipo: Mapped[TipoSolicitud] = mapped_column(
        Enum(TipoSolicitud, name="tipo_solicitud", native_enum=True),
        nullable=False,
    )
    titulo: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    canal: Mapped[CanalOrigen] = mapped_column(
        Enum(CanalOrigen, name="canal_origen", native_enum=True),
        nullable=False,
    )

    # Location
    ubicacion: Mapped[str | None] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326),
        nullable=True,
    )
    direccion: Mapped[str | None] = mapped_column(String(500), nullable=True)
    colonia: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Categorization (can be auto-classified by NLP)
    categoria: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prioridad: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    # Assignment
    asignado_a_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    dirigente_responsable_id: Mapped[int | None] = mapped_column(
        ForeignKey("dirigentes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Tracking
    estado: Mapped[EstadoSolicitud] = mapped_column(
        Enum(EstadoSolicitud, name="estado_solicitud", native_enum=True),
        default=EstadoSolicitud.RECIBIDA,
        nullable=False,
    )
    respuesta: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_respuesta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # External refs
    chatwoot_conversation_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

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

    # Relationships
    organizacion = relationship("Organizacion", lazy="selectin")
    ciudadano = relationship("Ciudadano", lazy="selectin")
    seccion = relationship("SeccionElectoral", lazy="selectin")
    asignado_a = relationship("User", foreign_keys=[asignado_a_id], lazy="selectin")
    dirigente_responsable = relationship("Dirigente", lazy="selectin")
    seguimientos = relationship(
        "SeguimientoSolicitud",
        back_populates="solicitud",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="SeguimientoSolicitud.created_at.desc()",
    )


class SeguimientoSolicitud(Base):
    __tablename__ = "seguimiento_solicitudes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    solicitud_id: Mapped[int] = mapped_column(
        ForeignKey("solicitudes_ciudadanas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    accion: Mapped[str] = mapped_column(String(100), nullable=False)
    detalle: Mapped[str] = mapped_column(Text, nullable=False)
    estado_anterior: Mapped[str | None] = mapped_column(String(50), nullable=True)
    estado_nuevo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    solicitud = relationship("SolicitudCiudadana", back_populates="seguimientos")
    usuario = relationship("User", lazy="selectin")
