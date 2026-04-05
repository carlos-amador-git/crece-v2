from __future__ import annotations

from datetime import UTC, date, datetime

from geoalchemy2 import Geometry
from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SeccionElectoral(Base):
    __tablename__ = "secciones_electorales"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    seccion: Mapped[str] = mapped_column(String(10), nullable=False, unique=True, index=True)
    estado: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    distrito_federal: Mapped[str] = mapped_column(String(10), nullable=False)
    distrito_local: Mapped[str] = mapped_column(String(10), nullable=False)
    municipio: Mapped[str] = mapped_column(String(200), nullable=False)
    geometry = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=4326), nullable=True
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
    fecha_encuesta: Mapped[date] = mapped_column(Date, nullable=False)
    capturado_por_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # relationships
    seccion = relationship("SeccionElectoral", lazy="selectin")
    dirigente = relationship("Dirigente", lazy="selectin")
    capturado_por = relationship("User", lazy="selectin")
