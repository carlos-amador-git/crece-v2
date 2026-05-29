"""Add plataformas_destino jsonb to recomendaciones_plan_ia

Elimina dependencia de regex frágil sobre accion_texto. La detección de
plataformas (IG, FB, X, TT, YT) se persiste explícitamente.

Revision ID: rec_platdest1
Revises: efm1_efemerides
Create Date: 2026-05-12

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "rec_platdest1"
down_revision = "efm1_efemerides"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "recomendaciones_plan_ia",
        sa.Column(
            "plataformas_destino",
            JSONB,
            nullable=True,
            comment="Array de plataformas target del post: INSTAGRAM, FACEBOOK, TIKTOK, YOUTUBE, TWITTER",
        ),
    )
    # Backfill mediante regex Postgres simple. Casos ambiguos quedan NULL para
    # que el script _backfill_plataformas_destino.py los limpie con lógica fina.
    op.execute(
        """
        UPDATE recomendaciones_plan_ia
        SET plataformas_destino = ARRAY_TO_JSON(
          ARRAY_REMOVE(
            ARRAY[
              CASE WHEN accion_texto ~* '\\m(Instagram|\\mIG\\M)' THEN 'INSTAGRAM' END,
              CASE WHEN accion_texto ~* '\\m(Facebook|\\mFB\\M)'  THEN 'FACEBOOK'  END,
              CASE WHEN accion_texto ~* '\\m(TikTok|\\mTT\\M)'    THEN 'TIKTOK'    END,
              CASE WHEN accion_texto ~* '\\m(YouTube|\\mYT\\M)'   THEN 'YOUTUBE'   END,
              CASE WHEN accion_texto ~* '\\m(Twitter|\\mX\\M)'    THEN 'TWITTER'   END
            ],
            NULL
          )
        )::jsonb
        WHERE plataformas_destino IS NULL;
        """
    )


def downgrade() -> None:
    op.drop_column("recomendaciones_plan_ia", "plataformas_destino")
