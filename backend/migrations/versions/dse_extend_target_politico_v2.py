"""extend ck_social_posts_target_politico with vocab v2 (matriz política)

Revision ID: dse_extend_tp_v2
Revises: dse_hitl_audit
Create Date: 2026-05-09

CONTEXTO:
La columna social_posts.target_politico tenía CHECK con vocab antiguo:
  oficialismo | oposicion | propio | personal | no_determinado

Pero el frontend, endpoint HITL, mapper v3.0.1 y matriz política producen vocab v2:
  gobierno | oposicion | ciudadania | medios | autopromocion | tema_especifico | dirigente

Solución NO destructiva: extender el CHECK con UNION de ambos vocabs.
Datos antiguos siguen válidos. Datos nuevos (v2) ahora pasan.
Post-reunión 2026-05-10 podemos hacer migration limpia rebuild + datos antiguos
mapeados al vocab v2 (oficialismo→gobierno, propio→autopromocion, etc.).
"""
from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "dse_extend_tp_v2"
down_revision = "dse_hitl_audit"
branch_labels = None
depends_on = None


VOCAB_UNION = (
    # Vocab antiguo (compatibilidad)
    "'oficialismo', 'oposicion', 'propio', 'personal', 'no_determinado', "
    # Vocab v2 (matriz política)
    "'gobierno', 'ciudadania', 'medios', 'autopromocion', 'tema_especifico', 'dirigente'"
)


def upgrade() -> None:
    op.execute("ALTER TABLE social_posts DROP CONSTRAINT IF EXISTS ck_social_posts_target_politico")
    op.execute(
        f"""
        ALTER TABLE social_posts
        ADD CONSTRAINT ck_social_posts_target_politico
        CHECK (
            target_politico IS NULL OR
            target_politico::text IN ({VOCAB_UNION})
        )
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE social_posts DROP CONSTRAINT IF EXISTS ck_social_posts_target_politico")
    op.execute(
        """
        ALTER TABLE social_posts
        ADD CONSTRAINT ck_social_posts_target_politico
        CHECK (
            target_politico IS NULL OR
            target_politico::text IN ('oficialismo', 'oposicion', 'propio', 'personal', 'no_determinado')
        )
        """
    )
