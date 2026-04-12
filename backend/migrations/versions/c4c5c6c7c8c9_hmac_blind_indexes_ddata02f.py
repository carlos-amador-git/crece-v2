"""D-DATA-02f: HMAC blind indexes for email + clave_electoral

Revision ID: c4c5c6c7c8c9
Revises: b3b4b5b6b7b8
Create Date: 2026-04-11 23:00:00.000000

Adds deterministic HMAC-SHA256 blind index columns to ciudadanos_legacy
so that lookups by email or clave_electoral can be done WITHOUT
decrypting every row. The HMAC is computed in Python (app.services.pii)
using PII_ENCRYPTION_KEY + hmac.new(sha256).

Column type: VARCHAR(64) — hex-encoded SHA-256 = 64 chars.
Both columns are indexed for O(log n) equality lookups.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c4c5c6c7c8c9"
down_revision: Union[str, None] = "b3b4b5b6b7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ciudadanos_legacy",
        sa.Column("email_hmac", sa.String(64), nullable=True),
    )
    op.add_column(
        "ciudadanos_legacy",
        sa.Column("clave_electoral_hmac", sa.String(64), nullable=True),
    )
    op.create_index(
        "ix_ciudadanos_legacy_email_hmac",
        "ciudadanos_legacy",
        ["email_hmac"],
    )
    op.create_index(
        "ix_ciudadanos_legacy_clave_electoral_hmac",
        "ciudadanos_legacy",
        ["clave_electoral_hmac"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ciudadanos_legacy_clave_electoral_hmac",
        table_name="ciudadanos_legacy",
    )
    op.drop_index(
        "ix_ciudadanos_legacy_email_hmac",
        table_name="ciudadanos_legacy",
    )
    op.drop_column("ciudadanos_legacy", "clave_electoral_hmac")
    op.drop_column("ciudadanos_legacy", "email_hmac")
