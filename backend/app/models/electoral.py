from __future__ import annotations

from datetime import UTC, datetime

import geoalchemy2
from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SeccionElectoral(Base):
    __tablename__ = "secciones_electorales"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    seccion: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    estado: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    distrito_federal: Mapped[str] = mapped_column(String(10), nullable=False)
    distrito_local: Mapped[str] = mapped_column(String(10), nullable=False)
    municipio: Mapped[str] = mapped_column(String(200), nullable=False)
    geometry = mapped_column(
        geoalchemy2.Geometry(
            geometry_type="MULTIPOLYGON", srid=4326, dimension=2
        ),
        nullable=True,
    )


class IntencionVoto(Base):
    __tablename__ = "intencion_voto"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    seccion_id: Mapped[int] = mapped_column(
        ForeignKey("secciones_electorales.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dirigente_id: Mapped[int | None] = mapped_column(
        ForeignKey("dirigentes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    periodo: Mapped[str] = mapped_column(String(50), nullable=False)
    muestra: Mapped[int] = mapped_column(Integer, nullable=False)
    a_favor: Mapped[float] = mapped_column(Float, nullable=False)
    en_contra: Mapped[float] = mapped_column(Float, nullable=False)
    indeciso: Mapped[float] = mapped_column(Float, nullable=False)
    no_responde: Mapped[float] = mapped_column(Float, nullable=False)
    fecha_encuesta: Mapped[datetime] = mapped_column(Date, nullable=False)
    capturado_por_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    seccion: Mapped[SeccionElectoral] = relationship()
    dirigente = relationship("Dirigente")
    capturado_por = relationship("User")
