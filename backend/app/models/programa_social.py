from __future__ import annotations

from datetime import UTC, date, datetime
from enum import StrEnum

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class NivelGobierno(StrEnum):
    FEDERAL = "federal"
    ESTATAL = "estatal"
    MUNICIPAL = "municipal"


class ProgramaSocial(Base):
    __tablename__ = "programas_sociales"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    dependencia: Mapped[str] = mapped_column(String(255), nullable=False)
    nivel_gobierno: Mapped[NivelGobierno] = mapped_column(
        Enum(NivelGobierno, name="nivel_gobierno", native_enum=True),
        nullable=False,
    )
    presupuesto_anual: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # relationships
    beneficiarios = relationship(
        "ProgramaBeneficiario",
        back_populates="programa",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )


class ProgramaBeneficiario(Base):
    __tablename__ = "programa_beneficiarios"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    programa_id: Mapped[int] = mapped_column(
        ForeignKey("programas_sociales.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    seccion_id: Mapped[int] = mapped_column(
        ForeignKey("secciones_electorales.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    beneficiarios_count: Mapped[int] = mapped_column(Integer, nullable=False)
    periodo: Mapped[str] = mapped_column(String(50), nullable=False)
    fecha_actualizacion: Mapped[date] = mapped_column(Date, nullable=False)
    fuente_datos: Mapped[str] = mapped_column(String(255), nullable=False)

    # relationships
    programa = relationship("ProgramaSocial", back_populates="beneficiarios")
    seccion = relationship("SeccionElectoral", lazy="selectin")
