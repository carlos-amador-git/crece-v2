"""social_comments — Índice de Aceptación (IA) por publicación.

Revision ID: h9c0d1e2f3g4
Revises: g8b9c0d1e2f3
Create Date: 2026-04-14 04:50:00.000000

Tabla para comments/replies scrapeados de posts. LFPDPPP compliant:
- author_hash SHA256(platform_user_id + salt) — nunca PII crudos
- content text (comentario público)
- nlp_tono/target aplicados con framework político existente
- is_follower booleano (si el hash aparece también en profile_snapshot de followers)
- es_externo derivado por defecto hasta tener followers list
"""
from alembic import op
import sqlalchemy as sa


revision = 'h9c0d1e2f3g4'
down_revision = 'g8b9c0d1e2f3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'social_comments',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('parent_post_id', sa.Integer,
                  sa.ForeignKey('social_posts.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('platform_comment_id', sa.String(255), nullable=False, unique=True),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('author_hash', sa.String(64), nullable=False, index=True),
        sa.Column('likes', sa.Integer, nullable=False, server_default='0'),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('nlp_tono', sa.String(30), nullable=True),
        sa.Column('nlp_target', sa.String(30), nullable=True),
        sa.Column('nlp_polaridad', sa.SmallInteger, nullable=True),
        sa.Column('nlp_model_version', sa.String(50), nullable=True),
        sa.Column('is_reply_to_comment', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('parent_comment_id', sa.Integer,
                  sa.ForeignKey('social_comments.id', ondelete='SET NULL'),
                  nullable=True),
        sa.Column('es_follower', sa.Boolean, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_social_comments_author_hash_post',
                    'social_comments', ['author_hash', 'parent_post_id'])
    op.create_index('ix_social_comments_published_at',
                    'social_comments', ['published_at'])


def downgrade() -> None:
    op.drop_index('ix_social_comments_published_at', table_name='social_comments')
    op.drop_index('ix_social_comments_author_hash_post', table_name='social_comments')
    op.drop_table('social_comments')
