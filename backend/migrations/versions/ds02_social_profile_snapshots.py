"""Create social_profile_snapshots table.

Revision ID: ds02_social_profile_snapshots
Revises: ds01_data_source_enum
Create Date: 2026-04-13 22:56:00.000000

Sprint: cirugía módulo dirigente — paso (b) migration 2/2.

Tabla de snapshots diarios por perfil social. Denormaliza
``dirigente_id``, ``org_id`` y ``platform`` para:
- RLS performante sin JOIN a ``social_profiles`` y ``dirigentes``.
- Queries time-series filtradas por plataforma (WHERE platform='TWITTER').

El ``profile_id`` es FK con ``ON DELETE CASCADE``. Si un dirigente cambia
de handle, el profile_id persiste → histórico intacto.

RLS policy: un usuario solo ve snapshots de su ``org_id``. Idéntica a la
política aplicada ya sobre ``social_profiles`` en migration 77bbd5e5f495.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Reuse existing platform_enum from social_profiles migration — do NOT re-create.
platform_enum_ref = postgresql.ENUM(
    "TWITTER", "INSTAGRAM", "FACEBOOK", "TIKTOK", "YOUTUBE",
    "BLUESKY", "THREADS", "TELEGRAM", "NEWS",
    name="platform_enum",
    create_type=False,
)

# revision identifiers
revision: str = "ds02_social_profile_snapshots"
down_revision: str | None = "ds01_data_source_enum"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "social_profile_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "profile_id",
            sa.Integer(),
            sa.ForeignKey("social_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "dirigente_id",
            sa.Integer(),
            sa.ForeignKey("dirigentes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "org_id",
            sa.Integer(),
            sa.ForeignKey("organizaciones.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("platform", platform_enum_ref, nullable=False),
        sa.Column("followers_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("posts_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "taken_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_snapshots_profile_taken",
        "social_profile_snapshots",
        ["profile_id", "taken_at"],
    )
    op.create_index(
        "ix_snapshots_org_platform_taken",
        "social_profile_snapshots",
        ["org_id", "platform", "taken_at"],
    )
    op.create_index(
        "ix_snapshots_dirigente_taken",
        "social_profile_snapshots",
        ["dirigente_id", "taken_at"],
    )

    # RLS: isolate by org_id (same pattern as social_profiles).
    op.execute("ALTER TABLE social_profile_snapshots ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY social_profile_snapshots_tenant_isolation
        ON social_profile_snapshots
        USING (org_id = current_setting('app.current_org_id', true)::int)
        WITH CHECK (org_id = current_setting('app.current_org_id', true)::int)
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS social_profile_snapshots_tenant_isolation ON social_profile_snapshots")
    op.drop_index("ix_snapshots_dirigente_taken", table_name="social_profile_snapshots")
    op.drop_index("ix_snapshots_org_platform_taken", table_name="social_profile_snapshots")
    op.drop_index("ix_snapshots_profile_taken", table_name="social_profile_snapshots")
    op.drop_table("social_profile_snapshots")
