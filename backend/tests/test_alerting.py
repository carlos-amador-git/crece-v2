"""Unit tests for F0.1 Discord webhook alerting.

Plan origen: `.context/PLAN-recuperacion-post-incidente-2026-04-21.md` F0.1 caso B.
Mockea httpx — NO hace requests reales.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.core import alerting
from app.core.alerting import (
    _COLOR_ORANGE,
    _COLOR_RED,
    _COLOR_YELLOW,
    _RATE_LIMIT,
    _build_embed,
    _color_for,
    _is_rate_limited,
    _rate_limit_key,
    send_discord_alert,
)


@pytest.fixture(autouse=True)
def reset_rate_limit_and_warning():
    """Clear in-memory rate limit + missing-url warning flag between tests."""
    _RATE_LIMIT.clear()
    alerting._missing_url_warned = False
    yield
    _RATE_LIMIT.clear()
    alerting._missing_url_warned = False


@pytest.fixture
def mock_async_client():
    """Factory: mock httpx.AsyncClient context manager with a successful POST."""
    def _make(status_code: int = 204, raise_error: Exception | None = None):
        mock_response = MagicMock()
        if raise_error is None:
            mock_response.raise_for_status = MagicMock()
        else:
            mock_response.raise_for_status = MagicMock(side_effect=raise_error)

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cm.__aexit__ = AsyncMock(return_value=False)

        return mock_cm, mock_client
    return _make


class TestColorMapping:
    def test_5xx_red(self):
        assert _color_for("5xx") == _COLOR_RED

    def test_exception_red(self):
        assert _color_for("exception") == _COLOR_RED

    def test_429_orange(self):
        assert _color_for("429") == _COLOR_ORANGE

    def test_uptime_yellow(self):
        assert _color_for("uptime") == _COLOR_YELLOW


class TestRateLimit:
    def test_first_call_not_limited(self):
        assert _is_rate_limited("abc") is False

    def test_second_call_limited(self):
        _is_rate_limited("abc")
        assert _is_rate_limited("abc") is True

    def test_different_keys_independent(self):
        _is_rate_limited("abc")
        assert _is_rate_limited("xyz") is False

    def test_rate_limit_key_deterministic(self):
        k1 = _rate_limit_key("5xx", "GET", "/foo", "title A")
        k2 = _rate_limit_key("5xx", "GET", "/foo", "title A")
        assert k1 == k2

    def test_rate_limit_key_differs_by_path(self):
        k1 = _rate_limit_key("5xx", "GET", "/foo", "title")
        k2 = _rate_limit_key("5xx", "GET", "/bar", "title")
        assert k1 != k2


class TestBuildEmbed:
    def test_title_truncated(self):
        title = "x" * 500
        embed = _build_embed(title, "5xx", {})
        assert len(embed["title"]) == 256

    def test_message_truncated(self):
        details = {"message": "y" * 5000}
        embed = _build_embed("t", "exception", details)
        msg_field = next(f for f in embed["fields"] if f["name"] == "Message")
        assert len(msg_field["value"]) == 1000

    def test_basic_fields_present(self):
        embed = _build_embed(
            "HTTP 500 on /foo",
            "5xx",
            {"method": "GET", "path": "/foo", "status_code": 500},
        )
        names = [f["name"] for f in embed["fields"]]
        assert "Method" in names
        assert "Path" in names
        assert "Status" in names
        assert "Env" in names
        assert "Service" in names

    def test_tunnel_url_field_when_file_exists(self, tmp_path, monkeypatch):
        tunnel_file = tmp_path / "crece-tunnel.url"
        tunnel_file.write_text("https://test-tunnel.trycloudflare.com\n")
        monkeypatch.setattr(alerting, "_TUNNEL_URL_FILE", tunnel_file)

        embed = _build_embed("t", "5xx", {"path": "/foo"})
        tunnel_field = next((f for f in embed["fields"] if f["name"] == "Tunnel URL"), None)
        assert tunnel_field is not None
        assert tunnel_field["value"] == "https://test-tunnel.trycloudflare.com"

    def test_tunnel_url_absent_when_file_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(alerting, "_TUNNEL_URL_FILE", tmp_path / "nonexistent.url")
        embed = _build_embed("t", "5xx", {})
        names = [f["name"] for f in embed["fields"]]
        assert "Tunnel URL" not in names


class TestSendDiscordAlert:
    @pytest.mark.asyncio
    async def test_no_url_noop(self, monkeypatch):
        monkeypatch.setattr(alerting.settings, "DISCORD_WEBHOOK_URL", "")
        result = await send_discord_alert("test", "5xx")
        assert result is False

    @pytest.mark.asyncio
    async def test_no_url_warns_once(self, monkeypatch, caplog):
        monkeypatch.setattr(alerting.settings, "DISCORD_WEBHOOK_URL", "")
        import logging as _log
        with caplog.at_level(_log.WARNING, logger="app.core.alerting"):
            await send_discord_alert("first", "5xx")
            await send_discord_alert("second", "exception")
        warning_msgs = [r for r in caplog.records if "DISCORD_WEBHOOK_URL not configured" in r.message]
        assert len(warning_msgs) == 1  # dedup: una sola advertencia por proceso

    @pytest.mark.asyncio
    async def test_sends_with_url(self, monkeypatch, mock_async_client):
        monkeypatch.setattr(
            alerting.settings, "DISCORD_WEBHOOK_URL",
            "https://discord.com/api/webhooks/fake/token",
        )
        mock_cm, mock_client = mock_async_client()
        with patch("app.core.alerting.httpx.AsyncClient", return_value=mock_cm):
            result = await send_discord_alert(
                "Test alert",
                "5xx",
                {"method": "GET", "path": "/test", "status_code": 500},
            )
        assert result is True
        mock_client.post.assert_called_once()
        # Verify payload structure
        call_args = mock_client.post.call_args
        assert "json" in call_args.kwargs
        payload = call_args.kwargs["json"]
        assert "embeds" in payload
        assert payload["embeds"][0]["color"] == _COLOR_RED

    @pytest.mark.asyncio
    async def test_duplicate_alerts_rate_limited(self, monkeypatch, mock_async_client):
        monkeypatch.setattr(
            alerting.settings, "DISCORD_WEBHOOK_URL",
            "https://discord.com/api/webhooks/fake/token",
        )
        mock_cm, mock_client = mock_async_client()
        with patch("app.core.alerting.httpx.AsyncClient", return_value=mock_cm):
            r1 = await send_discord_alert("same", "5xx", {"method": "GET", "path": "/foo"})
            r2 = await send_discord_alert("same", "5xx", {"method": "GET", "path": "/foo"})
        assert r1 is True
        assert r2 is False  # rate-limited
        assert mock_client.post.call_count == 1

    @pytest.mark.asyncio
    async def test_different_paths_not_rate_limited(self, monkeypatch, mock_async_client):
        monkeypatch.setattr(
            alerting.settings, "DISCORD_WEBHOOK_URL",
            "https://discord.com/api/webhooks/fake/token",
        )
        mock_cm, mock_client = mock_async_client()
        with patch("app.core.alerting.httpx.AsyncClient", return_value=mock_cm):
            r1 = await send_discord_alert("x", "5xx", {"method": "GET", "path": "/foo"})
            r2 = await send_discord_alert("x", "5xx", {"method": "GET", "path": "/bar"})
        assert r1 is True
        assert r2 is True
        assert mock_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_httpx_error_swallowed(self, monkeypatch, mock_async_client):
        monkeypatch.setattr(
            alerting.settings, "DISCORD_WEBHOOK_URL",
            "https://discord.com/api/webhooks/fake/token",
        )
        mock_cm, _ = mock_async_client(raise_error=httpx.HTTPError("boom"))
        with patch("app.core.alerting.httpx.AsyncClient", return_value=mock_cm):
            # Does not raise, returns False
            result = await send_discord_alert("err", "5xx", {"path": "/a"})
        assert result is False

    @pytest.mark.asyncio
    async def test_unexpected_error_swallowed(self, monkeypatch):
        monkeypatch.setattr(
            alerting.settings, "DISCORD_WEBHOOK_URL",
            "https://discord.com/api/webhooks/fake/token",
        )
        # Force a non-httpx unexpected exception
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(side_effect=RuntimeError("unexpected"))
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        with patch("app.core.alerting.httpx.AsyncClient", return_value=mock_cm):
            result = await send_discord_alert("x", "5xx", {"path": "/z"})
        assert result is False
