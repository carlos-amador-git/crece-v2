"""ingest_jobs radar handoff

Revision ID: d46ed59d5aa0
Revises: oc1
Create Date: 2026-06-11 23:07:40.476179

NOTA: el autogenerate detectó drift ajeno (tablas/columnas creadas por SQL crudo
sin modelo ORM: social_comments, framework_*, encuestas_publicas, columnas NLP de
social_posts, etc.) e intentaba DROPEARLAS. Esta migración fue recortada a mano a
SOLO la tabla ingest_jobs (PLAN-2026-06-11-auto-radar-crece). NO aplicar drift
de autogenerate sin revisión en este repo.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd46ed59d5aa0'
down_revision: Union[str, None] = 'oc1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ingest_jobs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('task_uuid', sa.String(length=64), nullable=False),
        sa.Column('schema_version', sa.String(length=32), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('dirigente_id', sa.Integer(), nullable=False),
        sa.Column(
            'status',
            sa.Enum('RECEIVED', 'RUNNING', 'COMPLETED', 'PARTIAL', 'TAINTED', 'FAILED',
                    name='ingest_job_status'),
            nullable=False,
        ),
        sa.Column('manifest', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('counts', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['dirigente_id'], ['dirigentes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_ingest_jobs_dirigente_id'), 'ingest_jobs', ['dirigente_id'],
                    unique=False)
    op.create_index(op.f('ix_ingest_jobs_task_uuid'), 'ingest_jobs', ['task_uuid'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_ingest_jobs_task_uuid'), table_name='ingest_jobs')
    op.drop_index(op.f('ix_ingest_jobs_dirigente_id'), table_name='ingest_jobs')
    op.drop_table('ingest_jobs')
    sa.Enum(name='ingest_job_status').drop(op.get_bind(), checkfirst=True)
