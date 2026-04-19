"""LLMHealthLog — smoke tests y pings del health-check Ollama dual-mode.

D-21 Coolify dual-mode. Cada corrida del health-checker escribe una fila por
provider (mac_m4_primary / coolify_vps_failover) y layer (ping / inference_warm /
inference_cold / prewarm). El circuit breaker consume las últimas N filas por
provider para decidir switch.

Índices:
    - (provider, created_at DESC) — lecturas por dashboard
    - (status, created_at DESC) WHERE status != 'ok' — alertas por degradación
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LLMHealthLog(Base):
    __tablename__ = "llm_health_log"
    __table_args__ = (
        CheckConstraint(
            "provider IN ('mac_m4_primary','coolify_vps_failover')",
            name="ck_llm_health_provider",
        ),
        CheckConstraint(
            "layer IN ('ping','inference_warm','inference_cold','prewarm')",
            name="ck_llm_health_layer",
        ),
        CheckConstraint(
            "status IN ('ok','degraded','fail','timeout')",
            name="ck_llm_health_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    layer: Mapped[str] = mapped_column(String(20), nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    error_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    model: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
        default=lambda: datetime.now(UTC),
    )
