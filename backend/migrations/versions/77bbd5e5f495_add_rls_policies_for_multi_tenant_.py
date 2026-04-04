"""add RLS policies for multi-tenant isolation

Revision ID: 77bbd5e5f495
Revises: ecb44c21a495
Create Date: 2026-04-03 19:42:15.254011

Multi-tenant Row Level Security (RLS) policies.

Strategy:
- Each request sets `app.current_org_id` via SET LOCAL at the start of a transaction
- RLS policies filter rows where org_id = current_setting('app.current_org_id')
- Superadmins (org_id IS NULL) bypass RLS via the BYPASSRLS attribute
- Tables without org_id (social_posts, sentiment_analyses, etc.) are not RLS-enabled
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import geoalchemy2


# revision identifiers, used by Alembic.
revision: str = '77bbd5e5f495'
down_revision: Union[str, None] = 'ecb44c21a495'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tables that have org_id and need RLS
_RLS_TABLES = [
    "ciudadanos",
    "dirigentes",
    "encuestas",
    "eventos",
    "users",
]


def upgrade() -> None:
    for table in _RLS_TABLES:
        # Enable RLS on the table
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

        # Force RLS even for table owners (important for testing)
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

        # Policy: users see rows matching their org_id, or rows with NULL org_id (shared)
        op.execute(f"""
            CREATE POLICY {table}_org_isolation ON {table}
            USING (
                org_id IS NULL
                OR org_id::text = current_setting('app.current_org_id', true)
            )
        """)

        # Policy: inserts must set org_id matching the current tenant
        op.execute(f"""
            CREATE POLICY {table}_org_insert ON {table}
            FOR INSERT
            WITH CHECK (
                org_id IS NULL
                OR org_id::text = current_setting('app.current_org_id', true)
            )
        """)


def downgrade() -> None:
    for table in reversed(_RLS_TABLES):
        op.execute(f"DROP POLICY IF EXISTS {table}_org_insert ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_org_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
