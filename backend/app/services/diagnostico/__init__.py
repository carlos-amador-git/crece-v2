"""Diagnóstico services package.

Legacy:
    - ``calculate_ipd`` (IPD 0-10 composite) — re-exported from ``legacy`` module
      for backwards compatibility with pre-Sprint-S2 callers (plan_generator,
      dashboard, dirigentes endpoints).

Sprint S2 Tier 1 (MASTER §3.1 #01-#10):
    - ``er_service.compute``                  — #01 ER normalizado por estrato
    - ``breakout_service.compute``            — #02 Breakout Scale Brookings
    - ``matrix_2x2_service.compute``          — #03 Matriz 2×2 contenido
    - ``benchmark_service.compute``           — #04 Benchmark competidores (proxies S2)
    - ``sentiment_plutchik_service.compute``  — #05 Plutchik 6 emociones
    - ``crisis_spike_service.compute``        — #06 Crisis Spike detector
    - ``growth_attribution_service.compute``  — #07 Growth time-decay
    - ``sov_service.compute``                 — #08 Share of Voice por tema
    - ``share_like_ratio_service.compute``    — #09 Share/Like ratio
    - ``humanizacion_service.compute``        — #10 Humanización Score

Contract for Tier 1 ``compute`` methods:
    async def compute(db, dirigente_id: int, org_id: int | None) -> dict

Return shape (common):
    {
        "status": "ok" | "insufficient_data",
        "data": {...},           # present when status == "ok"
        "missing": [...],        # present when status == "insufficient_data"
        "bloque": "B0X",
        "bloque_version": "tier1-v1",
        "computed_at": ISO8601 str,
    }
"""
from __future__ import annotations

from app.services.diagnostico.legacy import (
    ENGAGEMENT_BENCHMARKS,
    FOLLOWER_BENCHMARKS,
    PLATFORM_WEIGHTS,
    calculate_ipd,
)

__all__ = [
    "ENGAGEMENT_BENCHMARKS",
    "FOLLOWER_BENCHMARKS",
    "PLATFORM_WEIGHTS",
    "calculate_ipd",
]
