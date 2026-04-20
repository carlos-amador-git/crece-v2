"""Sección 6 · OAuth stubs activables (Sprint S5 MVP).

Endpoints stub para Meta (IG + FB Page) · TikTok Business · YouTube
(Google OAuth). Los endpoints devuelven estructura productiva lista pero
persisten filas con ``is_stub=True`` hasta que CEO complete:

    1. Meta Business Manager verificado
    2. App "CRECE v2" creada con redirect URIs configuradas
    3. App Review completo (DIFERIDO-02 · trigger cliente #15)

Cuando ``is_stub=True`` el Plan IA sabe que la plataforma sigue operando en
T3 aunque tenga "token" — es una bandera explícita anti-ilusión.

X NO tiene endpoint OAuth (D-19 permanente T3 vía stack Apify+Scrapling).
"""
from __future__ import annotations

import hashlib
import os
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dirigente import Dirigente
from app.models.oauth_token import OAuthPlatform, OAuthTokenByPlatform

PLATFORMS_OAUTH: frozenset[str] = frozenset(p.value for p in OAuthPlatform)

# Scopes por plataforma (según SPRINT-S5-SCOPING §1.1)
SCOPES_BY_PLATFORM: dict[str, list[str]] = {
    "instagram": ["instagram_basic", "instagram_manage_insights"],
    "facebook_page": [
        "pages_show_list",
        "pages_read_engagement",
        "business_management",
    ],
    "tiktok": ["user.info.basic", "video.list"],
    "youtube": ["youtube.readonly", "yt-analytics.readonly"],
}

_STUB_REDIRECT_BASE = os.environ.get(
    "OAUTH_STUB_REDIRECT_BASE", "https://crece.local/oauth/callback"
)
_STUB_CLIENT_ID = os.environ.get("OAUTH_STUB_CLIENT_ID", "crece-v2-stub-app-id")


class OAuthPlatformInvalidaError(ValueError):
    """Plataforma fuera del set permitido (X rechazado por D-19)."""


def build_init_url(platform: str, dirigente_id: int) -> dict[str, Any]:
    """Construye URL de inicio OAuth (stub MVP, activable post App Review)."""
    platform = platform.lower().strip()
    if platform not in PLATFORMS_OAUTH:
        raise OAuthPlatformInvalidaError(
            f"Plataforma '{platform}' no soporta OAuth en S5 MVP. "
            f"Permitidas: {sorted(PLATFORMS_OAUTH)}. "
            f"X queda permanentemente en T3 (D-19)."
        )

    state = hashlib.sha256(
        f"{dirigente_id}:{platform}:{datetime.now(UTC).isoformat()}".encode()
    ).hexdigest()[:32]
    scopes = SCOPES_BY_PLATFORM[platform]

    if platform in {"instagram", "facebook_page"}:
        base = "https://www.facebook.com/v21.0/dialog/oauth"
    elif platform == "tiktok":
        base = "https://www.tiktok.com/v2/auth/authorize/"
    else:  # youtube
        base = "https://accounts.google.com/o/oauth2/v2/auth"

    redirect_uri = f"{_STUB_REDIRECT_BASE}/{platform}"
    return {
        "platform": platform,
        "dirigente_id": dirigente_id,
        "redirect_url": (
            f"{base}?client_id={_STUB_CLIENT_ID}"
            f"&redirect_uri={redirect_uri}"
            f"&scope={','.join(scopes)}&state={state}"
        ),
        "state": state,
        "scopes": scopes,
        "is_stub": True,
        "stub_reason": (
            "Meta App Review pendiente · DIFERIDO-02 · "
            "endpoint devuelve URL válida estructural · "
            "activación post-contrato cliente firmado"
        ),
    }


async def persist_callback_stub(
    db: AsyncSession,
    *,
    dirigente_id: int,
    platform: str,
    platform_user_id: str | None = None,
    platform_username: str | None = None,
) -> OAuthTokenByPlatform:
    """Crea fila stub en oauth_tokens_by_platform con is_stub=True.

    En producción post App Review este servicio se reemplaza por el canje real
    ``code → short-lived → long-lived`` contra Meta/Google.
    """
    platform = platform.lower().strip()
    if platform not in PLATFORMS_OAUTH:
        raise OAuthPlatformInvalidaError(f"Plataforma '{platform}' inválida")

    dirigente = await db.get(Dirigente, dirigente_id)
    if dirigente is None:
        raise LookupError(f"Dirigente {dirigente_id} no existe")

    # Desactivar tokens activos previos para cumplir el índice parcial único
    existing_q = await db.execute(
        select(OAuthTokenByPlatform).where(
            OAuthTokenByPlatform.dirigente_id == dirigente_id,
            OAuthTokenByPlatform.platform == platform,
            OAuthTokenByPlatform.status == "active",
        )
    )
    for old in existing_q.scalars().all():
        old.status = "expired"
        old.updated_at = datetime.now(UTC)

    token = OAuthTokenByPlatform(
        dirigente_id=dirigente_id,
        org_id=dirigente.org_id,
        platform=platform,
        token_hash=f"stub-{hashlib.sha256(platform.encode()).hexdigest()[:16]}",
        refresh_token_hash=None,
        platform_user_id=platform_user_id,
        platform_username=platform_username,
        scopes=SCOPES_BY_PLATFORM[platform],
        expires_at=datetime.now(UTC) + timedelta(days=60),
        last_refreshed_at=None,
        is_stub=True,
        status="active",
    )
    db.add(token)
    await db.commit()
    await db.refresh(token)
    return token


async def listar_status(
    db: AsyncSession, *, dirigente_id: int
) -> dict[str, Any]:
    """Devuelve estado OAuth por plataforma para un dirigente."""
    dirigente = await db.get(Dirigente, dirigente_id)
    if dirigente is None:
        raise LookupError(f"Dirigente {dirigente_id} no existe")

    q = await db.execute(
        select(OAuthTokenByPlatform).where(
            OAuthTokenByPlatform.dirigente_id == dirigente_id,
            OAuthTokenByPlatform.status == "active",
        )
    )
    tokens = q.scalars().all()

    platforms_status: dict[str, dict[str, Any]] = {}
    for p in PLATFORMS_OAUTH:
        platforms_status[p] = {
            "connected": False,
            "is_stub": None,
            "expires_at": None,
        }

    for tok in tokens:
        platforms_status[tok.platform] = {
            "connected": True,
            "is_stub": tok.is_stub,
            "expires_at": tok.expires_at.isoformat() if tok.expires_at else None,
            "scopes": tok.scopes,
            "platform_username": tok.platform_username,
        }

    # X: D-19 permanente T3
    platforms_status["x"] = {
        "connected": False,
        "is_stub": None,
        "expires_at": None,
        "note": "X permanece T3 permanente (D-19)",
    }

    return {
        "dirigente_id": dirigente_id,
        "platforms": platforms_status,
        "oauth_count": sum(1 for p in tokens if not p.is_stub),
        "stub_count": sum(1 for p in tokens if p.is_stub),
    }
