from __future__ import annotations

from datetime import UTC, date, datetime
from enum import StrEnum

from geoalchemy2 import Geometry
from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.ciudadano import IntencionVotoCiudadano


class NivelCerteza(StrEnum):
    ALTA = "alta"
    MEDIA = "media"
    BAJA = "baja"


class Encuesta(Base):
    __tablename__ = "encuestas"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ciudadano_id: Mapped[int] = mapped_column(
        ForeignKey("ciudadanos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    encuestador_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    org_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizaciones.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    seccion_id: Mapped[int] = mapped_column(
        ForeignKey("secciones_electorales.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Survey data
    intencion_voto: Mapped[IntencionVotoCiudadano] = mapped_column(
        Enum(
            IntencionVotoCiudadano,
            name="intencion_voto_ciudadano",
            native_enum=True,
            create_type=False,
        ),
        nullable=False,
    )
    nivel_certeza: Mapped[NivelCerteza] = mapped_column(
        Enum(NivelCerteza, name="nivel_certeza", native_enum=True),
        nullable=False,
    )
    motivacion: Mapped[str | None] = mapped_column(Text, nullable=True)
    problematicas_detectadas: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Metadata
    ubicacion_captura: Mapped[str | None] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326),
        nullable=True,
    )
    fecha_encuesta: Mapped[date] = mapped_column(Date, nullable=False)
    duracion_minutos: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # relationships
    ciudadano = relationship("Ciudadano", lazy="selectin")
    encuestador = relationship("User", lazy="selectin")
    seccion = relationship("SeccionElectoral", lazy="selectin")
    organizacion = relationship("Organizacion", lazy="selectin")
