"""Tests para with_backoff decorator (S10 Sprint 2026-05-15)."""
from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from app.scrapers.helpers.backoff import with_backoff


# ─── Fakes que simulan errores transitorios/no transitorios ─────────────


class _FakeResponse:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


class _FakeHTTPError(Exception):
    """Imita requests.HTTPError sin agregar dependencia."""

    def __init__(self, status_code: int, msg: str = "fake") -> None:
        super().__init__(msg)
        self.response = _FakeResponse(status_code)


# ─── Sync tests ─────────────────────────────────────────────────────────


def test_backoff_sync_success_first_try():
    counter = MagicMock(return_value="ok")

    @with_backoff(retries=2, base_delay=0.01)
    def fn():
        return counter()

    assert fn() == "ok"
    assert counter.call_count == 1


def test_backoff_sync_retry_on_503_then_success():
    attempts = {"n": 0}

    @with_backoff(retries=2, base_delay=0.01)
    def fn():
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise _FakeHTTPError(503, "Service Unavailable")
        return "ok"

    assert fn() == "ok"
    assert attempts["n"] == 3


def test_backoff_sync_retry_on_timeout_then_success():
    attempts = {"n": 0}

    @with_backoff(retries=2, base_delay=0.01)
    def fn():
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise TimeoutError("network slow")
        return "ok"

    assert fn() == "ok"
    assert attempts["n"] == 2


def test_backoff_sync_aborts_on_429_no_retry():
    """429 NO debe reintentarse (riesgo shadowban según Gemini)."""
    attempts = {"n": 0}

    @with_backoff(retries=3, base_delay=0.01)
    def fn():
        attempts["n"] += 1
        raise _FakeHTTPError(429, "Too Many Requests")

    with pytest.raises(_FakeHTTPError):
        fn()
    assert attempts["n"] == 1  # un solo intento


def test_backoff_sync_aborts_on_non_transient():
    """ValueError genérico no reintenta."""
    attempts = {"n": 0}

    @with_backoff(retries=2, base_delay=0.01)
    def fn():
        attempts["n"] += 1
        raise ValueError("bug local")

    with pytest.raises(ValueError):
        fn()
    assert attempts["n"] == 1


def test_backoff_sync_exhausts_retries_then_raises():
    """Si todos los retries son 503, al final propaga el último error."""
    attempts = {"n": 0}

    @with_backoff(retries=2, base_delay=0.01)
    def fn():
        attempts["n"] += 1
        raise _FakeHTTPError(502, "Bad Gateway")

    with pytest.raises(_FakeHTTPError):
        fn()
    assert attempts["n"] == 3  # 1 inicial + 2 retries


# ─── Async tests ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_backoff_async_success_first_try():
    @with_backoff(retries=2, base_delay=0.01)
    async def fn():
        return "ok"

    assert await fn() == "ok"


@pytest.mark.asyncio
async def test_backoff_async_retry_then_success():
    attempts = {"n": 0}

    @with_backoff(retries=2, base_delay=0.01)
    async def fn():
        attempts["n"] += 1
        if attempts["n"] < 2:
            raise asyncio.TimeoutError("timeout")
        return "ok"

    assert await fn() == "ok"
    assert attempts["n"] == 2


@pytest.mark.asyncio
async def test_backoff_async_aborts_on_429():
    attempts = {"n": 0}

    @with_backoff(retries=3, base_delay=0.01)
    async def fn():
        attempts["n"] += 1
        raise _FakeHTTPError(429, "blocked")

    with pytest.raises(_FakeHTTPError):
        await fn()
    assert attempts["n"] == 1
