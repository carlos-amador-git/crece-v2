"""HITL audit log + review status columns (Sprint S1 editor HITL)

Revision ID: dse_hitl_audit
Revises: phb1_pesos_target_politico
Create Date: 2026-05-08 00:00:00.000000

Sprint S1 · Editor HITL `/dashboard/settings/evaluacion-nlp`

Plan de referencia:
  ``.context/PLAN-2026-05-09-editor-hitl.md`` · sección S1.

Cambios:

1. `social_comments` extendida con 3 columnas:
   - last_reviewed_by  INT  REFERENCES users(id)
   - last_reviewed_at  TIMESTAMP
   - review_status     VARCHAR(20) DEFAULT 'unreviewed'  (unreviewed|confirmed|edited)

2. `social_posts` extendida con las MISMAS 3 columnas.

3. Tabla nueva `hitl_edits_log` (audit log inmutable de ediciones HITL).

4. Indexes:
   - idx_hitl_edits_entity     (entity_type, entity_id)
   - idx_hitl_edits_dirigente  (dirigente_id, edited_at DESC)
   - idx_social_comments_review (review_status, parent_post_id)

NOTA: hand-written, NO autogenerate (mismo motivo que s1m1: drift intencional
en `social_comments` que no tiene modelo SQLAlchemy).
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "dse_hitl_audit"
down_revision = "phb1_pesos_target_politico"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =========================================================================
    # 1. social_comments — review tracking columns
    # =========================================================================
    op.add_column(
        "social_comments",
        sa.Column(
            "last_reviewed_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "social_comments",
        sa.Column("last_reviewed_at", sa.DateTime(timezone=False), nullable=True),
    )
    op.add_column(
        "social_comments",
        sa.Column(
            "review_status",
            sa.String(length=20),
            nullable=False,
            server_default="unreviewed",
        ),
    )

    # =========================================================================
    # 2. social_posts — review tracking columns
    # =========================================================================
    op.add_column(
        "social_posts",
        sa.Column(
            "last_reviewed_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "social_posts",
        sa.Column("last_reviewed_at", sa.DateTime(timezone=False), nullable=True),
    )
    op.add_column(
        "social_posts",
        sa.Column(
            "review_status",
            sa.String(length=20),
            nullable=False,
            server_default="unreviewed",
        ),
    )

    # =========================================================================
    # 3. hitl_edits_log — immutable audit log
    # =========================================================================
    op.create_table(
        "hitl_edits_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("entity_type", sa.String(length=20), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column(
            "dirigente_id",
            sa.Integer(),
            sa.ForeignKey("dirigentes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("from_tono", sa.String(length=20), nullable=True),
        sa.Column("to_tono", sa.String(length=20), nullable=True),
        sa.Column("from_target", sa.String(length=30), nullable=True),
        sa.Column("to_target", sa.String(length=30), nullable=True),
        sa.Column(
            "off_topic",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "actor_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "source",
            sa.String(length=30),
            nullable=False,
            server_default="hitl_settings_evaluacion_nlp",
        ),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "edited_at",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "entity_type IN ('post','comment')",
            name="hitl_edits_log_entity_type_check",
        ),
    )

    # =========================================================================
    # 4. Indexes
    # =========================================================================
    op.create_index(
        "idx_hitl_edits_entity",
        "hitl_edits_log",
        ["entity_type", "entity_id"],
    )
    op.create_index(
        "idx_hitl_edits_dirigente",
        "hitl_edits_log",
        ["dirigente_id", sa.text("edited_at DESC")],
    )
    op.create_index(
        "idx_social_comments_review",
        "social_comments",
        ["review_status", "parent_post_id"],
    )


def downgrade() -> None:
    # 4. drop indexes
    op.drop_index("idx_social_comments_review", table_name="social_comments")
    op.drop_index("idx_hitl_edits_dirigente", table_name="hitl_edits_log")
    op.drop_index("idx_hitl_edits_entity", table_name="hitl_edits_log")

    # 3. drop hitl_edits_log
    op.drop_table("hitl_edits_log")

    # 2. social_posts revert
    op.drop_column("social_posts", "review_status")
    op.drop_column("social_posts", "last_reviewed_at")
    op.drop_column("social_posts", "last_reviewed_by")

    # 1. social_comments revert
    op.drop_column("social_comments", "review_status")
    op.drop_column("social_comments", "last_reviewed_at")
    op.drop_column("social_comments", "last_reviewed_by")
