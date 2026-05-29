"""Migra filas existentes de oauth_tokens_by_platform al schema cifrado.

Recomendación Gemini cross-audit (2026-05-16): migración de datos separada del
Alembic schema-only para tener acceso completo al servicio
``app.services.pii.encrypt_value`` con todo el contexto de la app.

Ejecución:
    docker compose exec backend python -m scripts.encrypt_existing_oauth_tokens

Lógica:
- Selecciona filas con ``crypto_version=0`` y ``token_hash`` o
  ``refresh_token_hash`` no nulos.
- Encripta cada token plain → escribe a ``token_enc`` / ``refresh_token_enc``.
- Marca ``crypto_version=1`` + ``encrypted_at=NOW()``.
- DESPUÉS de verificar (en otra sesión humana), poner los plain en NULL.
  Este script NO los borra, solo migra. Borrado = paso separado para evitar
  pérdida si la encrypción falla a media corrida.

Idempotente: si una fila ya tiene ``crypto_version >= 1`` se salta.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.database import async_session_factory
from app.models.oauth_token import OAuthTokenByPlatform
from app.services.pii import encrypt_value

logger = logging.getLogger(__name__)


async def migrate() -> dict[str, int]:
    stats: dict[str, int] = {
        "selected": 0,
        "migrated": 0,
        "skipped_no_plain": 0,
        "errors": 0,
    }
    async with async_session_factory() as db:
        rows = await db.execute(
            select(OAuthTokenByPlatform).where(
                OAuthTokenByPlatform.crypto_version == 0
            )
        )
        for token in rows.scalars().all():
            stats["selected"] += 1
            access_plain = token.token_hash
            refresh_plain = token.refresh_token_hash
            if not access_plain and not refresh_plain:
                stats["skipped_no_plain"] += 1
                continue
            try:
                if access_plain:
                    token.token_enc = await encrypt_value(db, access_plain)
                if refresh_plain:
                    token.refresh_token_enc = await encrypt_value(
                        db, refresh_plain
                    )
                token.crypto_version = 1
                token.encrypted_at = datetime.now(UTC)
                stats["migrated"] += 1
                print(
                    f"  ✓ token id={token.id} dirigente_id={token.dirigente_id} "
                    f"platform={token.platform}"
                )
            except Exception as exc:
                stats["errors"] += 1
                logger.exception(
                    "Encryption failed for token id=%s: %s", token.id, exc
                )
        await db.commit()
    return stats


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    print("=" * 60)
    print("OAuth token encryption migration (B-OAUTH-YT-CRYPTO-1)")
    print("=" * 60)
    stats = await migrate()
    print()
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print()
    if stats["errors"] > 0:
        print("⚠ Algunas filas fallaron. Revisar logs antes de NULL-out plain.")
    elif stats["migrated"] > 0:
        print(
            "✓ Migración OK. Para terminar (en sesión humana posterior, "
            "tras smoke-test):"
        )
        print(
            "  UPDATE oauth_tokens_by_platform "
            "SET token_hash=NULL, refresh_token_hash=NULL "
            "WHERE crypto_version >= 1;"
        )
    else:
        print("Nothing to migrate.")


if __name__ == "__main__":
    asyncio.run(main())
