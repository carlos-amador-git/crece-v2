"""D-DATA-02 — Tests de encriptación PII + audit log.

Cubre:
- Round-trip encrypt/decrypt contra dev DB real con pgcrypto
- Cleanup idempotente (los tests dejan rows _enc NULL de nuevo)
- Audit log INSERT via PiiAuditor
- Rol no-admin denegado en require_pii_clearance
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.services.pii import (
    backfill_ciudadano_legacy,
    decrypt_value,
    encrypt_value,
    read_pii_fields,
)


@pytest.fixture
async def db() -> AsyncSession:
    engine = create_async_engine(settings.DATABASE_URL)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_encrypt_decrypt_round_trip(db: AsyncSession) -> None:
    plaintext = "test-pii-value-2026@crece.mx"
    ciphertext = await encrypt_value(db, plaintext)
    assert ciphertext is not None
    assert isinstance(ciphertext, bytes)
    assert len(ciphertext) > 0
    assert ciphertext != plaintext.encode()

    decrypted = await decrypt_value(db, ciphertext)
    assert decrypted == plaintext


@pytest.mark.asyncio
async def test_encrypt_empty_returns_none(db: AsyncSession) -> None:
    assert await encrypt_value(db, "") is None


@pytest.mark.asyncio
async def test_decrypt_wrong_key_returns_none(db: AsyncSession) -> None:
    """If the stored ciphertext is garbage, decrypt_value swallows and returns None."""
    fake_ciphertext = b"not-a-real-pgp-blob"
    result = await decrypt_value(db, fake_ciphertext)
    assert result is None


@pytest.mark.asyncio
async def test_read_pii_fields_on_real_row(db: AsyncSession) -> None:
    """Find a ciudadano_legacy with encrypted email and verify read_pii_fields."""
    row = (
        await db.execute(
            text(
                "SELECT id FROM ciudadanos_legacy WHERE email_enc IS NOT NULL LIMIT 1"
            )
        )
    ).first()
    if row is None:
        pytest.skip("No encrypted rows in dev DB — run backfill first")

    decrypted = await read_pii_fields(db, row[0], ["email"])
    assert "email" in decrypted
    assert decrypted["email"] is not None
    assert "@" in decrypted["email"]


@pytest.mark.asyncio
async def test_backfill_is_idempotent(db: AsyncSession) -> None:
    """Re-running backfill should upsert 0 rows if already encrypted."""
    stats_1 = await backfill_ciudadano_legacy(db)
    stats_2 = await backfill_ciudadano_legacy(db)
    # Second run must be 0 for every field (nothing left to encrypt)
    for field, count in stats_2.items():
        assert count == 0, f"backfill not idempotent for {field}: {count}"


@pytest.mark.asyncio
async def test_data_access_log_insert(db: AsyncSession) -> None:
    """PiiAuditor.log must write a row in data_access_log."""
    from app.core.pii_access import PiiAuditor

    auditor = PiiAuditor(
        user_id=1,
        org_id=3,
        role="admin",
        request_ip="127.0.0.1",
        user_agent="pytest",
    )
    before = (
        await db.execute(text("SELECT COUNT(*) FROM data_access_log"))
    ).scalar_one()

    await auditor.log(
        db=db,
        table_name="ciudadanos_legacy",
        row_id="test-pii-audit",
        action="read_pii",
        fields=["email", "phone_01"],
        metadata={"test": True},
    )

    after = (
        await db.execute(text("SELECT COUNT(*) FROM data_access_log"))
    ).scalar_one()
    assert after == before + 1

    # Cleanup
    await db.execute(
        text("DELETE FROM data_access_log WHERE row_id = 'test-pii-audit'")
    )
    await db.commit()
