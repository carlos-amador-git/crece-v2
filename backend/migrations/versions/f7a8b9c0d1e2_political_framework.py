"""Political framework (contexto + matriz configurable por tenant)

Revision ID: f7a8b9c0d1e2
Revises: f6a7b8c9d0e1
Create Date: 2026-04-13 18:10:00.000000

D-NLP-01: 3-layer architecture for political sentiment.
- contexto_politico: who governs what scope
- framework_matrix_defaults: published defaults for (rol, tono, target) → score
- framework_overrides_org: per-tenant overrides with audit trail
- dirigentes.rol_politico: derived (oficialismo|oposicion|independiente)
- social_posts: add tono_discurso, target_politico, sentimiento_politico_ajustado
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = 'f7a8b9c0d1e2'
down_revision = 'd5d6d7d8d9e0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Context: who governs what ───────────────────────────────────────
    op.create_table(
        'contexto_politico',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('ambito', sa.String(20), nullable=False),
        sa.Column('entidad', sa.String(80), nullable=True),
        sa.Column('partido_gobernante', sa.String(20), nullable=False),
        sa.Column('vigente_desde', sa.Date, nullable=False),
        sa.Column('vigente_hasta', sa.Date, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_contexto_ambito_entidad', 'contexto_politico', ['ambito', 'entidad'])

    # ── Rol político on dirigentes ──────────────────────────────────────
    op.add_column('dirigentes', sa.Column('rol_politico', sa.String(20), nullable=True))

    # ── Default matrix (published, immutable per version) ───────────────
    op.create_table(
        'framework_matrix_defaults',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('version', sa.String(20), nullable=False),
        sa.Column('rol', sa.String(20), nullable=False),
        sa.Column('tono', sa.String(30), nullable=False),
        sa.Column('target', sa.String(30), nullable=False),
        sa.Column('score_politico', sa.SmallInteger, nullable=False),
        sa.Column('descripcion', sa.String(200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_unique_constraint(
        'uq_framework_defaults',
        'framework_matrix_defaults',
        ['version', 'rol', 'tono', 'target']
    )

    # ── Tenant overrides ─────────────────────────────────────────────────
    op.create_table(
        'framework_overrides_org',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('org_id', sa.Integer, sa.ForeignKey('organizaciones.id', ondelete='CASCADE'), nullable=False),
        sa.Column('rol', sa.String(20), nullable=False),
        sa.Column('tono', sa.String(30), nullable=False),
        sa.Column('target', sa.String(30), nullable=False),
        sa.Column('score_politico', sa.SmallInteger, nullable=False),
        sa.Column('modified_by_user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False),
        sa.Column('modified_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_unique_constraint(
        'uq_framework_overrides',
        'framework_overrides_org',
        ['org_id', 'rol', 'tono', 'target']
    )
    op.create_index('ix_framework_overrides_org', 'framework_overrides_org', ['org_id'])

    # ── Audit trail for framework edits ──────────────────────────────────
    op.create_table(
        'framework_audit_log',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('org_id', sa.Integer, sa.ForeignKey('organizaciones.id', ondelete='CASCADE'), nullable=False),
        sa.Column('rol', sa.String(20), nullable=False),
        sa.Column('tono', sa.String(30), nullable=False),
        sa.Column('target', sa.String(30), nullable=False),
        sa.Column('score_before', sa.SmallInteger, nullable=True),
        sa.Column('score_after', sa.SmallInteger, nullable=False),
        sa.Column('score_default', sa.SmallInteger, nullable=False),
        sa.Column('changed_by_user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False),
        sa.Column('changed_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('razon', sa.Text, nullable=True),
    )
    op.create_index('ix_framework_audit_org', 'framework_audit_log', ['org_id'])

    # ── Post-level political classification ──────────────────────────────
    op.add_column('social_posts', sa.Column('tono_discurso', sa.String(30), nullable=True))
    op.add_column('social_posts', sa.Column('target_politico', sa.String(30), nullable=True))
    op.add_column('social_posts', sa.Column('sentimiento_politico_ajustado', sa.SmallInteger, nullable=True))
    op.add_column('social_posts', sa.Column('controversy_score', sa.Float, nullable=True))
    op.add_column('social_posts', sa.Column('toxicity_score', sa.Float, nullable=True))
    op.add_column('social_posts', sa.Column('topics_jsonb', postgresql.JSONB, nullable=True))
    op.add_column('social_posts', sa.Column('platform_adjusted_sentiment', sa.Float, nullable=True))
    op.add_column('social_posts', sa.Column('nlp_model_version', sa.String(50), nullable=True))
    op.add_column('social_posts', sa.Column('llm_razon', sa.Text, nullable=True))
    op.add_column('social_posts', sa.Column('llm_modelo', sa.String(50), nullable=True))
    op.add_column('social_posts', sa.Column('llm_processed_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('social_posts', 'llm_processed_at')
    op.drop_column('social_posts', 'llm_modelo')
    op.drop_column('social_posts', 'llm_razon')
    op.drop_column('social_posts', 'nlp_model_version')
    op.drop_column('social_posts', 'platform_adjusted_sentiment')
    op.drop_column('social_posts', 'topics_jsonb')
    op.drop_column('social_posts', 'toxicity_score')
    op.drop_column('social_posts', 'controversy_score')
    op.drop_column('social_posts', 'sentimiento_politico_ajustado')
    op.drop_column('social_posts', 'target_politico')
    op.drop_column('social_posts', 'tono_discurso')
    op.drop_index('ix_framework_audit_org', table_name='framework_audit_log')
    op.drop_table('framework_audit_log')
    op.drop_index('ix_framework_overrides_org', table_name='framework_overrides_org')
    op.drop_constraint('uq_framework_overrides', 'framework_overrides_org', type_='unique')
    op.drop_table('framework_overrides_org')
    op.drop_constraint('uq_framework_defaults', 'framework_matrix_defaults', type_='unique')
    op.drop_table('framework_matrix_defaults')
    op.drop_column('dirigentes', 'rol_politico')
    op.drop_index('ix_contexto_ambito_entidad', table_name='contexto_politico')
    op.drop_table('contexto_politico')
