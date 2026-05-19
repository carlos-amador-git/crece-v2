"""framework_matrix_defaults.contexto — matriz v2 discrimina post vs comment.

Revision ID: ds04_matrix_context
Revises: ds03_sc_data_source
Create Date: 2026-04-14 14:05:00.000000

Añade columna ``contexto VARCHAR(20) NOT NULL DEFAULT 'post_dirigente'`` y
redefine el unique constraint para incluirla.

Motivación: la matriz v1 (32 reglas) se calibró para posts del dirigente. Al
aplicarse a comments de terceros, 6 reglas tienen semántica divergente + faltan
14 reglas para ``target=dirigente`` (follower→autor del post). v2 sube a 52.

Valores permitidos en ``contexto``:
- ``post_dirigente`` — contenido emitido por el dirigente (v1 default)
- ``comment_tercero`` — contenido emitido por un follower/usuario en post del dirigente

Seed de las 20 reglas nuevas en ``backend/scripts/seed_matrix_v2.py`` (idempotente).
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "ds04_matrix_context"
down_revision: str | None = "ds03_sc_data_source"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "framework_matrix_defaults",
        sa.Column(
            "contexto",
            sa.String(20),
            nullable=False,
            server_default="post_dirigente",
        ),
    )
    # Replace unique constraint to include contexto
    op.drop_constraint(
        "uq_framework_defaults", "framework_matrix_defaults", type_="unique"
    )
    op.create_unique_constraint(
        "uq_framework_defaults_v2",
        "framework_matrix_defaults",
        ["version", "rol", "tono", "target", "contexto"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_framework_defaults_v2", "framework_matrix_defaults", type_="unique"
    )
    op.create_unique_constraint(
        "uq_framework_defaults",
        "framework_matrix_defaults",
        ["version", "rol", "tono", "target"],
    )
    op.drop_column("framework_matrix_defaults", "contexto")
