"""Comments data_source NOT NULL constraint

Sprint Q · A5 fix (AUDIT-INFO-LOGIC-2026-05-15.md).

Antes: 306 rows tenían data_source NULL (14% del total).
Fix manual previo:
  UPDATE social_comments SET data_source = 'legacy-pre-2026-04-13'
  WHERE data_source IS NULL;

Esta migration agrega el constraint NOT NULL para prevenir reincidencia.

Revision ID: sc2
Revises: cs2
"""
from alembic import op
import sqlalchemy as sa


revision = "sc2"
down_revision = "cs2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Safety: si quedó algún NULL por race (scraper concurrente), llenar antes
    # de aplicar el constraint. Idempotente.
    op.execute(
        "UPDATE social_comments "
        "SET data_source = 'legacy-pre-2026-04-13' "
        "WHERE data_source IS NULL"
    )
    op.alter_column(
        "social_comments",
        "data_source",
        existing_type=sa.String(length=64),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "social_comments",
        "data_source",
        existing_type=sa.String(length=64),
        nullable=True,
    )
