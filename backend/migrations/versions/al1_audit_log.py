"""Audit log table for destructive ops (LFPDPPP art. 32)

S8 Sprint dedicado 2026-05-15. Cross-audit Gemini sugirió SQLAlchemy
Event Listeners en lugar de middleware FastAPI para capturar también
cascade deletes + bulk updates + ops desde Celery/scripts.

Revision ID: al1
Revises: sc2
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "al1"
down_revision = "sc2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=False),
        sa.Column("record_id", sa.Integer(), nullable=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("request_path", sa.String(length=255), nullable=True),
        sa.Column("changes_summary", JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("ix_audit_log_action", "audit_log", ["action"])
    op.create_index("ix_audit_log_model", "audit_log", ["model"])
    op.create_index("ix_audit_log_user_id", "audit_log", ["user_id"])
    op.create_index("ix_audit_log_created_at", "audit_log", ["created_at"])
    # Index compuesto para consultas tipo "qué borró user X en model Y"
    op.create_index(
        "ix_audit_log_user_model_action",
        "audit_log",
        ["user_id", "model", "action"],
    )


def downgrade() -> None:
    op.drop_index("ix_audit_log_user_model_action", table_name="audit_log")
    op.drop_index("ix_audit_log_created_at", table_name="audit_log")
    op.drop_index("ix_audit_log_user_id", table_name="audit_log")
    op.drop_index("ix_audit_log_model", table_name="audit_log")
    op.drop_index("ix_audit_log_action", table_name="audit_log")
    op.drop_table("audit_log")
