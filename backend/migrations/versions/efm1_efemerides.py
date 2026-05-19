"""efemerides — Sprint 2026-05-12 calendario fechas conmemorativas.

Revision ID: efm1_efemerides
Revises: encmun1_municipio
Create Date: 2026-05-12 19:00:00.000000

Crea tabla ``efemerides`` para catálogo de fechas conmemorativas y estratégicas
(México 2026). D-CALENDARIO-1.

Decisión: mes y día como Integer (no Date) para recurrencia anual sin obsolescencia.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "efm1_efemerides"
down_revision = "encmun1_municipio"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "efemerides",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("mes", sa.Integer, nullable=False, index=True),
        sa.Column("dia", sa.Integer, nullable=False, index=True),
        sa.Column("titulo", sa.String(255), nullable=False),
        sa.Column(
            "tipo",
            sa.Enum(
                "civica", "internacional", "social",
                "emocional", "familiar", "comunidad",
                name="efemeride_tipo",
                create_type=True,
            ),
            nullable=False,
            index=True,
        ),
        sa.Column("descripcion", sa.Text, nullable=True),
        sa.Column("ideas_politicas", JSONB, nullable=False, server_default="[]"),
        sa.Column(
            "viralidad",
            sa.Enum(
                "alta", "media", "baja",
                name="efemeride_viralidad",
                create_type=True,
            ),
            nullable=False,
            server_default="media",
        ),
        sa.Column(
            "ambito",
            sa.Enum(
                "nacional", "internacional", "regional",
                name="efemeride_ambito",
                create_type=True,
            ),
            nullable=False,
            server_default="nacional",
        ),
        sa.Column(
            "is_active", sa.Boolean,
            nullable=False, server_default="true",
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
    )
    op.create_index(
        "idx_efemerides_mes_dia",
        "efemerides",
        ["mes", "dia"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_efemerides_mes_dia", table_name="efemerides")
    op.drop_table("efemerides")
    op.execute("DROP TYPE IF EXISTS efemeride_tipo")
    op.execute("DROP TYPE IF EXISTS efemeride_viralidad")
    op.execute("DROP TYPE IF EXISTS efemeride_ambito")
