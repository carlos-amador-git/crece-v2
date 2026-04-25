"""D-23-G' · Schema Actividad Política Alineada (4 columnas)

Revision ID: d23g1_actividad_alineada
Revises: s5m1_onboarding_tables
Create Date: 2026-04-24 12:00:00.000000

# D-OPS-08 hand-written · NO autogenerate
# D-OPS-09 atómica · solo schema · no incluye seed/data ni cambios de código
# D-OPS-10 revisor §9.8 (code-reviewer subagent + CEO) firma diff antes de aplicar

Recupera el subset mínimo de schema NLP perdido en migración destructiva
``3d6fe3f1660d_add_resultados_electorales_seccion_2024.py`` (2026-04-18) con
la reformulación D-23-G' (Actividad Política Alineada) que disuelve la
propuesta 4-fases con disenso CEO 2026-04-23.

Plan de referencia:
  ``.context/PLAN-D-23-G-actividad-alineada-2026-04-24.md``

Columnas agregadas
------------------

``social_posts``:
  - ``target_politico VARCHAR(32) NULL`` · clasificación 4-cat
    (oficialismo | oposicion | propio | personal) + ``no_determinado``
    como fallback cuando el post no tiene texto suficiente para clasificar
  - ``nlp_model_version VARCHAR(64) NULL`` · versión del prompt usado en
    backfill (permite re-procesar idempotente cuando se cambia el prompt)
  - ``clasificacion_origen VARCHAR(32) NOT NULL DEFAULT 'ai_suggested'``
    · provenance · valores ``human_*`` reservados forward-compat para Phase B
    opcional posterior (humano clasifica). Phase A solo usa ``ai_suggested``
    y ``human_admin`` (los 95 posts ya clasificados por equipo MD en sprint
    NLP framework 2026-04-13 se preservan con este valor)

``dirigentes``:
  - ``rol_politico VARCHAR(32) NULL`` · base para fórmula del KPI
    (oficialismo | oposicion | independiente). Recreación de la columna
    perdida en 3d6fe3f. La derivación desde ``partido`` se hace por código
    en ``app/services/actividad_alineada.py`` (Day 3 del plan).

Index agregado
--------------

  - ``ix_social_posts_profile_target_politico`` · partial index sobre
    ``(profile_id, target_politico)`` con ``WHERE target_politico IS NOT NULL``
    · acelera queries del KPI agregado por dirigente (que une social_posts
    → social_profiles → dirigente_id)

Constraints
-----------

CHECK constraints incluidos para enforcement de valores válidos en cada
columna enum-like (varchar). Se usa varchar en lugar de PostgreSQL ENUM
para evitar el dolor de ``ALTER TYPE foo_enum ADD VALUE`` en transacciones
separadas (D-OPS-09 atomicidad).

NO incluye
----------

Forward-compat decision: las siguientes columnas/tablas NO se crean en
Phase A. Si Phase B humano-clasifica se activa eventualmente, requerirá
una migración separada que las agregue:

- ``tono_discurso`` (3-cat redundante con target_politico para Phase A)
- ``sentimiento_politico_ajustado`` (no flip · KPI no necesita score ajustado)
- ``sentimiento_humano`` (Phase B opcional posterior)
- ``clasificacion_history`` (tabla audit · Phase B)
- ``clasificacion_samples`` (tabla sampling · Phase B)

Reversibilidad
--------------

``downgrade()`` simétrico a ``upgrade()``: drop index → drop constraints →
drop columns. Sin pérdida de datos crudos en ``social_posts`` o ``dirigentes``
porque las columnas son aditivas (todas NULL o con default seguro).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d23g1_actividad_alineada"
down_revision: Union[str, None] = "s5m1_onboarding_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── social_posts ────────────────────────────────────────────────

    # 1. target_politico · clasificación 4-cat IA + 'no_determinado' fallback
    op.add_column(
        "social_posts",
        sa.Column("target_politico", sa.String(32), nullable=True),
    )
    op.create_check_constraint(
        "ck_social_posts_target_politico",
        "social_posts",
        "target_politico IS NULL OR target_politico IN "
        "('oficialismo', 'oposicion', 'propio', 'personal', 'no_determinado')",
    )

    # 2. nlp_model_version · idempotencia backfill al cambiar prompt
    op.add_column(
        "social_posts",
        sa.Column("nlp_model_version", sa.String(64), nullable=True),
    )

    # 3. clasificacion_origen · provenance · forward-compat Phase B
    op.add_column(
        "social_posts",
        sa.Column(
            "clasificacion_origen",
            sa.String(32),
            nullable=False,
            server_default="ai_suggested",
        ),
    )
    op.create_check_constraint(
        "ck_social_posts_clasificacion_origen",
        "social_posts",
        "clasificacion_origen IN "
        "('ai_suggested', 'human_dirigente', 'human_admin', 'human_consultor')",
    )

    # ─── dirigentes ──────────────────────────────────────────────────

    # 4. rol_politico · base para fórmula KPI (recreación post-3d6fe3f)
    op.add_column(
        "dirigentes",
        sa.Column("rol_politico", sa.String(32), nullable=True),
    )
    op.create_check_constraint(
        "ck_dirigentes_rol_politico",
        "dirigentes",
        "rol_politico IS NULL OR rol_politico IN "
        "('oficialismo', 'oposicion', 'independiente')",
    )

    # ─── index ───────────────────────────────────────────────────────

    # 5. partial index para queries de KPI agregado por dirigente
    op.create_index(
        "ix_social_posts_profile_target_politico",
        "social_posts",
        ["profile_id", "target_politico"],
        postgresql_where=sa.text("target_politico IS NOT NULL"),
    )


def downgrade() -> None:
    # Orden inverso a upgrade(). Sin pérdida de datos crudos del piloto
    # porque las columnas son todas aditivas (sin transformación destructiva).

    # 5. index
    op.drop_index(
        "ix_social_posts_profile_target_politico",
        table_name="social_posts",
    )

    # 4. dirigentes.rol_politico
    op.drop_constraint(
        "ck_dirigentes_rol_politico", "dirigentes", type_="check"
    )
    op.drop_column("dirigentes", "rol_politico")

    # 3. social_posts.clasificacion_origen
    op.drop_constraint(
        "ck_social_posts_clasificacion_origen",
        "social_posts",
        type_="check",
    )
    op.drop_column("social_posts", "clasificacion_origen")

    # 2. social_posts.nlp_model_version
    op.drop_column("social_posts", "nlp_model_version")

    # 1. social_posts.target_politico
    op.drop_constraint(
        "ck_social_posts_target_politico", "social_posts", type_="check"
    )
    op.drop_column("social_posts", "target_politico")
