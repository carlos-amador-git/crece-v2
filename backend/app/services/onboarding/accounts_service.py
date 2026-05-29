"""Sección 2 · Input manual URLs (flujo primario D-23).

El cliente pega URLs de sus redes oficiales. El servicio:
    1. Detecta la plataforma con ``Platform.from_url`` (regex hosts en models.social).
    2. Extrae el handle normalizado.
    3. Persiste en ``social_profiles`` con ``data_source='manual_onboarding'``
       e ``is_confirmed=False`` (la confirmación ocurre en Sección 5).

No se inventan handles. Si la URL no matchea ningún host conocido,
se registra en ``invalid_urls`` para que el wizard lo muestre al cliente.
"""
from __future__ import annotations

import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dirigente import Dirigente
from app.models.social import DataSource, Platform, SocialProfile

# Regex por plataforma para extracción del handle desde la URL canonizada.
_HANDLE_PATTERNS: dict[Platform, re.Pattern[str]] = {
    Platform.INSTAGRAM: re.compile(r"instagram\.com/([^/?#]+)", re.IGNORECASE),
    Platform.FACEBOOK: re.compile(r"facebook\.com/([^/?#]+)", re.IGNORECASE),
    Platform.TWITTER: re.compile(r"(?:twitter|x)\.com/([^/?#]+)", re.IGNORECASE),
    Platform.TIKTOK: re.compile(r"tiktok\.com/@?([^/?#]+)", re.IGNORECASE),
    Platform.YOUTUBE: re.compile(
        r"youtube\.com/(?:@|c/|user/|channel/)?([^/?#]+)", re.IGNORECASE
    ),
}


def extract_handle(url: str) -> tuple[Platform | None, str | None]:
    """Devuelve (Platform, handle) normalizado a minúsculas o (None, None) si no matchea."""
    if not url:
        return None, None

    platform = Platform.from_url(url)
    if platform is None:
        return None, None

    pattern = _HANDLE_PATTERNS.get(platform)
    if pattern is None:
        return platform, None

    match = pattern.search(url)
    if match is None:
        return platform, None

    handle = match.group(1).lstrip("@").strip().lower()
    # excluir rutas no-perfil de FB
    if platform is Platform.FACEBOOK and handle in {"profile.php", "pages", "watch"}:
        return platform, None
    return platform, handle


async def persist_manual_accounts(
    db: AsyncSession,
    *,
    dirigente_id: int,
    accounts: list[dict[str, str]],
) -> dict[str, Any]:
    """Inserta o actualiza social_profiles desde input manual del wizard.

    accounts: [{plataforma: "INSTAGRAM", url: "..."}, ...]

    Retorna:
        {
            persisted: [{platform, handle, url, id}, ...],
            invalid_urls: [url no parseables],
            coverage: {plataforma: bool}
        }
    """
    dirigente = await db.get(Dirigente, dirigente_id)
    if dirigente is None:
        raise LookupError(f"Dirigente {dirigente_id} no existe")

    persisted: list[dict[str, Any]] = []
    invalid: list[str] = []
    coverage: dict[str, bool] = {p.value: False for p in Platform}

    for item in accounts:
        url = (item.get("url") or "").strip()
        platform_hint = (item.get("plataforma") or "").upper().strip()
        platform, handle = extract_handle(url)
        # Permitir plataforma declarada si no se detectó por URL
        if platform is None and platform_hint in Platform.__members__:
            platform = Platform(platform_hint)
        if platform is None or handle is None:
            invalid.append(url)
            continue

        # Upsert: buscar profile existente por (dirigente_id, platform)
        existing_q = await db.execute(
            select(SocialProfile).where(
                SocialProfile.dirigente_id == dirigente_id,
                SocialProfile.platform == platform,
            )
        )
        existing = existing_q.scalar_one_or_none()
        if existing is not None:
            existing.handle = handle
            existing.url = url
            existing.data_source = DataSource.MANUAL_ONBOARDING
            existing.is_confirmed = False  # requiere re-confirmación en Sección 5
            profile = existing
        else:
            profile = SocialProfile(
                dirigente_id=dirigente_id,
                platform=platform,
                handle=handle,
                url=url,
                data_source=DataSource.MANUAL_ONBOARDING,
                is_confirmed=False,
            )
            db.add(profile)

        await db.flush()
        persisted.append(
            {
                "id": profile.id,
                "platform": platform.value,
                "handle": handle,
                "url": url,
            }
        )
        coverage[platform.value] = True

    await db.commit()
    return {
        "dirigente_id": dirigente_id,
        "persisted": persisted,
        "invalid_urls": invalid,
        "coverage": coverage,
    }
