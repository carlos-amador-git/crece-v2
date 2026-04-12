"""add topic_trends + RLS + HNSW (S4.2)

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-11 12:35:00.000000

Sprint 4 — Motor de Trends MVP, tareas S4.2a/c/b.

Orden crítico (per cross-audit Gemini 2026-04-11):
    1. S4.2a: CREATE TABLE topic_trends (columnas base + FKs)
    2. S4.2c: ALTER TABLE ENABLE RLS + CREATE POLICY org_id
    3. S4.2b: ADD COLUMN topic_embedding vector(384) + CREATE INDEX HNSW

RLS antes del índice HNSW evita ventanas de fuga durante ingesta inicial.
`maintenance_work_mem` se eleva temporalmente para que el build del índice
HNSW no haga thrashing con el default (64MB).
"""
from __future__ import annotations

from typing import Sequence, Union

import pgvector.sqlalchemy
import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---- S4.2a: table -----------------------------------------------------
    op.create_table(
        "topic_trends",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("alcaldia_id", sa.Integer(), nullable=True),
        sa.Column("topic_label", sa.String(length=200), nullable=True),
        sa.Column("time_bucket", sa.DateTime(timezone=True), nullable=False),
        sa.Column("post_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sentiment_avg", sa.Float(), nullable=True),
        sa.Column("growth_rate_24h", sa.Float(), nullable=True),
        sa.Column("sample_posts", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["org_id"], ["organizaciones.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["alcaldia_id"], ["alcaldias_cdmx.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_topic_trends_org_id", "topic_trends", ["org_id"], unique=False
    )
    op.create_index(
        "ix_topic_trends_alcaldia_id",
        "topic_trends",
        ["alcaldia_id"],
        unique=False,
    )
    op.create_index(
        "ix_topic_trends_time_bucket",
        "topic_trends",
        ["time_bucket"],
        unique=False,
    )
    # Composite index for the most common query pattern:
    # WHERE org_id=X AND alcaldia_id=Y AND time_bucket BETWEEN ...
    op.create_index(
        "ix_topic_trends_org_alcaldia_bucket",
        "topic_trends",
        ["org_id", "alcaldia_id", "time_bucket"],
        unique=False,
    )

    # ---- S4.2c: RLS policies (BEFORE the HNSW index — Gemini G1) ---------
    op.execute("ALTER TABLE topic_trends ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE topic_trends FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY topic_trends_org_isolation ON topic_trends
        USING (
            org_id::text = current_setting('app.current_org_id', true)
        )
        """
    )
    op.execute(
        """
        CREATE POLICY topic_trends_org_insert ON topic_trends
        FOR INSERT
        WITH CHECK (
            org_id::text = current_setting('app.current_org_id', true)
        )
        """
    )

    # ---- S4.2b: vector column + HNSW index (RLS already enforced) --------
    op.add_column(
        "topic_trends",
        sa.Column("topic_embedding", pgvector.sqlalchemy.Vector(384), nullable=True),
    )
    # Elevate maintenance_work_mem for this session so HNSW build doesn't
    # thrash. Default 64MB is tight for 384-dim vectors at scale; 512MB is
    # the pgvector recommended minimum for moderate datasets.
    op.execute("SET maintenance_work_mem = '512MB'")
    # HNSW cosine distance — matches the embedding model convention (cos sim).
    # m=16 and ef_construction=64 are pgvector defaults, explicit for clarity.
    op.execute(
        """
        CREATE INDEX ix_topic_trends_embedding_hnsw
        ON topic_trends
        USING hnsw (topic_embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )
    op.execute("RESET maintenance_work_mem")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_topic_trends_embedding_hnsw")
    op.drop_column("topic_trends", "topic_embedding")
    op.execute("DROP POLICY IF EXISTS topic_trends_org_insert ON topic_trends")
    op.execute("DROP POLICY IF EXISTS topic_trends_org_isolation ON topic_trends")
    op.execute("ALTER TABLE topic_trends DISABLE ROW LEVEL SECURITY")
    op.drop_index(
        "ix_topic_trends_org_alcaldia_bucket", table_name="topic_trends"
    )
    op.drop_index("ix_topic_trends_time_bucket", table_name="topic_trends")
    op.drop_index("ix_topic_trends_alcaldia_id", table_name="topic_trends")
    op.drop_index("ix_topic_trends_org_id", table_name="topic_trends")
    op.drop_table("topic_trends")
