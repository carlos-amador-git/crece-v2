"""social_followers + follower_engagement — lista granular de seguidores.

Revision ID: fol1_social_followers
Revises: spm_media1
Create Date: 2026-05-13 09:00:00.000000

PLAN-2026-05-13-followers-oauth-pipeline.md S1. Tablas ADD-ONLY · sin ALTER
sobre tablas en producción · low-risk migration (B-23-01 doctrina).

- social_followers: lista individual de seguidores por dirigente × plataforma
- follower_engagement: cada interacción (comment/like/share/repost) entre un
  follower y un post del dirigente.

UPSERT idempotente por ``(dirigente_id, platform, follower_external_id)`` —
el scraper privilegiado (S3) puede re-correr sin duplicados.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "fol1_social_followers"
down_revision = "spm_media1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "social_followers",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "dirigente_id",
            sa.Integer,
            sa.ForeignKey("dirigentes.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "org_id",
            sa.Integer,
            sa.ForeignKey("organizaciones.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column("platform", sa.String(20), nullable=False),
        sa.Column("follower_external_id", sa.String(100), nullable=False),
        sa.Column("follower_handle", sa.String(100), nullable=True),
        sa.Column("follower_display_name", sa.String(200), nullable=True),
        sa.Column("follower_avatar_url", sa.Text, nullable=True),
        sa.Column(
            "follower_is_verified",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
        sa.Column(
            "is_real",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("TRUE"),
        ),
        sa.Column("bot_score", sa.Float, nullable=True),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column(
            "raw_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.CheckConstraint(
            "source IN ('oauth','scraper_auth','public_scraper')",
            name="ck_followers_source",
        ),
        sa.CheckConstraint(
            "platform IN ("
            "'twitter','instagram','facebook','tiktok','youtube',"
            "'bluesky','threads','telegram')",
            name="ck_followers_platform",
        ),
        sa.UniqueConstraint(
            "dirigente_id",
            "platform",
            "follower_external_id",
            name="uq_followers_dirigente_platform_external",
        ),
    )

    op.create_index(
        "idx_followers_dirigente_lastseen",
        "social_followers",
        ["dirigente_id", sa.text("last_seen_at DESC")],
    )
    op.create_index(
        "idx_followers_verified",
        "social_followers",
        ["dirigente_id", "follower_is_verified"],
    )

    op.create_table(
        "follower_engagement",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "follower_id",
            sa.BigInteger,
            sa.ForeignKey("social_followers.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "post_id",
            sa.Integer,
            sa.ForeignKey("social_posts.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("engagement_type", sa.String(20), nullable=False),
        sa.Column(
            "comment_id",
            sa.Integer,
            sa.ForeignKey("social_comments.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "engaged_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "raw_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.CheckConstraint(
            "engagement_type IN ('comment','like','share','repost','reaction')",
            name="ck_engagement_type",
        ),
        sa.UniqueConstraint(
            "follower_id",
            "post_id",
            "engagement_type",
            "comment_id",
            name="uq_engagement_follower_post_type_comment",
        ),
    )

    op.create_index(
        "idx_engagement_post_type",
        "follower_engagement",
        ["post_id", "engagement_type"],
    )


def downgrade() -> None:
    op.drop_index("idx_engagement_post_type", table_name="follower_engagement")
    op.drop_table("follower_engagement")

    op.drop_index("idx_followers_verified", table_name="social_followers")
    op.drop_index("idx_followers_dirigente_lastseen", table_name="social_followers")
    op.drop_table("social_followers")
