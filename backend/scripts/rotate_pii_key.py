"""D-DATA-02b — PII encryption key rotation script.

Decrypts all _enc columns with the old key and re-encrypts with the new key.
Transactional: rolls back if any row fails.

Usage:
    python scripts/rotate_pii_key.py --old-key "old-key-here" --new-key "new-key-here"

    Or via env vars:
    PII_OLD_KEY="..." PII_NEW_KEY="..." python scripts/rotate_pii_key.py
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys

# Ensure the backend package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ENC_COLUMNS = [
    "clave_electoral_enc",
    "email_enc",
    "phone_01_enc",
    "phone_02_enc",
    "whatsapp_enc",
    "fecha_nacimiento_enc",
]


async def rotate_key(old_key: str, new_key: str, dry_run: bool = False) -> dict[str, int]:
    """Rotate PII encryption key for all ciudadanos_legacy rows."""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    stats: dict[str, int] = {}

    async with async_session() as db:
        async with db.begin():
            for col in ENC_COLUMNS:
                # Count rows that have data in this column
                count_result = await db.execute(
                    text(f"SELECT COUNT(*) FROM ciudadanos_legacy WHERE {col} IS NOT NULL")
                )
                total = count_result.scalar() or 0

                if total == 0:
                    logger.info("Column %s: 0 rows, skipping", col)
                    stats[col] = 0
                    continue

                if dry_run:
                    logger.info("Column %s: %d rows (DRY RUN, no changes)", col, total)
                    stats[col] = total
                    continue

                # Decrypt with old key, re-encrypt with new key in a single UPDATE
                result = await db.execute(
                    text(f"""
                        UPDATE ciudadanos_legacy
                        SET {col} = pgp_sym_encrypt(
                            pgp_sym_decrypt(CAST({col} AS bytea), :old_key),
                            :new_key
                        )
                        WHERE {col} IS NOT NULL
                    """),
                    {"old_key": old_key, "new_key": new_key},
                )
                rotated = result.rowcount or 0
                logger.info("Column %s: %d/%d rows rotated", col, rotated, total)
                stats[col] = rotated

            # Verify: sample decrypt with new key
            if not dry_run:
                verify_result = await db.execute(
                    text("""
                        SELECT pgp_sym_decrypt(CAST(email_enc AS bytea), :key)
                        FROM ciudadanos_legacy
                        WHERE email_enc IS NOT NULL
                        LIMIT 1
                    """),
                    {"key": new_key},
                )
                sample = verify_result.scalar()
                if sample:
                    logger.info("Verification OK: sample decrypt with new key = '%s...'", sample[:5])
                else:
                    logger.warning("Verification: no email_enc rows to verify (may be OK)")

            if dry_run:
                logger.info("DRY RUN complete — no changes committed")
                await db.rollback()

    await engine.dispose()
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Rotate PII encryption key")
    parser.add_argument("--old-key", default=os.environ.get("PII_OLD_KEY"), help="Current encryption key")
    parser.add_argument("--new-key", default=os.environ.get("PII_NEW_KEY"), help="New encryption key")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be rotated without changing data")
    args = parser.parse_args()

    if not args.old_key or not args.new_key:
        parser.error("Both --old-key and --new-key are required (or set PII_OLD_KEY / PII_NEW_KEY env vars)")

    if len(args.new_key) < 32:
        parser.error("New key must be at least 32 characters")

    if args.old_key == args.new_key:
        parser.error("Old and new keys must be different")

    logger.info("Starting PII key rotation%s...", " (DRY RUN)" if args.dry_run else "")
    stats = asyncio.run(rotate_key(args.old_key, args.new_key, dry_run=args.dry_run))

    total = sum(stats.values())
    logger.info("Done. Total rows rotated: %d", total)
    for col, count in stats.items():
        logger.info("  %s: %d", col, count)


if __name__ == "__main__":
    main()
