"""Encuestas públicas — validación externa del sentiment (D-NLP-05)

Revision ID: g8b9c0d1e2f3
Revises: f7a8b9c0d1e2
Create Date: 2026-04-13 19:25:00.000000

Tabla para almacenar encuestas de aprobación scrapeadas de Oraculus,
Parametría, Enkoll, Mitofsky, Reforma, El Financiero. Se usan como
ancla para detectar divergencia del sentiment CRECE vs realidad externa.
"""
from alembic import op
import sqlalchemy as sa


revision = 'g8b9c0d1e2f3'
down_revision = 'f7a8b9c0d1e2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'encuestas_publicas',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('fuente', sa.String(50), nullable=False),
        sa.Column('fecha_publicacion', sa.Date, nullable=False),
        sa.Column('ambito', sa.String(20), nullable=False),
        sa.Column('entidad', sa.String(80), nullable=True),
        sa.Column('actor_tipo', sa.String(30), nullable=False),
        sa.Column('actor_nombre', sa.String(150), nullable=False),
        sa.Column('actor_partido', sa.String(20), nullable=True),
        sa.Column('metrica', sa.String(30), nullable=False),
        sa.Column('valor_pct', sa.Float, nullable=False),
        sa.Column('valor_delta_vs_anterior', sa.Float, nullable=True),
        sa.Column('tamaño_muestra', sa.Integer, nullable=True),
        sa.Column('margen_error', sa.Float, nullable=True),
        sa.Column('url_fuente', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_encuestas_publicas_fecha', 'encuestas_publicas', ['fecha_publicacion'])
    op.create_index('ix_encuestas_publicas_ambito_entidad', 'encuestas_publicas', ['ambito', 'entidad'])
    op.create_index('ix_encuestas_publicas_actor', 'encuestas_publicas', ['actor_nombre'])


def downgrade() -> None:
    op.drop_index('ix_encuestas_publicas_actor', table_name='encuestas_publicas')
    op.drop_index('ix_encuestas_publicas_ambito_entidad', table_name='encuestas_publicas')
    op.drop_index('ix_encuestas_publicas_fecha', table_name='encuestas_publicas')
    op.drop_table('encuestas_publicas')
