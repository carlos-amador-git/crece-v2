"""OAuth token encryption helpers (B-OAUTH-YT-CRYPTO-1).

Wraps ``app.services.pii.encrypt_value`` / ``decrypt_value`` para tokens OAuth.
Mismo precedente que ciudadanos_legacy (D-DATA-02 LFPDPPP · pgcrypto pgp_sym_*).

Tabla afectada: ``oauth_tokens_by_platform``
- Columnas legacy (plain): ``token_hash`` · ``refresh_token_hash`` (nombre histórico)
- Columnas nuevas (cifradas): ``token_enc`` · ``refresh_token_enc``
- ``crypto_version`` = 0 (plain legacy) | 1 (pgcrypto pgp_sym_encrypt actual)

Lectura — usar ``decrypt_oauth_tokens()`` que prefiere _enc si crypto_version >= 1
y cae a plain solo si la fila no migró aún (script standalone pendiente).
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.oauth_token import OAuthTokenByPlatform
from app.services.pii import decrypt_value, encrypt_value

CURRENT_CRYPTO_VERSION = 1


async def encrypt_oauth_pair(
    db: AsyncSession,
    *,
    access_token: str | None,
    refresh_token: str | None,
) -> dict[str, bytes | int | datetime | None]:
    """Cifra access + refresh tokens. Retorna dict listo para asignar a un
    ``OAuthTokenByPlatform`` (campos ``token_enc``, ``refresh_token_enc``,
    ``crypto_version``, ``encrypted_at``).
    """
    token_enc = await encrypt_value(db, access_token) if access_token else None
    refresh_enc = (
        await encrypt_value(db, refresh_token) if refresh_token else None
    )
    return {
        "token_enc": token_enc,
        "refresh_token_enc": refresh_enc,
        "crypto_version": CURRENT_CRYPTO_VERSION,
        "encrypted_at": datetime.now(UTC),
    }


async def decrypt_oauth_tokens(
    db: AsyncSession, token: OAuthTokenByPlatform
) -> dict[str, str | None]:
    """Lee access + refresh en plaintext. Prefiere columnas _enc; fallback
    a las columnas legacy plain mientras quede algo sin migrar.
    """
    if token.crypto_version >= 1 and token.token_enc is not None:
        access = await decrypt_value(db, token.token_enc)
    else:
        access = token.token_hash
    if token.crypto_version >= 1 and token.refresh_token_enc is not None:
        refresh = await decrypt_value(db, token.refresh_token_enc)
    else:
        refresh = token.refresh_token_hash
    return {"access_token": access, "refresh_token": refresh}
