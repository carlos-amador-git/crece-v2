from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class EstadoCampana(StrEnum):
    BORRADOR = "borrador"
    PROGRAMADA = "programada"
    ENVIANDO = "enviando"
    COMPLETADA = "completada"
    CANCELADA = "cancelada"


class TipoCampana(StrEnum):
    MASIVA = "masiva"
    SEGMENTADA = "segmentada"
    INDIVIDUAL = "individual"


class EstadoMensaje(StrEnum):
    PENDIENTE = "pendiente"
    ENVIADO = "enviado"
    ENTREGADO = "entregado"
    LEIDO = "leido"
    RESPONDIDO = "respondido"
    FALLIDO = "fallido"


class Campana(Base):
    __tablename__ = "campanas"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizaciones.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nombre: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    tipo: Mapped[TipoCampana] = mapped_column(
        Enum(TipoCampana, name="tipo_campana", native_enum=True),
        nullable=False,
    )
    plantilla_mensaje: Mapped[str] = mapped_column(Text, nullable=False)
    variables_plantilla: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    estado: Mapped[EstadoCampana] = mapped_column(
        Enum(EstadoCampana, name="estado_campana", native_enum=True),
        default=EstadoCampana.BORRADOR,
        nullable=False,
    )
    fecha_programada: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    fecha_envio: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fecha_completada: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    creado_por_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    dirigente_id: Mapped[int | None] = mapped_column(
        ForeignKey("dirigentes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ── Delivery counters ────────────────────────────────
    total_destinatarios: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_enviados: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_entregados: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_leidos: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_respondidos: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # ── Timestamps ───────────────────────────────────────
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

    # ── Relationships ────────────────────────────────────
    organizacion = relationship("Organizacion", lazy="selectin")
    creado_por = relationship("User", lazy="selectin")
    dirigente = relationship("Dirigente", lazy="selectin")
    segmentos = relationship(
        "CampanaSegmento",
        back_populates="campana",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    mensajes = relationship(
        "CampanaMensaje",
        back_populates="campana",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )


class CampanaSegmento(Base):
    __tablename__ = "campana_segmentos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    campana_id: Mapped[int] = mapped_column(
        ForeignKey("campanas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Segment filters ──────────────────────────────────
    filtro_seccion_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    filtro_intencion_voto: Mapped[str | None] = mapped_column(String(50), nullable=True)
    filtro_edad_rango: Mapped[str | None] = mapped_column(String(20), nullable=True)
    filtro_escolaridad: Mapped[str | None] = mapped_column(String(50), nullable=True)
    filtro_es_simpatizante: Mapped[bool | None] = mapped_column(nullable=True)
    filtro_es_promotor: Mapped[bool | None] = mapped_column(nullable=True)
    filtro_score_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    filtro_score_max: Mapped[float | None] = mapped_column(Float, nullable=True)

    ciudadanos_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # ── Relationships ────────────────────────────────────
    campana = relationship("Campana", back_populates="segmentos")


class CampanaMensaje(Base):
    __tablename__ = "campana_mensajes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    campana_id: Mapped[int] = mapped_column(
        ForeignKey("campanas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ciudadano_id: Mapped[int] = mapped_column(
        ForeignKey("ciudadanos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    telefono: Mapped[str] = mapped_column(String(20), nullable=False)
    estado: Mapped[EstadoMensaje] = mapped_column(
        Enum(EstadoMensaje, name="estado_mensaje", native_enum=True),
        default=EstadoMensaje.PENDIENTE,
        nullable=False,
    )
    chatwoot_message_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    # ── Delivery timestamps ──────────────────────────────
    enviado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    entregado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    leido_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_mensaje: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # ── Relationships ────────────────────────────────────
    campana = relationship("Campana", back_populates="mensajes")
    ciudadano = relationship("Ciudadano", lazy="selectin")
