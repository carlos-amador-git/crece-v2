"""Add municipio column to encuestas_publicas (Sprint 7 · 2026-05-09).

Revision ID: encmun1_municipio
Revises: dse_extend_tp_v2
Create Date: 2026-05-09
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "encmun1_municipio"
down_revision: str | None = "dse_extend_tp_v2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "encuestas_publicas",
        sa.Column("municipio", sa.String(length=120), nullable=True),
    )
    op.create_index(
        "ix_encuestas_publicas_ambito_entidad_mun",
        "encuestas_publicas",
        ["ambito", "entidad", "municipio"],
    )


def downgrade() -> None:
    op.drop_index("ix_encuestas_publicas_ambito_entidad_mun", table_name="encuestas_publicas")
    op.drop_column("encuestas_publicas", "municipio")
