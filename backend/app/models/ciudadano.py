from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class RangoEdad(StrEnum):
    E_18_25 = "18-25"
    E_26_35 = "26-35"
    E_36_45 = "36-45"
    E_46_55 = "46-55"
    E_56_65 = "56-65"
    E_65_PLUS = "65+"


class Genero(StrEnum):
    M = "M"
    F = "F"
    OTRO = "otro"
    NO_ESPECIFICADO = "no_especificado"


class NivelInteres(StrEnum):
    ALTO = "alto"
    MEDIO = "medio"
    BAJO = "bajo"
    DESCONOCIDO = "desconocido"


class IntencionVotoCiudadano(StrEnum):
    MC = "mc"
    MORENA = "morena"
    PAN = "pan"
    PRI = "pri"
    PVEM = "pvem"
    PT = "pt"
    OTRO = "otro"
    INDECISO = "indeciso"
    NO_RESPONDE = "no_responde"


class Escolaridad(StrEnum):
    SIN_ESTUDIOS = "sin_estudios"
    PRIMARIA = "primaria"
    SECUNDARIA = "secundaria"
    PREPARATORIA = "preparatoria"
    UNIVERSIDAD = "universidad"
    POSGRADO = "posgrado"


class Ciudadano(Base):
    __tablename__ = "ciudadanos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    apellido_paterno: Mapped[str] = mapped_column(String(255), nullable=False)
    apellido_materno: Mapped[str | None] = mapped_column(String(255), nullable=True)
    seccion_id: Mapped[int] = mapped_column(
        ForeignKey("secciones_electorales.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    direccion: Mapped[str | None] = mapped_column(String(500), nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    edad_rango: Mapped[RangoEdad] = mapped_column(
        Enum(RangoEdad, name="rango_edad", native_enum=True),
        nullable=False,
    )
    genero: Mapped[Genero] = mapped_column(
        Enum(Genero, name="genero", native_enum=True),
        default=Genero.NO_ESPECIFICADO,
        nullable=False,
    )
    nivel_interes: Mapped[NivelInteres] = mapped_column(
        Enum(NivelInteres, name="nivel_interes", native_enum=True),
        default=NivelInteres.DESCONOCIDO,
        nullable=False,
    )
    es_simpatizante_mc: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    es_promotor: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    registrado_por_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Political intelligence fields
    intencion_voto: Mapped[IntencionVotoCiudadano | None] = mapped_column(
        Enum(IntencionVotoCiudadano, name="intencion_voto_ciudadano", native_enum=True),
        nullable=True,
    )
    programas_sociales: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    problematicas: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Geographic fields
    ubicacion: Mapped[str | None] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326),
        nullable=True,
    )
    colonia: Mapped[str | None] = mapped_column(String(255), nullable=True)
    codigo_postal: Mapped[str | None] = mapped_column(String(5), nullable=True)

    # Demographic segmentation
    escolaridad: Mapped[Escolaridad | None] = mapped_column(
        Enum(Escolaridad, name="escolaridad", native_enum=True),
        nullable=True,
    )

    # Field capture
    foto_ine_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Data provenance
    data_source: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Multi-tenant
    org_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizaciones.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
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

    # relationships
    seccion = relationship("SeccionElectoral", lazy="selectin")
    registrado_por = relationship("User", lazy="selectin")
    organizacion = relationship("Organizacion", lazy="selectin")
    asistencias = relationship(
        "EventoAsistente",
        back_populates="ciudadano",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
