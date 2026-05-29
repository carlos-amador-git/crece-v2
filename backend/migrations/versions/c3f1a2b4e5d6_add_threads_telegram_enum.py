"""Add THREADS and TELEGRAM to platform_enum

Revision ID: c3f1a2b4e5d6
Revises: b2dd52dcf65e
Create Date: 2026-04-05T22:51:16.789621
"""
from collections.abc import Sequence

from alembic import op

revision: str = 'c3f1a2b4e5d6'
down_revision: str | None = 'b2dd52dcf65e'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE platform_enum ADD VALUE IF NOT EXISTS 'THREADS'")
    op.execute("ALTER TYPE platform_enum ADD VALUE IF NOT EXISTS 'TELEGRAM'")


def downgrade() -> None:
    # PostgreSQL does not support removing values from enums
    # A full recreate would be needed, but is destructive
    pass
