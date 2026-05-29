"""D-DATA-02c: Drop PII clear columns from ciudadanos_legacy.

Data is already encrypted in _enc columns (backfill ran in D-DATA-02).
Clear columns are no longer read by any code path.

Revision ID: b2b3b4b5b6b7
Revises: a1a2a3a4a5a6
Create Date: 2026-04-12 02:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b2b3b4b5b6b7"
down_revision: str | None = "a1a2a3a4a5a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("ciudadanos_legacy", "email")
    op.drop_column("ciudadanos_legacy", "phone_01")
    op.drop_column("ciudadanos_legacy", "phone_02")
    op.drop_column("ciudadanos_legacy", "whatsapp")
    op.drop_column("ciudadanos_legacy", "fecha_nacimiento")
    op.drop_column("ciudadanos_legacy", "clave_electoral")


def downgrade() -> None:
    op.add_column(
        "ciudadanos_legacy",
        sa.Column("clave_electoral", sa.String(30), nullable=True),
    )
    op.add_column(
        "ciudadanos_legacy",
        sa.Column("fecha_nacimiento", sa.Date(), nullable=True),
    )
    op.add_column(
        "ciudadanos_legacy",
        sa.Column("whatsapp", sa.String(30), nullable=True),
    )
    op.add_column(
        "ciudadanos_legacy",
        sa.Column("phone_02", sa.String(30), nullable=True),
    )
    op.add_column(
        "ciudadanos_legacy",
        sa.Column("phone_01", sa.String(30), nullable=True),
    )
    op.add_column(
        "ciudadanos_legacy",
        sa.Column("email", sa.String(320), nullable=True),
    )
