from __future__ import annotations

import geoalchemy2
from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AlcaldiaCDMX(Base):
    """Catálogo oficial INEGI de las 16 alcaldías de la Ciudad de México.

    Fuente: Marco Geoestadístico INEGI 2023 (CVE_ENT=09).
    Usado por `location_inference.py` para resolver posts a una alcaldía
    via `ST_Contains(geom, point)`.
    """

    __tablename__ = "alcaldias_cdmx"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cvegeo: Mapped[str] = mapped_column(String(5), unique=True, nullable=False, index=True)
    cve_mun: Mapped[str] = mapped_column(String(3), nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    area_km2: Mapped[float | None] = mapped_column(Float, nullable=True)
    perimetro_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    geom = mapped_column(
        geoalchemy2.Geometry(geometry_type="MULTIPOLYGON", srid=4326, dimension=2),
        nullable=False,
    )
