"""Add data_source column to ciudadanos table.

Revision ID: d5d6d7d8d9e0
Revises: c4c5c6c7c8c9
Create Date: 2026-04-12 06:00:00.000000

The Ciudadano model had data_source defined but no migration created the column.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d5d6d7d8d9e0"
down_revision: str | None = "c4c5c6c7c8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ciudadanos",
        sa.Column("data_source", sa.String(100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ciudadanos", "data_source")
