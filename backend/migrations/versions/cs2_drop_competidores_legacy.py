"""cs2: drop tablas competidores + competidor_social_profiles legacy

Plan war-room-personal · W7. La tabla `competidores` queda deprecada en favor
de `competitor_profiles` (D-MODEL-WAR-ROOM-1). Migración de datos hecha
manualmente con /tmp/migrate_competidores.sql el 2026-05-14 antes de aplicar
esta migración:
- 2 duplicados (Ivette+Susana TBD) borrados (ya estaban en competitor_profiles)
- 5 originales (Batres/Taboada×2/Harfuch/Brugada) movidos a competitor_profiles
  con dirigente_objetivo_id=8 (Ballesteros)
- Tabla competidores quedó vacía antes de esta migración.

Callers refactorizados al usar `competitor_profiles`:
- backend/app/services/plan_generator.py
- backend/app/services/onboarding/competidores_service.py
- backend/scripts/seed.py
- backend/app/api/v1/endpoints/benchmark.py → ELIMINADO (cero callers)

Revision ID: cs2
Revises: cp3
Create Date: 2026-05-14
"""
from __future__ import annotations

from alembic import op


revision = "cs2"
down_revision = "cp3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # competidor_social_profiles tiene FK a competidores (ON DELETE CASCADE),
    # pero hay que dropearla primero por orden de tablas.
    op.drop_table("competidor_social_profiles")
    op.drop_table("competidores")


def downgrade() -> None:
    # Downgrade no recupera datos (ya migrados a competitor_profiles).
    # Recrea esquema vacío para alembic happy path.
    import sqlalchemy as sa

    op.create_table(
        "competidores",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("nombre", sa.String(length=255), nullable=False, index=True),
        sa.Column("partido", sa.String(length=50), nullable=False),
        sa.Column("cargo", sa.String(length=255), nullable=False),
        sa.Column("es_rival", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.create_index("ix_competidores_nombre", "competidores", ["nombre"])
    op.create_table(
        "competidor_social_profiles",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column(
            "competidor_id",
            sa.Integer(),
            sa.ForeignKey("competidores.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("platform", sa.String(length=20), nullable=False),
        sa.Column("handle", sa.String(length=255), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=True),
        sa.Column("followers_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("following_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("posts_count", sa.Integer(), nullable=False, server_default="0"),
    )
