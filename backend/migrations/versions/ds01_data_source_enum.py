"""Add data_source enum + last_manual_update to social_profiles.

Revision ID: ds01_data_source_enum
Revises: g8b9c0d1e2f3
Create Date: 2026-04-13 22:55:00.000000

Sprint: cirugía módulo dirigente — paso (b) migration 1/2.

Añade:
- ENUM ``data_source_enum`` con valores ``automated_scraper``, ``manual_host_ingest``,
  ``official_api``. Permite al worker saltar perfiles marcados ``manual_host_ingest``
  (YouTube + TikTok bloquean IP del container Docker).
- Columna ``social_profiles.data_source`` con default ``automated_scraper``.
- Columna ``social_profiles.last_manual_update DATETIME`` para detectar deuda de
  frescura en perfiles ingestados a mano (alerta 48h).

Aditiva no-breaking. Puede desplegarse independientemente de la migration ds02.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "ds01_data_source_enum"
down_revision: str | None = "h9c0d1e2f3g4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


data_source_enum = postgresql.ENUM(
    "automated_scraper",
    "manual_host_ingest",
    "official_api",
    name="data_source_enum",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    data_source_enum.create(bind, checkfirst=True)

    op.add_column(
        "social_profiles",
        sa.Column(
            "data_source",
            sa.Enum(
                "automated_scraper",
                "manual_host_ingest",
                "official_api",
                name="data_source_enum",
                create_type=False,
            ),
            nullable=False,
            server_default="automated_scraper",
        ),
    )
    op.add_column(
        "social_profiles",
        sa.Column("last_manual_update", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("social_profiles", "last_manual_update")
    op.drop_column("social_profiles", "data_source")
    bind = op.get_bind()
    data_source_enum.drop(bind, checkfirst=True)
