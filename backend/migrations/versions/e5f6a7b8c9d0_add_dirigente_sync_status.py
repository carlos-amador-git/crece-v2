"""add dirigente.sync_status + onboarding metadata (S5)

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-04-11 15:30:00.000000

Sprint 5 — Wizard Onboarding Político.
D-S5-01: el endpoint POST /dirigentes/onboard retorna `sync_status=pending`
inmediatamente; el polling de /onboarding-progress actualiza el enum a
medida que la Celery chain progresa.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_STATES = ("pending", "scraping", "analyzing", "calculating_ipd", "ready", "error")


def upgrade() -> None:
    op.execute(
        "CREATE TYPE dirigente_sync_status AS ENUM ("
        + ", ".join(f"'{s}'" for s in _STATES)
        + ")"
    )
    op.add_column(
        "dirigentes",
        sa.Column(
            "sync_status",
            postgresql.ENUM(
                *_STATES,
                name="dirigente_sync_status",
                create_type=False,
            ),
            nullable=False,
            server_default="ready",
        ),
    )
    op.add_column(
        "dirigentes",
        sa.Column("sync_task_id", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "dirigentes",
        sa.Column("sync_error", sa.Text(), nullable=True),
    )
    op.add_column(
        "dirigentes",
        sa.Column(
            "sync_updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_dirigentes_sync_status", "dirigentes", ["sync_status"]
    )


def downgrade() -> None:
    op.drop_index("ix_dirigentes_sync_status", table_name="dirigentes")
    op.drop_column("dirigentes", "sync_updated_at")
    op.drop_column("dirigentes", "sync_error")
    op.drop_column("dirigentes", "sync_task_id")
    op.drop_column("dirigentes", "sync_status")
    op.execute("DROP TYPE dirigente_sync_status")
