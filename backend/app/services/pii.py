"""D-DATA-02 LFPDPPP — PII encryption/decryption helpers (pgcrypto).

Uses PostgreSQL pgcrypto `pgp_sym_encrypt` / `pgp_sym_decrypt` with the
symmetric key from `settings.PII_ENCRYPTION_KEY`. The key NEVER leaves
Python — the DB receives it as a bind param, executes the crypto, and
returns ciphertext (bytes) or plaintext (str).

Design:
- Encryption happens inside the DB (pgcrypto) so the key is only in Python
  memory and in the SQL bind; never in disk-resident SQL or query logs.
- Decryption requires `role=admin` + request logging (see
  `app.core.pii_dependency.require_pii_clearance`).
- Batch helpers minimize round-trips during the initial backfill.

Fields covered in ciudadanos_legacy:
- clave_electoral → clave_electoral_enc  (INE credential)
- email           → email_enc
- phone_01        → phone_01_enc
- phone_02        → phone_02_enc
- whatsapp        → whatsapp_enc
- fecha_nacimiento→ fecha_nacimiento_enc (stored as ISO date text)
"""

from __future__ import annotations

import hashlib
import hmac as _hmac
import logging
from typing import Literal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = logging.getLogger(__name__)


PiiField = Literal[
    "clave_electoral",
    "email",
    "phone_01",
    "phone_02",
    "whatsapp",
    "fecha_nacimiento",
]

_FIELD_TO_ENC_COLUMN: dict[PiiField, str] = {
    "clave_electoral": "clave_electoral_enc",
    "email": "email_enc",
    "phone_01": "phone_01_enc",
    "phone_02": "phone_02_enc",
    "whatsapp": "whatsapp_enc",
    "fecha_nacimiento": "fecha_nacimiento_enc",
}


async def encrypt_value(db: AsyncSession, plaintext: str) -> bytes | None:
    """Encrypt a plaintext string using pgp_sym_encrypt.

    Returns the ciphertext bytes, or None if plaintext is empty.
    """
    if not plaintext:
        return None
    result = await db.execute(
        text("SELECT pgp_sym_encrypt(:pt, :key)"),
        {"pt": plaintext, "key": settings.PII_ENCRYPTION_KEY},
    )
    row = result.scalar()
    return bytes(row) if row else None


async def decrypt_value(db: AsyncSession, ciphertext: bytes) -> str | None:
    """Decrypt a ciphertext blob. Caller is responsible for access control."""
    if ciphertext is None:
        return None
    try:
        result = await db.execute(
            text("SELECT pgp_sym_decrypt(CAST(:ct AS bytea), :key)"),
            {"ct": ciphertext, "key": settings.PII_ENCRYPTION_KEY},
        )
        return result.scalar()
    except Exception as exc:
        logger.error("decrypt_value failed: %s", exc)
        return None


async def backfill_ciudadano_legacy(
    db: AsyncSession, batch_size: int = 500
) -> dict[str, int]:
    """Backfill all ciudadanos_legacy rows that still have NULL in _enc columns.

    Iterates in batches, encrypts the clear values inside the same UPDATE
    statement via a subquery. Idempotent: only touches rows where the
    _enc column is NULL AND the clear column is not NULL.
    """
    stats: dict[str, int] = {}
    for clear_col, enc_col in (
        ("clave_electoral", "clave_electoral_enc"),
        ("email", "email_enc"),
        ("phone_01", "phone_01_enc"),
        ("phone_02", "phone_02_enc"),
        ("whatsapp", "whatsapp_enc"),
    ):
        result = await db.execute(
            text(
                f"""
                UPDATE ciudadanos_legacy
                SET {enc_col} = pgp_sym_encrypt({clear_col}, :key)
                WHERE {enc_col} IS NULL
                  AND {clear_col} IS NOT NULL
                  AND {clear_col} != ''
                """
            ),
            {"key": settings.PII_ENCRYPTION_KEY},
        )
        stats[clear_col] = result.rowcount or 0

    # fecha_nacimiento: cast to text first
    result = await db.execute(
        text(
            """
            UPDATE ciudadanos_legacy
            SET fecha_nacimiento_enc = pgp_sym_encrypt(
                fecha_nacimiento::text, :key
            )
            WHERE fecha_nacimiento_enc IS NULL
              AND fecha_nacimiento IS NOT NULL
            """
        ),
        {"key": settings.PII_ENCRYPTION_KEY},
    )
    stats["fecha_nacimiento"] = result.rowcount or 0

    await db.commit()
    return stats


async def read_pii_fields(
    db: AsyncSession,
    ciudadano_id: int,
    fields: list[PiiField],
) -> dict[str, str | None]:
    """Decrypt and return the requested PII fields for a ciudadano.

    SECURITY: The caller MUST have already gone through `require_pii_clearance`
    to land in this function. This service does NOT enforce role checks —
    that is the dependency's job (see `app.core.pii_dependency`).
    """
    if not fields:
        return {}

    enc_cols = [_FIELD_TO_ENC_COLUMN[f] for f in fields if f in _FIELD_TO_ENC_COLUMN]
    if not enc_cols:
        return {}

    select_parts = ", ".join(
        f"pgp_sym_decrypt(CAST({c} AS bytea), :key) AS {c}" for c in enc_cols
    )
    result = await db.execute(
        text(
            f"SELECT {select_parts} FROM ciudadanos_legacy WHERE id = :id"
        ),
        {"id": ciudadano_id, "key": settings.PII_ENCRYPTION_KEY},
    )
    row = result.first()
    if row is None:
        return {}

    out: dict[str, str | None] = {}
    for field in fields:
        enc_col = _FIELD_TO_ENC_COLUMN[field]
        out[field] = getattr(row, enc_col, None)
    return out


# ── HMAC blind indexes (D-DATA-02f) ─────────────────────────────


def compute_hmac(value: str) -> str:
    """Compute a deterministic HMAC-SHA256 of *value* for blind-index lookup.

    Returns hex-encoded digest (64 chars). The key is PII_ENCRYPTION_KEY
    encoded as UTF-8 bytes. The value is lowercased + stripped before
    hashing so that ``compute_hmac("Foo@Bar.COM")`` equals
    ``compute_hmac("foo@bar.com")``.
    """
    normalised = value.strip().lower()
    return _hmac.new(
        key=settings.PII_ENCRYPTION_KEY.encode("utf-8"),
        msg=normalised.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()


async def backfill_hmac_indexes(db: AsyncSession) -> dict[str, int]:
    """Backfill email_hmac and clave_electoral_hmac for all rows.

    Decrypts each _enc value via pgcrypto, computes the HMAC in Python,
    and writes it back. Processes in batches to limit memory usage.

    Idempotent: skips rows that already have a non-NULL hmac value.

    Returns counts of rows updated per field.
    """
    stats: dict[str, int] = {"email": 0, "clave_electoral": 0}
    batch_size = 500

    for field, enc_col, hmac_col in (
        ("email", "email_enc", "email_hmac"),
        ("clave_electoral", "clave_electoral_enc", "clave_electoral_hmac"),
    ):
        # Count eligible rows
        count_result = await db.execute(
            text(
                f"SELECT COUNT(*) FROM ciudadanos_legacy "
                f"WHERE {hmac_col} IS NULL AND {enc_col} IS NOT NULL"
            )
        )
        total = count_result.scalar() or 0
        if total == 0:
            continue

        logger.info("backfill_hmac: %s — %d rows to process", field, total)

        offset = 0
        while offset < total:
            # Fetch batch: decrypt _enc in-DB, return id + plaintext
            rows = await db.execute(
                text(
                    f"SELECT id, pgp_sym_decrypt(CAST({enc_col} AS bytea), :key) AS val "
                    f"FROM ciudadanos_legacy "
                    f"WHERE {hmac_col} IS NULL AND {enc_col} IS NOT NULL "
                    f"ORDER BY id LIMIT :limit"
                ),
                {"key": settings.PII_ENCRYPTION_KEY, "limit": batch_size},
            )
            batch = rows.fetchall()
            if not batch:
                break

            for row in batch:
                if row.val:
                    digest = compute_hmac(row.val)
                    await db.execute(
                        text(
                            f"UPDATE ciudadanos_legacy "
                            f"SET {hmac_col} = :hmac WHERE id = :id"
                        ),
                        {"hmac": digest, "id": row.id},
                    )
                    stats[field] += 1

            offset += len(batch)

        logger.info("backfill_hmac: %s — %d rows updated", field, stats[field])

    await db.commit()
    return stats
