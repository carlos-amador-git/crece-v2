"""Ops endpoints — LLM health, circuit state, etc. Public read (no auth).

Sprint S1 T8 · D-21 Coolify dual-mode.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.llm_health_log import LLMHealthLog
from app.ops.llm_health import get_circuit_state

router = APIRouter()


async def _provider_status(
    db: AsyncSession, provider: str, since: datetime
) -> dict[str, Any]:
    """Return latest inference_warm row + circuit state for provider in last 5 min."""
    # Latest inference row (any status)
    inf_stmt = (
        select(LLMHealthLog)
        .where(LLMHealthLog.provider == provider)
        .where(LLMHealthLog.layer.in_(["inference_warm", "inference_cold"]))
        .where(LLMHealthLog.created_at >= since)
        .order_by(desc(LLMHealthLog.created_at))
        .limit(1)
    )
    inf_res = await db.execute(inf_stmt)
    inf_row = inf_res.scalar_one_or_none()

    # Latest ping (for last_check)
    ping_stmt = (
        select(LLMHealthLog)
        .where(LLMHealthLog.provider == provider)
        .where(LLMHealthLog.created_at >= since)
        .order_by(desc(LLMHealthLog.created_at))
        .limit(1)
    )
    ping_res = await db.execute(ping_stmt)
    latest_row = ping_res.scalar_one_or_none()

    circuit = await get_circuit_state(provider)  # type: ignore[arg-type]

    # Aggregate status
    if circuit == "down":
        status = "down"
    elif inf_row is None:
        # No data in 5 min window — use latest row status if any
        status = "unknown" if latest_row is None else latest_row.status
    else:
        status = inf_row.status

    return {
        "provider": provider,
        "status": status,
        "last_inference_ms": inf_row.latency_ms if inf_row else None,
        "last_check": latest_row.created_at.isoformat() if latest_row else None,
        "circuit_breaker": circuit,
    }


@router.get("/llm/health")
async def llm_health(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Public health endpoint for LLM dual-provider monitoring.

    Queries last 5 min of llm_health_log grouped by provider.
    """
    since = datetime.now(UTC) - timedelta(minutes=5)

    primary = await _provider_status(db, "mac_m4_primary", since)
    failover = await _provider_status(db, "coolify_vps_failover", since)

    # Circuit state aggregate
    p_down = primary["circuit_breaker"] == "down"
    f_down = failover["circuit_breaker"] == "down"
    if p_down and f_down:
        circuit_state = "both_down"
    elif p_down:
        circuit_state = "failover_active"
    else:
        circuit_state = "primary_active"

    # Latest prewarm timestamp (either provider)
    prewarm_stmt = (
        select(LLMHealthLog.created_at)
        .where(LLMHealthLog.layer == "prewarm")
        .where(LLMHealthLog.status == "ok")
        .order_by(desc(LLMHealthLog.created_at))
        .limit(1)
    )
    pw_res = await db.execute(prewarm_stmt)
    last_prewarm_dt = pw_res.scalar_one_or_none()

    return {
        "primary": primary,
        "failover": failover,
        "circuit_state": circuit_state,
        "last_prewarm": last_prewarm_dt.isoformat() if last_prewarm_dt else None,
    }
