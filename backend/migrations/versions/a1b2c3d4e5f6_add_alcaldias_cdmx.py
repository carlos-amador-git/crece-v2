"""add alcaldias_cdmx catalog (S4.1)

Revision ID: a1b2c3d4e5f6
Revises: 402acb98d2d4
Create Date: 2026-04-11 12:05:00.000000

Sprint 4 — Motor de Trends MVP, tarea S4.1.
Catálogo oficial INEGI de las 16 alcaldías de CDMX (CVE_ENT=09).
"""
from __future__ import annotations

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "402acb98d2d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "alcaldias_cdmx",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("cvegeo", sa.String(length=5), nullable=False),
        sa.Column("cve_mun", sa.String(length=3), nullable=False),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column("area_km2", sa.Float(), nullable=True),
        sa.Column("perimetro_km", sa.Float(), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="MULTIPOLYGON",
                srid=4326,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cvegeo", name="uq_alcaldias_cdmx_cvegeo"),
        sa.UniqueConstraint("nombre", name="uq_alcaldias_cdmx_nombre"),
    )
    op.create_index(
        "ix_alcaldias_cdmx_cvegeo", "alcaldias_cdmx", ["cvegeo"], unique=False
    )
    op.create_index(
        "ix_alcaldias_cdmx_nombre", "alcaldias_cdmx", ["nombre"], unique=False
    )
    # spatial index — GeoAlchemy2 normally auto-creates it, but be explicit
    # so that the raw SQL query optimizer uses it without waiting for autogenerate.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_alcaldias_cdmx_geom "
        "ON alcaldias_cdmx USING GIST (geom)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_alcaldias_cdmx_geom")
    op.drop_index("ix_alcaldias_cdmx_nombre", table_name="alcaldias_cdmx")
    op.drop_index("ix_alcaldias_cdmx_cvegeo", table_name="alcaldias_cdmx")
    op.drop_table("alcaldias_cdmx")
