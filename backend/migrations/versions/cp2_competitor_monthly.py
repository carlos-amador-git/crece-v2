"""Rename competitor_metrics_weekly → competitor_metrics_monthly.

CEO decisión 2026-05-14: pipeline competidores es mensual, no semanal.
Tabla aún vacía al momento del rename, así que el cambio es cosmético en BD.

Revision ID: cp2
Revises: cp1
Create Date: 2026-05-14
"""
from __future__ import annotations

from alembic import op


revision = "cp2"
down_revision = "cp1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.rename_table("competitor_metrics_weekly", "competitor_metrics_monthly")
    op.alter_column(
        "competitor_metrics_monthly",
        "week_start",
        new_column_name="month_start",
    )
    op.execute(
        "ALTER INDEX ix_competitor_metrics_week RENAME TO ix_competitor_metrics_month"
    )
    op.execute(
        "ALTER INDEX ix_competitor_metrics_comp RENAME TO ix_competitor_metrics_monthly_comp"
    )
    op.execute(
        "ALTER TABLE competitor_metrics_monthly RENAME CONSTRAINT uq_competitor_week TO uq_competitor_month"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE competitor_metrics_monthly RENAME CONSTRAINT uq_competitor_month TO uq_competitor_week"
    )
    op.execute(
        "ALTER INDEX ix_competitor_metrics_monthly_comp RENAME TO ix_competitor_metrics_comp"
    )
    op.execute(
        "ALTER INDEX ix_competitor_metrics_month RENAME TO ix_competitor_metrics_week"
    )
    op.alter_column(
        "competitor_metrics_monthly",
        "month_start",
        new_column_name="week_start",
    )
    op.rename_table("competitor_metrics_monthly", "competitor_metrics_weekly")
