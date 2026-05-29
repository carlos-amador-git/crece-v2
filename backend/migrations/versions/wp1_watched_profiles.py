"""Add watched_profiles + watched_like_events.

Origen: PLAN-2026-05-14-watchlist-saymi.md · Fase 2.

Tablas:
- ``watched_profiles`` — perfiles bajo observación (lista nominada cliente).
- ``watched_like_events`` — likes/reactions detectados de los watched.

Revision ID: wp1
Revises: fol1_social_followers
Create Date: 2026-05-14
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "wp1"
down_revision = "fol1_social_followers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "watched_profiles",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "dirigente_observador_id",
            sa.Integer(),
            sa.ForeignKey("dirigentes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "org_id",
            sa.Integer(),
            sa.ForeignKey("organizaciones.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("platform", sa.String(20), nullable=False),
        sa.Column("profile_external_id", sa.String(100), nullable=False),
        sa.Column("profile_handle", sa.String(255), nullable=True),
        sa.Column("profile_url", sa.String(500), nullable=True),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("avatar_url", sa.Text, nullable=True),
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column("tags", JSONB, nullable=False, server_default="[]"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("author_hash", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "created_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.UniqueConstraint(
            "dirigente_observador_id",
            "platform",
            "profile_external_id",
            name="uq_watched_dirigente_platform_external",
        ),
        sa.CheckConstraint(
            "platform IN ('TWITTER','INSTAGRAM','FACEBOOK','TIKTOK','YOUTUBE','BLUESKY','THREADS','TELEGRAM')",
            name="ck_watched_platform",
        ),
        sa.CheckConstraint(
            "source IN ('cliente_seed','manual','auto_suggested','competidor')",
            name="ck_watched_source",
        ),
    )
    op.create_index(
        "ix_watched_obs", "watched_profiles", ["dirigente_observador_id"]
    )
    op.create_index("ix_watched_org_id", "watched_profiles", ["org_id"])
    op.create_index("ix_watched_author_hash", "watched_profiles", ["author_hash"])
    op.create_index(
        "ix_watched_obs_source",
        "watched_profiles",
        ["dirigente_observador_id", "source"],
    )

    # ── RLS por organización (sigue patrón social_followers/dirigentes) ──
    op.execute("ALTER TABLE watched_profiles ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE watched_profiles FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY watched_org_isolation ON watched_profiles
            USING (
                org_id IS NULL
                OR org_id::text = current_setting('app.current_org_id', true)
            );
        """
    )
    op.execute(
        """
        CREATE POLICY watched_org_insert ON watched_profiles
            FOR INSERT
            WITH CHECK (
                org_id IS NULL
                OR org_id::text = current_setting('app.current_org_id', true)
            );
        """
    )

    # ── Tabla watched_like_events ──
    op.create_table(
        "watched_like_events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "watched_profile_id",
            sa.BigInteger(),
            sa.ForeignKey("watched_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "post_id",
            sa.Integer(),
            sa.ForeignKey("social_posts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("reaction_type", sa.String(20), nullable=False, server_default="like"),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("source", sa.String(20), nullable=False),
        sa.UniqueConstraint(
            "watched_profile_id",
            "post_id",
            "reaction_type",
            name="uq_watched_like_post_type",
        ),
        sa.CheckConstraint(
            "source IN ('apify_reactions','visual_evidence','oauth_api','other_scraper')",
            name="ck_watched_like_source",
        ),
        sa.CheckConstraint(
            "reaction_type IN ('like','love','wow','haha','sad','angry','support','care')",
            name="ck_watched_reaction_type",
        ),
    )
    op.create_index("ix_watched_like_wp", "watched_like_events", ["watched_profile_id"])
    op.create_index("ix_watched_like_post", "watched_like_events", ["post_id"])


def downgrade() -> None:
    op.drop_table("watched_like_events")
    op.execute("DROP POLICY IF EXISTS watched_org_isolation ON watched_profiles")
    op.execute("DROP POLICY IF EXISTS watched_org_insert ON watched_profiles")
    op.drop_index("ix_watched_obs_source", table_name="watched_profiles")
    op.drop_index("ix_watched_author_hash", table_name="watched_profiles")
    op.drop_index("ix_watched_org_id", table_name="watched_profiles")
    op.drop_index("ix_watched_obs", table_name="watched_profiles")
    op.drop_table("watched_profiles")
