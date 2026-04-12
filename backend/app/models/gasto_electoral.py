from __future__ import annotations

from datetime import UTC, date, datetime
from enum import StrEnum

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


class CategoriaGastoINE(StrEnum):
    """INE SIF categories for electoral spending."""

    PROPAGANDA = "propaganda"
    OPERATIVOS = "operativos"
    GASTOS_PRODUCCION = "gastos_produccion"
    TRANSPORTE = "transporte"
    ALIMENTACION = "alimentacion"
    ALQUILER_INMUEBLES = "alquiler_inmuebles"
    SERVICIOS_PERSONALES = "servicios_personales"
    PUBLICIDAD_REDES = "publicidad_redes"
    OTROS = "otros"


class TipoAlertaCompliance(StrEnum):
    """Types of compliance alerts tracked by the blindaje module."""

    GASTO_SIN_FACTURA = "gasto_sin_factura"
    GASTO_EXCEDE_TOPE = "gasto_excede_tope"
    BOT_DETECTADO = "bot_detectado"
    CONTENIDO_SIN_ETIQUETA_IA = "contenido_sin_etiqueta_ia"
    VEDA_VIOLACION = "veda_violacion"
    ENGAGEMENT_ANOMALO = "engagement_anomalo"
    TOPE_CAMPANA_PROXIMO = "tope_campana_proximo"


class SeveridadAlerta(StrEnum):
    """Alert severity levels."""

    CRITICA = "critica"
    ALTA = "alta"
    MEDIA = "media"
    BAJA = "baja"


class GastoElectoral(Base):
    __tablename__ = "gastos_electorales"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizaciones.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dirigente_id: Mapped[int | None] = mapped_column(
        ForeignKey("dirigentes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    evento_id: Mapped[int | None] = mapped_column(
        ForeignKey("eventos.id", ondelete="SET NULL"),
        nullable=True,
    )

    concepto: Mapped[str] = mapped_column(String(500), nullable=False)
    categoria: Mapped[CategoriaGastoINE] = mapped_column(
        Enum(CategoriaGastoINE, name="categoria_gasto_ine", native_enum=True),
        nullable=False,
    )
    monto: Mapped[float] = mapped_column(Float, nullable=False)
    fecha_gasto: Mapped[date] = mapped_column(Date, nullable=False)
    proveedor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    factura_uuid: Mapped[str | None] = mapped_column(String(36), nullable=True)
    evidencia_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Compliance approval
    aprobado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    aprobado_por_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # relationships
    organizacion = relationship("Organizacion", lazy="selectin")
    dirigente = relationship("Dirigente", lazy="selectin")
    evento = relationship("Evento", lazy="selectin")
    aprobado_por = relationship("User", lazy="selectin")


class AlertaCompliance(Base):
    __tablename__ = "alertas_compliance"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizaciones.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo: Mapped[TipoAlertaCompliance] = mapped_column(
        Enum(TipoAlertaCompliance, name="tipo_alerta_compliance", native_enum=True),
        nullable=False,
    )
    severidad: Mapped[SeveridadAlerta] = mapped_column(
        Enum(SeveridadAlerta, name="severidad_alerta", native_enum=True),
        nullable=False,
    )
    titulo: Mapped[str] = mapped_column(String(255), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    referencia_tipo: Mapped[str] = mapped_column(String(50), nullable=False)
    referencia_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resuelta: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    resuelta_por_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resuelta_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # relationships
    organizacion = relationship("Organizacion", lazy="selectin")
    resuelta_por = relationship("User", lazy="selectin")
