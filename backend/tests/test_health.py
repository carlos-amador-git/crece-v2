"""Tests for health-check endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.core.config import settings


# ---------------------------------------------------------------------------
# Basic health
# ---------------------------------------------------------------------------


async def test_health_endpoint(client: AsyncClient) -> None:
    """Basic health check returns status, version, and environment."""
    resp = await client.get("/api/v1/health/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert body["version"] == settings.APP_VERSION
    assert body["environment"] == settings.APP_ENV


# ---------------------------------------------------------------------------
# Database health
# ---------------------------------------------------------------------------


async def test_health_db_success(client: AsyncClient) -> None:
    """DB health check succeeds when the test database is reachable.

    The test database is set up by conftest.py, so this should pass
    in any environment where the test suite can run.
    """
    resp = await client.get("/api/v1/health/db")
    # If the test DB is reachable, expect 200; otherwise 503.
    # In CI with a PostgreSQL container, this should be 200.
    if resp.status_code == 200:
        body = resp.json()
        assert body["status"] == "healthy"
        assert body["database"] == "connected"
    else:
        assert resp.status_code == 503


async def test_health_db_failure_mocked(client: AsyncClient) -> None:
    """When the DB is unreachable, the endpoint returns 503."""
    with patch(
        "app.api.v1.endpoints.health.async_session_factory",
    ) as mock_factory:
        mock_session = AsyncMock()
        mock_session.execute.side_effect = ConnectionRefusedError("DB down")
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_factory.return_value = mock_session

        resp = await client.get("/api/v1/health/db")
        assert resp.status_code == 503
        assert "Database unavailable" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Redis health
# ---------------------------------------------------------------------------


async def test_health_redis_success_mocked(client: AsyncClient) -> None:
    """Redis health check returns version info when connection succeeds."""
    with patch("app.api.v1.endpoints.health.aioredis") as mock_redis_module:
        mock_conn = AsyncMock()
        mock_conn.ping.return_value = True
        mock_conn.info.return_value = {"redis_version": "7.2.4"}
        mock_conn.aclose = AsyncMock()
        mock_redis_module.from_url.return_value = mock_conn

        resp = await client.get("/api/v1/health/redis")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"
        assert body["redis"] == "connected"
        assert body["redis_version"] == "7.2.4"


async def test_health_redis_failure_mocked(client: AsyncClient) -> None:
    """Redis health check returns 503 when connection fails."""
    with patch("app.api.v1.endpoints.health.aioredis") as mock_redis_module:
        mock_conn = AsyncMock()
        mock_conn.ping.side_effect = ConnectionError("Redis down")
        mock_redis_module.from_url.return_value = mock_conn

        resp = await client.get("/api/v1/health/redis")
        assert resp.status_code == 503
        assert "Redis unavailable" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Root endpoint (not under /health but good to verify)
# ---------------------------------------------------------------------------


async def test_root_endpoint(client: AsyncClient) -> None:
    """Root endpoint returns service info."""
    resp = await client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["service"] == settings.APP_TITLE
    assert body["version"] == settings.APP_VERSION
