"""RecomendacionPlanIA — modelo de recomendación accionable con ciclo de vida completo.

MASTER §6.3.2 + D-17. Cada recomendación se clasifica en start/stop/continue, tiene
ventana temporal, criterio de éxito medible, principio conductual de respaldo, estado
de ciclo de vida, post ejecutor opcional, y veredicto post-ejecución editable por
cliente con trazabilidad (veredicto_original preservado).

Estados válidos:
    propuesta → aprobada/rechazada/modificada → ejecutada → completada/fallida

Veredicto (post-ejecución):
    exitosa / parcial / fallida · NULL hasta que estado='completada'

No hay seed en Sprint S1. La tabla se puebla en Sprint S4 al generarse la primera
recomendación vía el pipeline de planificación Claude + Gemma.
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class RecomendacionPlanIA(Base):
    __tablename__ = "recomendaciones_plan_ia"
    __table_args__ = (
        CheckConstraint(
            "tipo IN ('start','stop','continue')",
            name="ck_recom_tipo",
        ),
        CheckConstraint(
            "estado IN ('propuesta','aprobada','rechazada','modificada','ejecutada','completada','fallida')",
            name="ck_recom_estado",
        ),
        CheckConstraint(
            "veredicto IS NULL OR veredicto IN ('exitosa','parcial','fallida')",
            name="ck_recom_veredicto",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    plan_ia_id: Mapped[int | None] = mapped_column(
        ForeignKey("planes_ia.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    dirigente_id: Mapped[int] = mapped_column(
        ForeignKey("dirigentes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizaciones.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    accion_texto: Mapped[str] = mapped_column(Text, nullable=False)

    ventana_inicio: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ventana_fin: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ventana_duracion_dias: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="14", default=14
    )

    criterio_exito: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    principio_conductual: Mapped[str | None] = mapped_column(String(100), nullable=True)
    evidencia_respaldo: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="propuesta", default="propuesta"
    )

    post_ejecutor_id: Mapped[int | None] = mapped_column(
        ForeignKey("social_posts.id", ondelete="SET NULL"),
        nullable=True,
    )

    metricas_predichas: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    metricas_observadas: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    veredicto: Mapped[str | None] = mapped_column(String(20), nullable=True)
    veredicto_editado_por_cliente: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false"), default=False
    )
    veredicto_original: Mapped[str | None] = mapped_column(String(20), nullable=True)
    notas_cliente: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    plan = relationship("PlanIA", lazy="selectin")
    dirigente = relationship("Dirigente", lazy="selectin")
    organizacion = relationship("Organizacion", lazy="selectin")
    post_ejecutor = relationship("SocialPost", lazy="selectin")
