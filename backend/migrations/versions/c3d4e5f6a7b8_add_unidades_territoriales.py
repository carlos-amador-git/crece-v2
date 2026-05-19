"""add unidades_territoriales (master_catalogo legacy CRECE)

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-04-11 13:50:00.000000

D-DATA-01 Ruta C — importar master_catalogo del CRECE Oracle APEX legacy.
Grano: sección electoral × unidad territorial (colonia/pueblo).
5,548 filas esperadas cubriendo las 16 alcaldías de CDMX.

Sin PII. Datos agregados INE + INEGI + clasificación política del CRECE
original (categoria P1..P5, volatilidad 0-100, estrato socioeconómico).
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "unidades_territoriales",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("legacy_id", sa.String(length=50), nullable=False),
        sa.Column("alcaldia_id", sa.Integer(), nullable=True),
        sa.Column("alcaldia_nombre", sa.String(length=100), nullable=False),
        sa.Column("clave_unidad_territorial", sa.String(length=20), nullable=False),
        sa.Column("cabecera_nombre", sa.String(length=200), nullable=True),
        sa.Column("parcial_completa", sa.String(length=20), nullable=True),
        sa.Column("seccion_2024", sa.String(length=10), nullable=False),
        sa.Column("dtto_federal_2024", sa.String(length=10), nullable=True),
        sa.Column("dtto_local_2024", sa.String(length=10), nullable=True),
        sa.Column("circunscripcion_2024", sa.String(length=10), nullable=True),
        sa.Column("circunscripcion_2022", sa.String(length=10), nullable=True),
        sa.Column("estrato", sa.String(length=50), nullable=True),
        sa.Column("nivel_socioeconomico_resumen", sa.String(length=100), nullable=True),
        sa.Column("grado_promedio_estudios", sa.Float(), nullable=True),
        sa.Column("p_viv_inter", sa.Float(), nullable=True),
        sa.Column("lista_nominal_2023", sa.Integer(), nullable=True),
        sa.Column("volatilidad", sa.Float(), nullable=True),
        sa.Column("categoria", sa.String(length=10), nullable=True),
        sa.ForeignKeyConstraint(
            ["alcaldia_id"], ["alcaldias_cdmx.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("legacy_id", name="uq_ut_legacy_id"),
    )
    op.create_index("ix_ut_legacy_id", "unidades_territoriales", ["legacy_id"])
    op.create_index("ix_ut_alcaldia_id", "unidades_territoriales", ["alcaldia_id"])
    op.create_index("ix_ut_alcaldia_nombre", "unidades_territoriales", ["alcaldia_nombre"])
    op.create_index(
        "ix_ut_clave_unidad_territorial",
        "unidades_territoriales",
        ["clave_unidad_territorial"],
    )
    op.create_index("ix_ut_seccion_2024", "unidades_territoriales", ["seccion_2024"])
    op.create_index(
        "ix_ut_circunscripcion_2024",
        "unidades_territoriales",
        ["circunscripcion_2024"],
    )
    op.create_index("ix_ut_estrato", "unidades_territoriales", ["estrato"])
    op.create_index("ix_ut_volatilidad", "unidades_territoriales", ["volatilidad"])
    op.create_index("ix_ut_categoria", "unidades_territoriales", ["categoria"])


def downgrade() -> None:
    for idx in [
        "ix_ut_categoria",
        "ix_ut_volatilidad",
        "ix_ut_estrato",
        "ix_ut_circunscripcion_2024",
        "ix_ut_seccion_2024",
        "ix_ut_clave_unidad_territorial",
        "ix_ut_alcaldia_nombre",
        "ix_ut_alcaldia_id",
        "ix_ut_legacy_id",
    ]:
        op.drop_index(idx, table_name="unidades_territoriales")
    op.drop_table("unidades_territoriales")
