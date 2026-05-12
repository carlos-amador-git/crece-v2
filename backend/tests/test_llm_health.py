"""Tests for LLM health service (Sprint S1 T8 · D-21 Coolify dual-mode).

Covers:
    - Layer 1 ping: mocked OK response → status=ok inserted in llm_health_log
    - Layer 2 warm inference: mocked timeout → status=timeout inserted
    - Endpoint /api/v1/ops/llm/health returns correct shape given fixture rows
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.llm_health_log import LLMHealthLog
from app.ops import llm_health as svc


# ---------------------------------------------------------------------------
# Redis mock fixture — avoid real Redis dependency in unit tests
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_redis():
    """Patch _get_redis in llm_health service to return an async-mocked client."""
    fake = AsyncMock()
    fake.incr = AsyncMock(return_value=1)
    fake.expire = AsyncMock(return_value=True)
    fake.set = AsyncMock(return_value=True)
    fake.get = AsyncMock(return_value=None)
    fake.delete = AsyncMock(return_value=1)
    fake.aclose = AsyncMock(return_value=None)
    with patch("app.ops.llm_health._get_redis", return_value=fake):
        yield fake


# ---------------------------------------------------------------------------
# Layer 1: ping OK
# ---------------------------------------------------------------------------


async def test_ping_ok_inserts_row(db_session: AsyncSession, mock_redis) -> None:
    """Mocked httpx 200 + gemma3:12b listed → status=ok row persisted."""
    fake_response = AsyncMock()
    fake_response.status_code = 200
    fake_response.json = lambda: {"models": [{"name": "gemma3:12b"}]}

    with patch("app.ops.llm_health.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=fake_response)
        mock_client_cls.return_value = mock_client

        result = await svc.check_ping("mac_m4_primary", "http://fake:11434")

    assert result.status == "ok"
    assert result.model == "gemma3:12b"
    assert result.latency_ms is not None

    # Verify row persisted
    stmt = (
        select(LLMHealthLog)
        .where(LLMHealthLog.provider == "mac_m4_primary")
        .where(LLMHealthLog.layer == "ping")
    )
    res = await db_session.execute(stmt)
    rows = res.scalars().all()
    assert len(rows) >= 1
    assert rows[-1].status == "ok"


# ---------------------------------------------------------------------------
# Layer 2: inference timeout
# ---------------------------------------------------------------------------


async def test_inference_timeout_inserts_row(db_session: AsyncSession, mock_redis) -> None:
    """Mocked httpx.TimeoutException → status=timeout row persisted."""
    with patch("app.ops.llm_health.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("simulated"))
        mock_client_cls.return_value = mock_client

        result = await svc.check_inference_warm(
            "coolify_vps_failover", "http://fake:11434"
        )

    assert result.status == "timeout"
    assert result.error_text and "timeout" in result.error_text.lower()

    stmt = (
        select(LLMHealthLog)
        .where(LLMHealthLog.provider == "coolify_vps_failover")
        .where(LLMHealthLog.layer == "inference_warm")
    )
    res = await db_session.execute(stmt)
    rows = res.scalars().all()
    assert len(rows) >= 1
    assert rows[-1].status == "timeout"


# ---------------------------------------------------------------------------
# Endpoint shape
# ---------------------------------------------------------------------------


async def test_ops_llm_health_endpoint_shape(
    client: AsyncClient, db_session: AsyncSession, mock_redis
) -> None:
    """GET /api/v1/ops/llm/health returns expected keys with fixture rows."""
    # Seed: 1 row per provider in last minute
    now = datetime.now(UTC)
    db_session.add_all([
        LLMHealthLog(
            provider="mac_m4_primary",
            layer="inference_warm",
            latency_ms=8500,
            status="ok",
            model="gemma3:12b",
            created_at=now - timedelta(seconds=30),
        ),
        LLMHealthLog(
            provider="coolify_vps_failover",
            layer="inference_warm",
            latency_ms=12100,
            status="ok",
            model="gemma3:12b",
            created_at=now - timedelta(seconds=30),
        ),
        LLMHealthLog(
            provider="mac_m4_primary",
            layer="prewarm",
            latency_ms=2000,
            status="ok",
            model="gemma3:12b",
            created_at=now - timedelta(minutes=2),
        ),
    ])
    await db_session.commit()

    resp = await client.get("/api/v1/ops/llm/health")
    assert resp.status_code == 200
    body = resp.json()

    # Top-level keys
    assert set(body.keys()) == {"primary", "failover", "circuit_state", "last_prewarm"}

    # Per-provider shape
    for key in ("primary", "failover"):
        provider_data = body[key]
        assert "provider" in provider_data
        assert "status" in provider_data
        assert "last_inference_ms" in provider_data
        assert "last_check" in provider_data
        assert "circuit_breaker" in provider_data

    assert body["primary"]["provider"] == "mac_m4_primary"
    assert body["failover"]["provider"] == "coolify_vps_failover"
    assert body["primary"]["status"] == "ok"
    assert body["primary"]["last_inference_ms"] == 8500
    assert body["failover"]["last_inference_ms"] == 12100
    assert body["circuit_state"] == "primary_active"
    assert body["last_prewarm"] is not None
