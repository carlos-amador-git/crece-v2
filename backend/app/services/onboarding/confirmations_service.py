"""Sección 5 · Confirmación humana OBLIGATORIA (D-23 regla dura).

El scraping automatizado NUNCA se activa sin que el cliente marque
``confirmed: true`` en una cuenta. Este servicio persiste
``social_profiles.is_confirmed = true`` solo cuando el body lo explicita.

Cualquier intento de llamar con ``confirmed: false`` o sin el flag
devuelve la cuenta como "pending_confirmation" — NO se falla silenciosamente.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dirigente import Dirigente
from app.models.social import Platform, SocialProfile


async def confirmar_cuentas(
    db: AsyncSession,
    *,
    dirigente_id: int,
    confirmed: list[dict[str, Any]],
) -> dict[str, Any]:
    """Marca is_confirmed=True SOLO en cuentas con confirmed=True explícito.

    confirmed: [{platform, handle, confirmed}]

    Retorna:
        {
            dirigente_id,
            activated: [{id, platform, handle}],
            pending: [{platform, handle, reason}],
        }
    """
    dirigente = await db.get(Dirigente, dirigente_id)
    if dirigente is None:
        raise LookupError(f"Dirigente {dirigente_id} no existe")

    activated: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []
    now = datetime.now(UTC)

    for item in confirmed:
        platform_str = (item.get("platform") or "").upper().strip()
        handle = (item.get("handle") or "").strip().lstrip("@").lower()
        is_confirmed = bool(item.get("confirmed"))

        if platform_str not in Platform.__members__:
            pending.append(
                {"platform": platform_str, "handle": handle, "reason": "platform_invalid"}
            )
            continue
        platform = Platform(platform_str)

        if not is_confirmed:
            pending.append(
                {
                    "platform": platform.value,
                    "handle": handle,
                    "reason": "confirmed_flag_missing_or_false",
                }
            )
            continue

        q = await db.execute(
            select(SocialProfile).where(
                SocialProfile.dirigente_id == dirigente_id,
                SocialProfile.platform == platform,
                SocialProfile.handle == handle,
            )
        )
        profile = q.scalar_one_or_none()
        if profile is None:
            pending.append(
                {
                    "platform": platform.value,
                    "handle": handle,
                    "reason": "profile_not_found · correr Sección 2 primero",
                }
            )
            continue

        profile.is_confirmed = True
        profile.last_manual_update = now
        activated.append(
            {
                "id": profile.id,
                "platform": platform.value,
                "handle": handle,
            }
        )

    await db.commit()
    return {
        "dirigente_id": dirigente_id,
        "activated": activated,
        "pending": pending,
        "total_activated": len(activated),
    }
