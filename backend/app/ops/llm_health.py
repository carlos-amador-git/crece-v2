"""LLM Health Check service (Sprint S1 T8 · D-21 Coolify dual-mode).

3-layer health check for Ollama dual-provider (Mac M4 primary / Coolify VPS failover).

Layers:
    - Layer 1 (ping):      GET /api/tags, timeout 2s. ok if HTTP 200 + gemma3:12b in .models
    - Layer 2 (warm):      POST /api/generate, 30 tokens, seed=42. ok<30s, degraded 30-60s, timeout>60s
    - Layer 3 (cold):      same as warm but 180s timeout (only if >4h since last ok check)
    - Prewarm:             10-token inference, keeps model warm, evita cold start 102s

Circuit breaker (Redis-backed):
    - Si provider consecutivamente fail 3+ veces → DOWN en Redis por 5 min
    - Estado accesible: {provider}_circuit_state → "active" | "down"

SLOs (from coolify_failover_smoke.md):
    - Ping p50: <500ms, timeout 2s
    - Inference warm p50: <15s, p95: <30s
    - Inference cold: <120s, timeout 180s
    - Prewarm: cada 4h
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

import httpx
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session_factory
from app.models.llm_health_log import LLMHealthLog

logger = logging.getLogger(__name__)

# ── Provider endpoints ─────────────────────────────────────────────
# Mac M4 local: desde container → host.docker.internal, desde host → localhost
PRIMARY_URL = "http://host.docker.internal:11434"
FAILOVER_URL = "http://163.245.208.96:11434"
MODEL = "gemma3:12b"

ProviderName = Literal["mac_m4_primary", "coolify_vps_failover"]
LayerName = Literal["ping", "inference_warm", "inference_cold", "prewarm"]
StatusName = Literal["ok", "degraded", "fail", "timeout"]

# ── SLO thresholds (ms) ────────────────────────────────────────────
PING_TIMEOUT_S = 2.0
PING_OK_MS = 500

WARM_OK_MS = 30_000        # <30s = ok
WARM_DEGRADED_MS = 60_000  # 30-60s = degraded
WARM_TIMEOUT_S = 60.0

COLD_TIMEOUT_S = 180.0
COLD_IDLE_THRESHOLD_H = 4.0  # Layer 3 fires if last ok >4h ago

PREWARM_TIMEOUT_S = 120.0

# ── Circuit breaker ────────────────────────────────────────────────
CIRCUIT_FAIL_THRESHOLD = 3       # 3 consecutive fails → DOWN
CIRCUIT_DOWN_TTL_S = 300         # DOWN for 5 minutes
CIRCUIT_FAIL_COUNTER_TTL_S = 600 # fails older than 10 min are forgotten


@dataclass
class HealthResult:
    provider: ProviderName
    layer: LayerName
    status: StatusName
    latency_ms: int | None
    error_text: str | None
    model: str | None


# ── Persistence ────────────────────────────────────────────────────

async def _persist(result: HealthResult, session: AsyncSession | None = None) -> None:
    """Insert 1 row into llm_health_log. Opens a session if none provided."""
    row = LLMHealthLog(
        provider=result.provider,
        layer=result.layer,
        latency_ms=result.latency_ms,
        status=result.status,
        error_text=result.error_text,
        model=result.model,
    )
    if session is not None:
        session.add(row)
        await session.flush()
        return
    async with async_session_factory() as s:
        s.add(row)
        await s.commit()


# ── Circuit breaker (Redis) ─────────────────────────────────────────

async def _get_redis() -> aioredis.Redis:
    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)


async def _record_circuit_fail(provider: ProviderName) -> bool:
    """Increment fail counter. If >= threshold → mark DOWN for TTL. Returns True if marked DOWN."""
    r = await _get_redis()
    try:
        key_fails = f"llm_circuit:{provider}:fails"
        key_state = f"llm_circuit:{provider}:state"
        count = await r.incr(key_fails)
        await r.expire(key_fails, CIRCUIT_FAIL_COUNTER_TTL_S)
        if count >= CIRCUIT_FAIL_THRESHOLD:
            await r.set(key_state, "down", ex=CIRCUIT_DOWN_TTL_S)
            logger.warning("Circuit breaker: %s marked DOWN (fails=%d)", provider, count)
            return True
        return False
    finally:
        await r.aclose()


async def _record_circuit_ok(provider: ProviderName) -> None:
    """Reset fail counter and clear DOWN state."""
    r = await _get_redis()
    try:
        await r.delete(f"llm_circuit:{provider}:fails", f"llm_circuit:{provider}:state")
    finally:
        await r.aclose()


async def get_circuit_state(provider: ProviderName) -> str:
    """Returns 'active' (default) or 'down'."""
    r = await _get_redis()
    try:
        state = await r.get(f"llm_circuit:{provider}:state")
        return state or "active"
    finally:
        await r.aclose()


# ── Layer 1: ping ──────────────────────────────────────────────────

async def check_ping(
    provider: ProviderName,
    base_url: str,
    session: AsyncSession | None = None,
) -> HealthResult:
    """Layer 1: GET /api/tags. Verifies endpoint reachable + model available."""
    url = f"{base_url}/api/tags"
    start = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=PING_TIMEOUT_S) as client:
            resp = await client.get(url)
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        if resp.status_code != 200:
            result = HealthResult(
                provider=provider,
                layer="ping",
                status="fail",
                latency_ms=elapsed_ms,
                error_text=f"HTTP {resp.status_code}",
                model=None,
            )
        else:
            data = resp.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            model_present = any(MODEL in m for m in models)
            if not model_present:
                result = HealthResult(
                    provider=provider,
                    layer="ping",
                    status="degraded",
                    latency_ms=elapsed_ms,
                    error_text=f"Model {MODEL} not in .models",
                    model=None,
                )
            elif elapsed_ms > PING_OK_MS:
                result = HealthResult(
                    provider=provider,
                    layer="ping",
                    status="degraded",
                    latency_ms=elapsed_ms,
                    error_text=f"Ping slow: {elapsed_ms}ms > {PING_OK_MS}ms",
                    model=MODEL,
                )
            else:
                result = HealthResult(
                    provider=provider,
                    layer="ping",
                    status="ok",
                    latency_ms=elapsed_ms,
                    error_text=None,
                    model=MODEL,
                )
    except httpx.TimeoutException:
        result = HealthResult(
            provider=provider,
            layer="ping",
            status="timeout",
            latency_ms=int((time.perf_counter() - start) * 1000),
            error_text=f"Ping timeout {PING_TIMEOUT_S}s",
            model=None,
        )
    except Exception as exc:
        result = HealthResult(
            provider=provider,
            layer="ping",
            status="fail",
            latency_ms=int((time.perf_counter() - start) * 1000),
            error_text=f"{type(exc).__name__}: {exc}",
            model=None,
        )

    await _persist(result, session)
    if result.status == "ok":
        await _record_circuit_ok(provider)
    elif result.status in ("fail", "timeout"):
        await _record_circuit_fail(provider)
    return result


# ── Layer 2/3: inference ───────────────────────────────────────────

async def _inference_call(
    provider: ProviderName,
    base_url: str,
    layer: LayerName,
    timeout_s: float,
    num_predict: int = 30,
    prompt: str | None = None,
    session: AsyncSession | None = None,
) -> HealthResult:
    """Shared logic for Layer 2 (warm), Layer 3 (cold), and prewarm."""
    url = f"{base_url}/api/generate"
    body = {
        "model": MODEL,
        "prompt": prompt or "Di solo 'ok' y nada mas.",
        "stream": False,
        "options": {
            "temperature": 0.0,
            "seed": 42,
            "num_predict": num_predict,
        },
    }
    start = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            resp = await client.post(url, json=body)
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        if resp.status_code != 200:
            status: StatusName = "fail"
            err = f"HTTP {resp.status_code}: {resp.text[:200]}"
        else:
            # Classify by latency
            if layer == "inference_warm":
                if elapsed_ms < WARM_OK_MS:
                    status = "ok"
                elif elapsed_ms < WARM_DEGRADED_MS:
                    status = "degraded"
                else:
                    status = "timeout"
                err = None
            elif layer == "inference_cold":
                status = "ok" if elapsed_ms < int(COLD_TIMEOUT_S * 1000) else "timeout"
                err = None
            else:  # prewarm
                status = "ok"
                err = None

        result = HealthResult(
            provider=provider,
            layer=layer,
            status=status,
            latency_ms=elapsed_ms,
            error_text=err,
            model=MODEL,
        )
    except httpx.TimeoutException:
        result = HealthResult(
            provider=provider,
            layer=layer,
            status="timeout",
            latency_ms=int((time.perf_counter() - start) * 1000),
            error_text=f"Inference timeout {timeout_s}s",
            model=MODEL,
        )
    except Exception as exc:
        result = HealthResult(
            provider=provider,
            layer=layer,
            status="fail",
            latency_ms=int((time.perf_counter() - start) * 1000),
            error_text=f"{type(exc).__name__}: {exc}",
            model=MODEL,
        )

    await _persist(result, session)
    if result.status == "ok":
        await _record_circuit_ok(provider)
    elif result.status in ("fail", "timeout"):
        await _record_circuit_fail(provider)
    return result


async def check_inference_warm(
    provider: ProviderName,
    base_url: str,
    session: AsyncSession | None = None,
) -> HealthResult:
    """Layer 2: warm inference. 30 tokens, 60s timeout."""
    return await _inference_call(
        provider, base_url, "inference_warm", WARM_TIMEOUT_S, num_predict=30, session=session
    )


async def check_inference_cold(
    provider: ProviderName,
    base_url: str,
    session: AsyncSession | None = None,
) -> HealthResult:
    """Layer 3: cold inference. Only run when idle >4h. 180s timeout."""
    return await _inference_call(
        provider, base_url, "inference_cold", COLD_TIMEOUT_S, num_predict=30, session=session
    )


async def prewarm(
    provider: ProviderName,
    base_url: str,
    session: AsyncSession | None = None,
) -> HealthResult:
    """Prewarm: 10-token call, keeps model hot. Runs every 4h via cron."""
    return await _inference_call(
        provider,
        base_url,
        "prewarm",
        PREWARM_TIMEOUT_S,
        num_predict=10,
        prompt="ok",
        session=session,
    )


# ── Orchestration ──────────────────────────────────────────────────

PROVIDERS: list[tuple[ProviderName, str]] = [
    ("mac_m4_primary", PRIMARY_URL),
    ("coolify_vps_failover", FAILOVER_URL),
]


async def _last_ok_age_hours(provider: ProviderName) -> float:
    """Returns hours since last 'ok' inference_warm check. Returns large number if never."""
    from sqlalchemy import select

    async with async_session_factory() as s:
        stmt = (
            select(LLMHealthLog.created_at)
            .where(LLMHealthLog.provider == provider)
            .where(LLMHealthLog.status == "ok")
            .where(LLMHealthLog.layer.in_(["inference_warm", "inference_cold", "prewarm"]))
            .order_by(LLMHealthLog.created_at.desc())
            .limit(1)
        )
        res = await s.execute(stmt)
        row = res.scalar_one_or_none()
        if row is None:
            return 999.0
        delta = datetime.now(UTC) - row
        return delta.total_seconds() / 3600.0


async def health_smoke_both() -> dict[ProviderName, list[HealthResult]]:
    """Runs Layer 1 + Layer 2 against both providers. Returns results grouped by provider."""
    results: dict[ProviderName, list[HealthResult]] = {}
    for provider, base_url in PROVIDERS:
        pings = await check_ping(provider, base_url)
        inferences = await check_inference_warm(provider, base_url)
        results[provider] = [pings, inferences]

        # Cold check only if idle >4h AND warm just passed
        if inferences.status == "ok":
            age_h = await _last_ok_age_hours(provider)
            if age_h > COLD_IDLE_THRESHOLD_H:
                logger.info("Running Layer 3 cold check for %s (last ok %.1fh ago)", provider, age_h)
                cold = await check_inference_cold(provider, base_url)
                results[provider].append(cold)

    # Dual-alert: both DOWN → log CRITICAL
    primary_down = await get_circuit_state("mac_m4_primary") == "down"
    failover_down = await get_circuit_state("coolify_vps_failover") == "down"
    if primary_down and failover_down:
        logger.critical(
            "BOTH LLM providers DOWN — primary=%s failover=%s",
            "mac_m4_primary", "coolify_vps_failover"
        )

    return results


async def prewarm_both() -> dict[ProviderName, HealthResult]:
    """Prewarm both providers. Called by cron every 4h."""
    results: dict[ProviderName, HealthResult] = {}
    for provider, base_url in PROVIDERS:
        results[provider] = await prewarm(provider, base_url)
    return results
