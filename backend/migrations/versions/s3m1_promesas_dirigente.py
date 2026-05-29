"""promesas_dirigente — Sprint S3 B16 Rastreador Promesas de Campaña.

Revision ID: s3m1_promesas_dirigente
Revises: s1m1_sprint_s1_schema
Create Date: 2026-04-19 22:00:00.000000

Crea tabla ``promesas_dirigente`` para tracking de promesas de campaña.
MASTER §3.2 #16.

Columnas:
    - id
    - dirigente_id (FK → dirigentes.id, CASCADE)
    - texto_promesa (TEXT)
    - fecha_compromiso (DATE, cuándo se prometió realizar)
    - fecha_realizada (DATE, cuándo efectivamente se cumplió)
    - estado (ENUM: pendiente/cumplida/contradicha)
    - evidencia_url (VARCHAR 500, link a fuente de verdad)
    - created_at / updated_at
"""
import sqlalchemy as sa
from alembic import op

revision = "s3m1_promesas_dirigente"
down_revision = "s1m1_sprint_s1_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "promesas_dirigente",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "dirigente_id", sa.Integer,
            sa.ForeignKey("dirigentes.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column("texto_promesa", sa.Text, nullable=False),
        sa.Column("fecha_compromiso", sa.Date, nullable=True),
        sa.Column("fecha_realizada", sa.Date, nullable=True),
        sa.Column(
            "estado",
            sa.Enum(
                "pendiente", "cumplida", "contradicha",
                name="promesa_estado",
                create_type=True,
            ),
            nullable=False,
            server_default="pendiente",
        ),
        sa.Column("evidencia_url", sa.String(500), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
    )
    op.create_index(
        "ix_promesas_dirigente_estado",
        "promesas_dirigente",
        ["dirigente_id", "estado"],
    )


def downgrade() -> None:
    op.drop_index("ix_promesas_dirigente_estado", table_name="promesas_dirigente")
    op.drop_table("promesas_dirigente")
    op.execute("DROP TYPE IF EXISTS promesa_estado")
