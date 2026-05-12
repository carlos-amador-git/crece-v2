"""add plan_tareas and estructura_json

Revision ID: 402acb98d2d4
Revises: d4e7a2c1b8f3
Create Date: 2026-04-11 02:29:01.438660

Sprint 3: structured plan support. Adds:
    - ENUM `estado_tarea_enum` (TODO, IN_PROGRESS, DONE)
    - TABLE `plan_tareas` (editable tasks attached to a plan)
    - COLUMN `planes_ia.estructura_json` (JSONB, original LLM output)

NOTE: autogenerate also detected drift between the Python models and the
dev DB (embedding column on social_posts, last_scraped_at on
competidor_social_profiles, secciones_electorales unique constraint).
Those are NOT part of Sprint 3 and are intentionally EXCLUDED from this
migration. They represent pre-existing drift that should be addressed
in a dedicated drift-reconciliation migration.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "402acb98d2d4"
down_revision: Union[str, None] = "d4e7a2c1b8f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. ENUM used by plan_tareas.estado
    estado_tarea_enum = postgresql.ENUM(
        "TODO", "IN_PROGRESS", "DONE", name="estado_tarea_enum"
    )
    estado_tarea_enum.create(op.get_bind(), checkfirst=True)

    # 2. planes_ia.estructura_json — stores the raw LLM JSON output
    op.add_column(
        "planes_ia",
        sa.Column(
            "estructura_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )

    # 3. plan_tareas table
    op.create_table(
        "plan_tareas",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("titulo", sa.String(length=200), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("plataforma", sa.String(length=50), nullable=True),
        sa.Column("formato", sa.String(length=100), nullable=True),
        sa.Column("frecuencia", sa.String(length=100), nullable=True),
        sa.Column("responsable", sa.String(length=100), nullable=True),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metrica_objetivo", sa.String(length=200), nullable=True),
        sa.Column("metrica_valor_objetivo", sa.Float(), nullable=True),
        sa.Column("metrica_valor_real", sa.Float(), nullable=True),
        sa.Column(
            "estado",
            postgresql.ENUM(
                "TODO",
                "IN_PROGRESS",
                "DONE",
                name="estado_tarea_enum",
                create_type=False,
            ),
            nullable=False,
            server_default="TODO",
        ),
        sa.Column(
            "cambios_historial",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("completado_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["plan_id"], ["planes_ia.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_plan_tareas_plan_id"),
        "plan_tareas",
        ["plan_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_plan_tareas_plan_id"), table_name="plan_tareas")
    op.drop_table("plan_tareas")
    op.drop_column("planes_ia", "estructura_json")

    estado_tarea_enum = postgresql.ENUM(
        "TODO", "IN_PROGRESS", "DONE", name="estado_tarea_enum"
    )
    estado_tarea_enum.drop(op.get_bind(), checkfirst=True)
