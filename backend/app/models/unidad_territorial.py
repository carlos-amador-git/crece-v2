from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UnidadTerritorial(Base):
    """Unidad territorial electoral — grano sección × colonia/pueblo.

    Imported from CRECE Oracle APEX legacy (`master_catalogo.csv`).
    5,548 rows across the 16 CDMX alcaldías. Combines INE (sección,
    distrito, lista nominal), INEGI (estrato, grado promedio estudios) y
    segmentación política del CRECE original (categoría P1..P5,
    volatilidad 0-100).
    """

    __tablename__ = "unidades_territoriales"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    legacy_id: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    alcaldia_id: Mapped[int | None] = mapped_column(
        ForeignKey("alcaldias_cdmx.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    alcaldia_nombre: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    clave_unidad_territorial: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )
    cabecera_nombre: Mapped[str | None] = mapped_column(String(200), nullable=True)
    parcial_completa: Mapped[str | None] = mapped_column(String(20), nullable=True)
    seccion_2024: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    dtto_federal_2024: Mapped[str | None] = mapped_column(String(10), nullable=True)
    dtto_local_2024: Mapped[str | None] = mapped_column(String(10), nullable=True)
    circunscripcion_2024: Mapped[str | None] = mapped_column(
        String(10), nullable=True, index=True
    )
    circunscripcion_2022: Mapped[str | None] = mapped_column(String(10), nullable=True)
    estrato: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    nivel_socioeconomico_resumen: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    grado_promedio_estudios: Mapped[float | None] = mapped_column(Float, nullable=True)
    p_viv_inter: Mapped[float | None] = mapped_column(Float, nullable=True)
    lista_nominal_2023: Mapped[int | None] = mapped_column(Integer, nullable=True)
    volatilidad: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    categoria: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)

    alcaldia = relationship("AlcaldiaCDMX", lazy="noload")
