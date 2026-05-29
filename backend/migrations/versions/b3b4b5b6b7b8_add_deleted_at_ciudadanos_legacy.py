"""D.12 — add deleted_at to ciudadanos_legacy for LFPDPPP right-to-delete

Revision ID: b3b4b5b6b7b8
Revises: f6a7b8c9d0e1
Create Date: 2026-04-11 22:00:00.000000

Adds `deleted_at TIMESTAMP WITH TIME ZONE NULL` to ciudadanos_legacy
for soft-delete support per LFPDPPP (Ley Federal de Proteccion de
Datos Personales en Posesion de los Particulares) right-to-erasure.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b3b4b5b6b7b8"
down_revision: str | None = "b2b3b4b5b6b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ciudadanos_legacy",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_ciudadanos_legacy_deleted_at",
        "ciudadanos_legacy",
        ["deleted_at"],
        postgresql_where=sa.text("deleted_at IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_ciudadanos_legacy_deleted_at", table_name="ciudadanos_legacy")
    op.drop_column("ciudadanos_legacy", "deleted_at")
