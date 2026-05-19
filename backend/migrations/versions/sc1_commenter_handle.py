"""sc1: cachear commenter_handle público en social_comments

Sprint C del PLAN-2026-05-14-fix-fantasmas-observados.md.

Razón: `author_hash` (SHA256 one-way) bloquea UX de sugerencias en
/dashboard/aceptacion/fantasmas tab "Perfiles Observados". El usuario solo
ve un hash truncado y no puede tomar acción de etiquetar.

Solución: cachear el **handle público** (`@username`) del commenter al
momento del scrape. Handle público no es PII directa bajo LFPDPPP
(es identificador elegido por el usuario al publicar en una red social).

Camino C de la decisión D del plan (vs A re-scrape on-demand · vs B lookup
table con TTL · vs C cachear handle público — el elegido por base legal +
costo cero marginal).

Histórico (3,161 comments existentes) queda con commenter_handle IS NULL.
Endpoint /suggestions devuelve handle si existe, fallback a hash. UI pinta
botón "Investigar" para hashes sin handle (flujo A on-demand · pendiente
saldo Apify post 2026-06-13).
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "sc1"
down_revision = "cp2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "social_comments",
        sa.Column("commenter_handle", sa.String(length=255), nullable=True),
    )
    # Índice para queries que filtran por handle en sugerencias agrupadas.
    op.create_index(
        "ix_social_comments_commenter_handle",
        "social_comments",
        ["commenter_handle"],
        postgresql_where=sa.text("commenter_handle IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_social_comments_commenter_handle", table_name="social_comments")
    op.drop_column("social_comments", "commenter_handle")
