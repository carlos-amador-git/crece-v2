"""social_comments.data_source — trazabilidad por stack de scraping.

Revision ID: ds03_sc_data_source
Revises: ds02_social_profile_snapshots
Create Date: 2026-04-14 13:10:00.000000

Añade columna ``data_source VARCHAR(40) NULLABLE`` a ``social_comments``.

Convención valores (acordada con Carlos en Sprint B):
    {stack}-{plataforma}-{version}
Ej: 'brightdata-tt-v1', 'scraperapi-tt-api-v1', 'crawlbase-ig-embed-v1'.

Motivación: LFPDPPP + auditoría externa requiere trazabilidad de origen del dato.
Permite además backfill/reprocesamiento selectivo por stack (ej. "re-correr solo
comments de scraperapi que fallaron NLP").

Backfill:
- Piña (dirigente_id=1) tiene 200 comments pre-existentes via Brightdata → 'brightdata-tt-v1'.
- dirigentes 2..6 TikTok ingestados via ScraperAPI → 'scraperapi-tt-api-v1'.
Separación sin overlap temporal ni de dirigente — safe.

Columna NULLABLE: inserts futuros deben poblarla; el índice parcial excluye NULLs
para no inflar cuando se queda vacía.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "ds03_sc_data_source"
down_revision: Union[str, None] = "ds02_social_profile_snapshots"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "social_comments",
        sa.Column("data_source", sa.String(40), nullable=True),
    )
    op.create_index(
        "ix_social_comments_data_source",
        "social_comments",
        ["data_source"],
        postgresql_where=sa.text("data_source IS NOT NULL"),
    )

    # Backfill: usar dirigente_id + platform como discriminador (no overlap temporal con run de Carlos).
    op.execute(
        """
        UPDATE social_comments sc
        SET data_source = 'brightdata-tt-v1'
        FROM social_posts sp
        JOIN social_profiles prof ON prof.id = sp.profile_id
        WHERE sc.parent_post_id = sp.id
          AND prof.platform = 'TIKTOK'
          AND prof.dirigente_id = 1
          AND sc.data_source IS NULL
        """
    )
    op.execute(
        """
        UPDATE social_comments sc
        SET data_source = 'scraperapi-tt-api-v1'
        FROM social_posts sp
        JOIN social_profiles prof ON prof.id = sp.profile_id
        WHERE sc.parent_post_id = sp.id
          AND prof.platform = 'TIKTOK'
          AND prof.dirigente_id IN (2, 3, 4, 5, 6)
          AND sc.data_source IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_social_comments_data_source", table_name="social_comments")
    op.drop_column("social_comments", "data_source")
