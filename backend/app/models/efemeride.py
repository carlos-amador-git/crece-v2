"""Efemeride — catálogo de fechas conmemorativas y estratégicas (México 2026).

Diseñado para recurrencia anual (mes + día como Integer, no Date) — D-CALENDARIO-1.

Tipos:
    civica            — días patrios y constitucionales
    internacional     — días ONU/UNESCO de alcance internacional
    social            — temas sociales (mujer, discapacidad, salud mental)
    emocional         — fechas con carga emocional alta (madres, padres, niños)
    familiar          — celebraciones familiares
    comunidad         — temas comunitarios y de valores

Viralidad: indica potencial de engagement en redes (alta/media/baja).
Ámbito: nacional/internacional/regional.
"""
from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EfemerideTipo(StrEnum):
    CIVICA = "civica"
    INTERNACIONAL = "internacional"
    SOCIAL = "social"
    EMOCIONAL = "emocional"
    FAMILIAR = "familiar"
    COMUNIDAD = "comunidad"


class EfemerideViralidad(StrEnum):
    ALTA = "alta"
    MEDIA = "media"
    BAJA = "baja"


class EfemerideAmbito(StrEnum):
    NACIONAL = "nacional"
    INTERNACIONAL = "internacional"
    REGIONAL = "regional"


class Efemeride(Base):
    __tablename__ = "efemerides"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # Recurrencia anual: mes 1-12, día 1-31 (no Date para evitar obsolescencia)
    mes: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    dia: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    titulo: Mapped[str] = mapped_column(String(255), nullable=False)
    tipo: Mapped[EfemerideTipo] = mapped_column(
        Enum(
            EfemerideTipo,
            name="efemeride_tipo",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        index=True,
    )
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    # ideas_politicas: lista de ángulos sugeridos para contenido
    # ej: ["mujeres líderes", "derechos sociales", "medio ambiente"]
    ideas_politicas: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    viralidad: Mapped[EfemerideViralidad] = mapped_column(
        Enum(
            EfemerideViralidad,
            name="efemeride_viralidad",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=EfemerideViralidad.MEDIA,
    )
    ambito: Mapped[EfemerideAmbito] = mapped_column(
        Enum(
            EfemerideAmbito,
            name="efemeride_ambito",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=EfemerideAmbito.NACIONAL,
    )
    is_active: Mapped[bool] = mapped_column(
        nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default="now()",
    )

    def __repr__(self) -> str:
        return f"<Efemeride {self.dia:02d}/{self.mes:02d} · {self.titulo}>"
