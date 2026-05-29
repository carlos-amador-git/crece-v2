"""YouTube OAuth 2.0 real flow (S2, PLAN-2026-05-13).

⊕ Gateado por CEO (B-OAUTH-YT-GCP-1):
    1. Google Cloud Console → Project "CRECE v2" + YouTube Data API v3 habilitada
    2. OAuth consent screen (External · testing mode)
    3. Credenciales OAuth 2.0 client → entregadas como env vars:
        - ``GOOGLE_OAUTH_CLIENT_ID``
        - ``GOOGLE_OAUTH_CLIENT_SECRET``
        - ``GOOGLE_OAUTH_REDIRECT_BASE`` (default ``http://localhost:8002/api/v1``)
    4. Toggle ``OAUTH_YOUTUBE_ENABLED=true`` activa el path real desde
       ``oauth_service.build_init_url`` / ``persist_callback``.

Mientras ``OAUTH_YOUTUBE_ENABLED=false`` (default) la fila persistida sigue
con ``is_stub=True`` y el endpoint stub clásico responde — esto evita romper
el comportamiento actual hasta que CEO complete GCP setup.

Las funciones aquí NO importan Google client libraries (evita pesada dependencia)
y hablan directo contra los endpoints estándar OAuth 2.0 vía httpx.

Tokens se guardan **cifrados** con pgcrypto a través de ``services.pii``
(mismo patrón que PII LFPDPPP). El plaintext nunca toca disk.
"""
from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dirigente import Dirigente
from app.models.oauth_token import OAuthTokenByPlatform
from app.services.oauth_crypto import encrypt_oauth_pair
from app.services.oauth_state import sign_state

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

# Scopes mínimos solicitados — readonly es suficiente para subs + comments
YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]


class YouTubeOAuthError(RuntimeError):
    """Falla durante OAuth flow real (config, exchange, refresh)."""


def is_enabled() -> bool:
    """Retorna True si OAUTH_YOUTUBE_ENABLED y los creds GCP están presentes."""
    return (
        os.environ.get("OAUTH_YOUTUBE_ENABLED", "false").lower() == "true"
        and bool(os.environ.get("GOOGLE_OAUTH_CLIENT_ID"))
        and bool(os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET"))
    )


def _redirect_uri() -> str:
    base = os.environ.get(
        "GOOGLE_OAUTH_REDIRECT_BASE", "http://localhost:8002/api/v1"
    ).rstrip("/")
    return f"{base}/oauth/callback/youtube"


def build_init_url_real(dirigente_id: int) -> dict[str, Any]:
    """Construye URL OAuth 2.0 real apuntando a Google.

    Devuelve dict con ``state`` que el callback debe validar.
    """
    if not is_enabled():
        raise YouTubeOAuthError(
            "OAuth real YouTube no habilitado · OAUTH_YOUTUBE_ENABLED=false "
            "o falta GOOGLE_OAUTH_CLIENT_ID/SECRET"
        )

    # State firmado con HMAC-SHA256 sobre JWT_SECRET (B-OAUTH-YT-STATE-1).
    # Payload incluye dirigente_id + nonce + ts. Callback valida firma antes de
    # confiar en el dirigente_id que viene del wire.
    state = sign_state(dirigente_id)
    params = {
        "client_id": os.environ["GOOGLE_OAUTH_CLIENT_ID"],
        "redirect_uri": _redirect_uri(),
        "response_type": "code",
        "scope": " ".join(YOUTUBE_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return {
        "platform": "youtube",
        "dirigente_id": dirigente_id,
        "redirect_url": f"{GOOGLE_AUTH_URL}?{urlencode(params)}",
        "state": state,
        "scopes": YOUTUBE_SCOPES,
        "is_stub": False,
    }


async def exchange_code_for_tokens(
    code: str, *, client: httpx.AsyncClient | None = None
) -> dict[str, Any]:
    """Canjea ``code`` (de Google consent) por access_token + refresh_token."""
    if not is_enabled():
        raise YouTubeOAuthError("OAuth real YouTube no habilitado")

    data = {
        "code": code,
        "client_id": os.environ["GOOGLE_OAUTH_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_OAUTH_CLIENT_SECRET"],
        "redirect_uri": _redirect_uri(),
        "grant_type": "authorization_code",
    }
    own_client = client is None
    cl = client or httpx.AsyncClient(timeout=15.0)
    try:
        resp = await cl.post(GOOGLE_TOKEN_URL, data=data)
    finally:
        if own_client:
            await cl.aclose()

    if resp.status_code != 200:
        raise YouTubeOAuthError(
            f"Google token exchange falló · status={resp.status_code} · {resp.text}"
        )
    return resp.json()


async def refresh_access_token(
    refresh_token: str, *, client: httpx.AsyncClient | None = None
) -> dict[str, Any]:
    """Renueva access token con ``refresh_token`` previamente almacenado."""
    if not is_enabled():
        raise YouTubeOAuthError("OAuth real YouTube no habilitado")

    data = {
        "refresh_token": refresh_token,
        "client_id": os.environ["GOOGLE_OAUTH_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_OAUTH_CLIENT_SECRET"],
        "grant_type": "refresh_token",
    }
    own_client = client is None
    cl = client or httpx.AsyncClient(timeout=15.0)
    try:
        resp = await cl.post(GOOGLE_TOKEN_URL, data=data)
    finally:
        if own_client:
            await cl.aclose()

    if resp.status_code != 200:
        raise YouTubeOAuthError(
            f"Google refresh falló · status={resp.status_code} · {resp.text}"
        )
    return resp.json()


async def persist_callback_real(
    db: AsyncSession,
    *,
    dirigente_id: int,
    tokens: dict[str, Any],
    platform_user_id: str | None = None,
    platform_username: str | None = None,
) -> OAuthTokenByPlatform:
    """Guarda tokens reales en BD con ``is_stub=False``.

    Tokens cifrados con pgcrypto pgp_sym_encrypt vía ``services.pii``
    (B-OAUTH-YT-CRYPTO-1 cerrado 2026-05-16). Columnas ``token_enc`` y
    ``refresh_token_enc`` reciben el ciphertext. Las viejas
    ``token_hash`` / ``refresh_token_hash`` quedan NULL desde aquí en
    adelante (mantienen el nombre histórico por compat schema).
    """
    dirigente = await db.get(Dirigente, dirigente_id)
    if dirigente is None:
        raise LookupError(f"Dirigente {dirigente_id} no existe")

    # Expirar tokens activos previos (mismo patrón que stub service)
    existing = await db.execute(
        select(OAuthTokenByPlatform).where(
            OAuthTokenByPlatform.dirigente_id == dirigente_id,
            OAuthTokenByPlatform.platform == "youtube",
            OAuthTokenByPlatform.status == "active",
        )
    )
    for old in existing.scalars().all():
        old.status = "expired"
        old.updated_at = datetime.now(UTC)

    expires_in = int(tokens.get("expires_in") or 3600)
    expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)

    crypto_fields = await encrypt_oauth_pair(
        db,
        access_token=tokens.get("access_token"),
        refresh_token=tokens.get("refresh_token"),
    )

    token = OAuthTokenByPlatform(
        dirigente_id=dirigente_id,
        org_id=dirigente.org_id,
        platform="youtube",
        token_hash=None,
        refresh_token_hash=None,
        token_enc=crypto_fields["token_enc"],
        refresh_token_enc=crypto_fields["refresh_token_enc"],
        crypto_version=crypto_fields["crypto_version"],
        encrypted_at=crypto_fields["encrypted_at"],
        platform_user_id=platform_user_id,
        platform_username=platform_username,
        scopes=YOUTUBE_SCOPES,
        expires_at=expires_at,
        last_refreshed_at=datetime.now(UTC),
        is_stub=False,
        status="active",
    )
    db.add(token)
    await db.commit()
    await db.refresh(token)
    return token
