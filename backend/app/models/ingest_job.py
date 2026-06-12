from __future__ import annotations

import enum
from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class IngestJobStatus(str, enum.Enum):
    """Ciclo de vida de un handoff RADAR→CRECE.

    RECEIVED   → manifest aceptado, job encolado.
    RUNNING    → Celery procesando (descarga + adapters + gates).
    COMPLETED  → ingest OK y gate de cobertura sin huecos.
    PARTIAL    → ingest OK pero gate de cobertura detectó huecos (SOP §2.5).
    TAINTED    → checksums/record_count del manifest no cuadran — NO se ingirió.
    FAILED     → error de ejecución (adapter, MinIO, DB).
    """

    RECEIVED = "RECEIVED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    TAINTED = "TAINTED"
    FAILED = "FAILED"


class IngestJob(Base):
    """Job de ingest de un handoff RADAR (contrato PLAN-2026-06-11-auto-radar-crece).

    `task_uuid` es la clave de idempotencia de transporte: un re-push del mismo
    uuid devuelve el job existente y NO re-procesa (decisión Gemini cross-audit).
    """

    __tablename__ = "ingest_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_uuid: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    dirigente_id: Mapped[int] = mapped_column(
        ForeignKey("dirigentes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[IngestJobStatus] = mapped_column(
        Enum(IngestJobStatus, name="ingest_job_status"),
        default=IngestJobStatus.RECEIVED,
        nullable=False,
    )
    manifest: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Conteos medidos: {"validated_files": N, "db_delta": {tabla: delta}, "coverage_gaps": [...]}
    counts: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
