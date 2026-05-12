"""Sprint C hardening: platform_enum += NEWS.

Revision ID: a1a2a3a4a5a6
Revises: f6a7b8c9d0e1
Create Date: 2026-04-12 01:30:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers
revision: str = "a1a2a3a4a5a6"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE cannot run inside a transaction block (Gemini G4).
    # Use autocommit_block to execute outside the Alembic transaction.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE platform_enum ADD VALUE IF NOT EXISTS 'NEWS'")


def downgrade() -> None:
    # PostgreSQL does not support removing values from enums.
    # To fully downgrade, the enum would need to be recreated.
    pass
