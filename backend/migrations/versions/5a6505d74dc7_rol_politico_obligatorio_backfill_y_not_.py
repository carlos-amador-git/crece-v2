"""rol_politico obligatorio backfill y not null

DISENO-actores-politicos-2026-07-16 (consenso tríada + GO CEO):
rol_politico es el parámetro del motor de scoring (KPI D-23-H + prompts NLP).
NULL producía scoring silenciosamente mal (fallback a 'independiente').

1. Backfill de NULLs existentes por partido (decisiones CEO 2026-07-16):
   MORENA → oficialismo · MC → oposicion · PAZ → independiente (partido nuevo,
   vinculado a Morena — decisión explícita CEO) · resto (SISTEMA/bots) → independiente.
2. NOT NULL constraint — ningún dirigente nuevo entra sin rol.

Revision ID: 5a6505d74dc7
Revises: d46ed59d5aa0
Create Date: 2026-07-16 23:50:52.085780
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import geoalchemy2  # noqa: F401


# revision identifiers, used by Alembic.
revision: str = '5a6505d74dc7'
down_revision: Union[str, None] = 'd46ed59d5aa0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1 · Backfill por partido — solo filas NULL (idempotente, no pisa overrides).
    op.execute(
        """
        UPDATE dirigentes SET rol_politico = CASE
            WHEN UPPER(partido) = 'MORENA' THEN 'oficialismo'
            WHEN UPPER(partido) = 'MC' THEN 'oposicion'
            ELSE 'independiente'
        END
        WHERE rol_politico IS NULL
        """
    )
    # 2 · Gate BD: NOT NULL (el CHECK de valores ya existe desde d23g1).
    op.alter_column(
        "dirigentes",
        "rol_politico",
        existing_type=sa.String(length=32),
        nullable=False,
    )


def downgrade() -> None:
    # Solo relaja el constraint — el backfill no se revierte (datos correctos).
    op.alter_column(
        "dirigentes",
        "rol_politico",
        existing_type=sa.String(length=32),
        nullable=True,
    )
