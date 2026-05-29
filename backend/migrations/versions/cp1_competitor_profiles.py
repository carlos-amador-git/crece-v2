"""Add competitor_profiles + competitor_posts + competitor_metrics_weekly.

Modelo ligero benchmark-oriented (Opción C de B-COMPETIDORES-MODELO-1).
Reemplaza WatchedProfile.source='competidor' (que era huérfano).

Revision ID: cp1
Revises: wp1
Create Date: 2026-05-14
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "cp1"
down_revision = "wp1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "competitor_profiles",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "org_id",
            sa.Integer(),
            sa.ForeignKey("organizaciones.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "dirigente_objetivo_id",
            sa.Integer(),
            sa.ForeignKey("dirigentes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("partido", sa.String(64), nullable=True),
        sa.Column("cargo", sa.String(255), nullable=True),
        sa.Column("platform", sa.String(20), nullable=False, server_default="FACEBOOK"),
        sa.Column("profile_external_id", sa.String(100), nullable=False),
        sa.Column("profile_handle", sa.String(255), nullable=True),
        sa.Column("profile_url", sa.String(500), nullable=True),
        sa.Column("avatar_url", sa.Text, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("tags", JSONB, nullable=False, server_default="[]"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("verified", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("last_scraped_at", sa.DateTime(timezone=True), nullable=True),
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
            "org_id",
            "platform",
            "profile_external_id",
            name="uq_competitor_org_platform_external",
        ),
        sa.CheckConstraint(
            "platform IN ('TWITTER','INSTAGRAM','FACEBOOK','TIKTOK','YOUTUBE')",
            name="ck_competitor_platform",
        ),
    )
    op.create_index("ix_competitor_org", "competitor_profiles", ["org_id"])
    op.create_index(
        "ix_competitor_objetivo", "competitor_profiles", ["dirigente_objetivo_id"]
    )

    op.execute("ALTER TABLE competitor_profiles ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE competitor_profiles FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY competitor_org_isolation ON competitor_profiles
            USING (org_id::text = current_setting('app.current_org_id', true));
        """
    )
    op.execute(
        """
        CREATE POLICY competitor_org_insert ON competitor_profiles
            FOR INSERT
            WITH CHECK (org_id::text = current_setting('app.current_org_id', true));
        """
    )

    op.create_table(
        "competitor_posts",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "competitor_id",
            sa.BigInteger(),
            sa.ForeignKey("competitor_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("platform_post_id", sa.String(255), nullable=False),
        sa.Column("post_url", sa.Text, nullable=True),
        sa.Column("content", sa.Text, nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reactions", sa.Integer, nullable=False, server_default="0"),
        sa.Column("comments_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("shares", sa.Integer, nullable=False, server_default="0"),
        sa.Column("views", sa.Integer, nullable=True),
        sa.Column("sentiment_score", sa.Float, nullable=True),
        sa.Column("sentiment_label", sa.String(20), nullable=True),
        sa.Column("nlp_model_version", sa.String(50), nullable=True),
        sa.Column(
            "scraped_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "competitor_id", "platform_post_id", name="uq_competitor_post_id"
        ),
    )
    op.create_index("ix_competitor_posts_comp", "competitor_posts", ["competitor_id"])
    op.create_index(
        "ix_competitor_posts_published",
        "competitor_posts",
        ["competitor_id", "published_at"],
    )

    op.create_table(
        "competitor_metrics_weekly",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "competitor_id",
            sa.BigInteger(),
            sa.ForeignKey("competitor_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("week_start", sa.Date, nullable=False),
        sa.Column("posts_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_reactions", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_comments", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_shares", sa.Integer, nullable=False, server_default="0"),
        sa.Column("engagement_rate", sa.Float, nullable=True),
        sa.Column("sentiment_avg", sa.Float, nullable=True),
        sa.Column("sentiment_label_modal", sa.String(20), nullable=True),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "competitor_id", "week_start", name="uq_competitor_week"
        ),
    )
    op.create_index(
        "ix_competitor_metrics_comp", "competitor_metrics_weekly", ["competitor_id"]
    )
    op.create_index(
        "ix_competitor_metrics_week", "competitor_metrics_weekly", ["week_start"]
    )


def downgrade() -> None:
    op.drop_index("ix_competitor_metrics_week", table_name="competitor_metrics_weekly")
    op.drop_index("ix_competitor_metrics_comp", table_name="competitor_metrics_weekly")
    op.drop_table("competitor_metrics_weekly")
    op.drop_index("ix_competitor_posts_published", table_name="competitor_posts")
    op.drop_index("ix_competitor_posts_comp", table_name="competitor_posts")
    op.drop_table("competitor_posts")
    op.execute("DROP POLICY IF EXISTS competitor_org_isolation ON competitor_profiles")
    op.execute("DROP POLICY IF EXISTS competitor_org_insert ON competitor_profiles")
    op.drop_index("ix_competitor_objetivo", table_name="competitor_profiles")
    op.drop_index("ix_competitor_org", table_name="competitor_profiles")
    op.drop_table("competitor_profiles")
