"""HITL audit log model — Sprint S1 editor HITL `/dashboard/settings/evaluacion-nlp`.

Audit log inmutable de ediciones HITL: cada UPDATE de `nlp_tono`/`nlp_target`/
`off_topic` desde el editor HITL inserta UN row aquí. Confirmaciones (sin
cambio de label) también se persisten con `from_* == to_*`.

Ver migration: ``backend/migrations/versions/dse_hitl_audit.py``.
"""
from __future__ import annotations

from datetime import datetime

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
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class HitlEditsLog(Base):
    __tablename__ = "hitl_edits_log"
    __table_args__ = (
        CheckConstraint(
            "entity_type IN ('post','comment')",
            name="hitl_edits_log_entity_type_check",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 'post' | 'comment'
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)

    dirigente_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("dirigentes.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Propuesta del sistema (snapshot pre-edit)
    from_tono: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_tono: Mapped[str | None] = mapped_column(String(20), nullable=True)
    from_target: Mapped[str | None] = mapped_column(String(30), nullable=True)
    to_target: Mapped[str | None] = mapped_column(String(30), nullable=True)

    off_topic: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
        default=False,
    )

    actor_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    source: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default="hitl_settings_evaluacion_nlp",
        default="hitl_settings_evaluacion_nlp",
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    edited_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=text("NOW()"),
    )
