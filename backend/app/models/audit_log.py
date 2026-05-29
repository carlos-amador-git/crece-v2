"""AuditLog — registro de operaciones destructivas/modificadoras sensibles.

LFPDPPP art. 32 + S8 Sprint dedicado 2026-05-15. Cross-audit Gemini sugirió
usar SQLAlchemy Event Listeners (no middleware FastAPI) porque el middleware
no captura cascade deletes ni bulk updates.

Lo que guardamos por fila:
- action: DELETE | UPDATE
- model: nombre tabla (str, no FK — sobrevive a refactors)
- record_id: PK del row tocado
- user_id: quién ejecutó (vía ContextVar; NULL si fue Celery/script)
- request_path: ruta HTTP si vino de request
- changes_summary: para UPDATE solo, lista de columnas tocadas (NO valores
  — evita persistir PII en el audit log mismo)
- created_at: timestamp

NO guardamos:
- Row completo (riesgo PII duplicado en logs)
- Valores antes/después (mismo riesgo)
- author_hash, password_hash, ningún campo flagged como PII

Esta tabla NO se purga bajo ARCO — es el propio audit log de cumplimiento.
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    record_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    request_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    changes_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
        default=lambda: datetime.now(UTC),
        index=True,
    )
