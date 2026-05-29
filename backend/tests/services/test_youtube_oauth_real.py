"""Tests S2 · YouTube OAuth real scaffold (PLAN-2026-05-13).

Tests cubren:
- Toggle ``OAUTH_YOUTUBE_ENABLED=false`` (default) → todas las funciones lanzan
  ``YouTubeOAuthError``. No rompe en ausencia de credenciales GCP.
- Con env vars mockeadas → ``build_init_url_real`` produce URL correcta con state.
- ``exchange_code_for_tokens`` con httpx mock → devuelve dict con tokens.
- ``refresh_access_token`` con httpx mock → devuelve nuevo access_token.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.onboarding import youtube_oauth_real as yt


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    """Asegura entorno limpio al inicio de cada test."""
    for key in [
        "OAUTH_YOUTUBE_ENABLED",
        "GOOGLE_OAUTH_CLIENT_ID",
        "GOOGLE_OAUTH_CLIENT_SECRET",
        "GOOGLE_OAUTH_REDIRECT_BASE",
    ]:
        monkeypatch.delenv(key, raising=False)


def test_disabled_by_default():
    assert yt.is_enabled() is False


def test_enabled_requires_all_three_env(monkeypatch):
    monkeypatch.setenv("OAUTH_YOUTUBE_ENABLED", "true")
    assert yt.is_enabled() is False  # falta client_id
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "test-id")
    assert yt.is_enabled() is False  # falta secret
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "test-secret")
    assert yt.is_enabled() is True


def test_build_init_url_disabled_raises():
    with pytest.raises(yt.YouTubeOAuthError):
        yt.build_init_url_real(dirigente_id=1)


def test_build_init_url_real_ok(monkeypatch):
    monkeypatch.setenv("OAUTH_YOUTUBE_ENABLED", "true")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "test-id")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "test-secret")
    monkeypatch.setenv("GOOGLE_OAUTH_REDIRECT_BASE", "http://localhost:8002/api/v1")

    result = yt.build_init_url_real(dirigente_id=42)
    assert result["platform"] == "youtube"
    assert result["dirigente_id"] == 42
    assert result["is_stub"] is False
    assert "accounts.google.com" in result["redirect_url"]
    assert "client_id=test-id" in result["redirect_url"]
    assert (
        "redirect_uri=http%3A%2F%2Flocalhost%3A8002%2Fapi%2Fv1%2Foauth%2Fcallback%2Fyoutube"
        in result["redirect_url"]
    )
    assert "scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fyoutube.readonly" in result["redirect_url"]
    assert len(result["state"]) >= 16


@pytest.mark.asyncio
async def test_exchange_code_for_tokens_ok(monkeypatch):
    monkeypatch.setenv("OAUTH_YOUTUBE_ENABLED", "true")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "test-id")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "test-secret")

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "access_token": "ya29.xyz",
        "refresh_token": "1//abc",
        "expires_in": 3599,
        "token_type": "Bearer",
        "scope": " ".join(yt.YOUTUBE_SCOPES),
    }
    mock_client.post = AsyncMock(return_value=mock_response)

    result = await yt.exchange_code_for_tokens(code="auth-code-xyz", client=mock_client)
    assert result["access_token"] == "ya29.xyz"
    assert result["refresh_token"] == "1//abc"
    mock_client.post.assert_called_once()
    posted_data = mock_client.post.call_args.kwargs["data"]
    assert posted_data["code"] == "auth-code-xyz"
    assert posted_data["grant_type"] == "authorization_code"


@pytest.mark.asyncio
async def test_exchange_code_failure(monkeypatch):
    monkeypatch.setenv("OAUTH_YOUTUBE_ENABLED", "true")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "test-id")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "test-secret")

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = '{"error":"invalid_grant"}'
    mock_client.post = AsyncMock(return_value=mock_response)

    with pytest.raises(yt.YouTubeOAuthError):
        await yt.exchange_code_for_tokens(code="bad-code", client=mock_client)


@pytest.mark.asyncio
async def test_refresh_access_token_ok(monkeypatch):
    monkeypatch.setenv("OAUTH_YOUTUBE_ENABLED", "true")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "test-id")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "test-secret")

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "access_token": "ya29.new",
        "expires_in": 3599,
        "token_type": "Bearer",
    }
    mock_client.post = AsyncMock(return_value=mock_response)

    result = await yt.refresh_access_token(refresh_token="1//old", client=mock_client)
    assert result["access_token"] == "ya29.new"
    posted_data = mock_client.post.call_args.kwargs["data"]
    assert posted_data["refresh_token"] == "1//old"
    assert posted_data["grant_type"] == "refresh_token"
