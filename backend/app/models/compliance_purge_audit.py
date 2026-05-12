"""CompliancePurgeAudit — audit log de purgas ARCO LFPDPPP.

D-18. Cada vez que un admin ejecuta `POST /api/v1/admin/compliance/purge-hash`
para eliminar todo el rastro de un `author_hash_sha256` (comments + embeddings +
vectores), se persiste una fila aquí con contadores por tipo de fila afectada y
la justificación legal (solicitud ARCO del titular, resolución INAI, etc.).

Índices: (author_hash, created_at DESC) y (admin_user_id, created_at DESC).

Esta tabla NO se purga bajo ninguna solicitud ARCO — es el propio audit log de
cumplimiento y debe sobrevivir a las purgas que documenta.
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CompliancePurgeAudit(Base):
    __tablename__ = "compliance_purge_audit"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    admin_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    author_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    rows_deleted_social_comments: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0", default=0
    )
    rows_deleted_social_posts: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0", default=0
    )
    rows_deleted_vectors: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0", default=0
    )
    justificacion: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
        default=lambda: datetime.now(UTC),
    )

    # Relationships
    admin_user = relationship("User", lazy="selectin")
