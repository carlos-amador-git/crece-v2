"""cp3: agregar followers_total a competitor_metrics_monthly

Plan war-room-personal · W1. El dropdown de comparación en Índice de Aceptación
compara métricas externas — followers y engagement. La tabla actual tiene
engagement_rate + posts_count pero falta el snapshot mensual de followers.

Revision ID: cp3
Revises: sc1
Create Date: 2026-05-14
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "cp3"
down_revision = "sc1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "competitor_metrics_monthly",
        sa.Column("followers_total", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("competitor_metrics_monthly", "followers_total")
