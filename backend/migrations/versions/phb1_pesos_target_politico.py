"""Phase B · Pesos editables target_politico (3 columnas en dirigentes)

Revision ID: phb1_pesos_target_politico
Revises: d23g1_actividad_alineada
Create Date: 2026-04-25 14:30:00.000000

# D-OPS-08 hand-written · NO autogenerate
# D-OPS-09 atómica · solo schema · sin seed/data ni cambios de código
# D-OPS-10 revisor §9.8 (code-reviewer subagent + CEO) firma diff antes de aplicar

Schema mínimo para Panel Editable de Evaluación (Palanca 1: pesos por
categoría target_politico). Forward-compat con Phase A sin tocar columnas
existentes.

Plan de referencia:
  ``.context/PLAN-D-23-H-panel-editable-2026-04-24.md``

Decisiones consolidadas (3 revisiones · Gemini → Claude IA → CEO 2026-04-25)
----------------------------------------------------------------------------
- Solo Palanca 1 (pesos por categoría). Palanca 2 (override per-post) → Phase C.
- Doble métrica: KPI default (pesos=1.0) y KPI ajustado (pesos del dirigente)
  ambos visibles. La transparencia es el audit, no el cap.
- Cap valores 0.5-1.5 enforced en CHECK + UI.
- last_modified stamp en columna · sin tabla history para MVP. Si se detecta
  manipulación grosera post-deploy, agregar tabla en Phase B.1.
- Comparativa entre dirigentes usa SIEMPRE default · vista personal usa ajustado.

Columnas agregadas
------------------

``dirigentes``:
  - ``pesos_target_politico JSONB DEFAULT {oficialismo:1, oposicion:1,
    propio:1, personal:1}`` · default neutro (sin manipulación). Cada dirigente
    ajusta sus pesos · NULL nunca (default-on-insert).
  - ``pesos_last_modified_by BIGINT NULL REFERENCES users(id)`` · audit de
    quién modificó por última vez (dirigente, admin MD, consultor).
  - ``pesos_last_modified_at TIMESTAMPTZ NULL`` · audit timestamp.

CHECK constraint
----------------

``ck_dirigentes_pesos_target_politico_shape`` valida:
  - JSONB tiene exactamente las 4 keys (oficialismo, oposicion, propio, personal)
  - Cada valor es numérico en rango ``[0.5, 1.5]``

Forward-compat preservado
-------------------------

NO se agregan en esta migración (diferido a Phase C si demanda):
- ``social_posts.target_politico_humano`` (override per-post · Palanca 2)
- ``pesos_history`` tabla (audit temporal · solo si vemos manipulación)
- Jerarquía multi-rol (admin MD propone, dirigente acepta) · MVP es last-write-wins

Reversibilidad
--------------

``downgrade()`` simétrico: drop check → drop FK constraint → drop columns.
Sin pérdida de datos porque las 3 columnas son aditivas.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "phb1_pesos_target_politico"
down_revision: str | None = "d23g1_actividad_alineada"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. pesos_target_politico · JSONB con default neutro.
    # server_default usa single-string + escape para evitar splicing de
    # triple-quotes (issue HIGH detectado por code-reviewer subagent).
    op.add_column(
        "dirigentes",
        sa.Column(
            "pesos_target_politico",
            sa.dialects.postgresql.JSONB(),
            nullable=False,
            # `\\:` escapa el colon ante SQLAlchemy text() (que interpreta `:nombre`
            # como bind param). Sin escape, `:1.0` se sustituye a `NULL.0`.
            server_default=sa.text(
                "'{\"oficialismo\"\\:1.0,\"oposicion\"\\:1.0,"
                "\"propio\"\\:1.0,\"personal\"\\:1.0}'\\:\\:jsonb"
            ),
        ),
    )

    # 2. CHECK constraint · shape + cap 0.5-1.5.
    # `jsonb_typeof(...)='number'` blinda contra null JSON en valor individual
    # (issue MEDIUM detectado por code-reviewer · CHECK con NULL implícito
    # se evalúa como satisfecho). Cada key debe existir y ser número en [0.5, 1.5].
    op.create_check_constraint(
        "ck_dirigentes_pesos_target_politico_shape",
        "dirigentes",
        """
        jsonb_typeof(pesos_target_politico) = 'object'
        AND pesos_target_politico ? 'oficialismo'
        AND pesos_target_politico ? 'oposicion'
        AND pesos_target_politico ? 'propio'
        AND pesos_target_politico ? 'personal'
        AND jsonb_typeof(pesos_target_politico->'oficialismo') = 'number'
        AND jsonb_typeof(pesos_target_politico->'oposicion') = 'number'
        AND jsonb_typeof(pesos_target_politico->'propio') = 'number'
        AND jsonb_typeof(pesos_target_politico->'personal') = 'number'
        AND (pesos_target_politico->>'oficialismo')::numeric BETWEEN 0.5 AND 1.5
        AND (pesos_target_politico->>'oposicion')::numeric BETWEEN 0.5 AND 1.5
        AND (pesos_target_politico->>'propio')::numeric BETWEEN 0.5 AND 1.5
        AND (pesos_target_politico->>'personal')::numeric BETWEEN 0.5 AND 1.5
        """,
    )

    # 3. pesos_last_modified_by · audit FK (nullable: nunca tocado = NULL)
    op.add_column(
        "dirigentes",
        sa.Column("pesos_last_modified_by", sa.BigInteger(), nullable=True),
    )
    op.create_foreign_key(
        "fk_dirigentes_pesos_last_modified_by_users",
        "dirigentes",
        "users",
        ["pesos_last_modified_by"],
        ["id"],
        ondelete="SET NULL",
    )

    # 4. pesos_last_modified_at · audit timestamp (nullable hasta primera edición)
    op.add_column(
        "dirigentes",
        sa.Column(
            "pesos_last_modified_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    # Orden inverso a upgrade(). Sin pérdida de datos · columnas aditivas.

    # 4. pesos_last_modified_at
    op.drop_column("dirigentes", "pesos_last_modified_at")

    # 3. pesos_last_modified_by + FK
    op.drop_constraint(
        "fk_dirigentes_pesos_last_modified_by_users",
        "dirigentes",
        type_="foreignkey",
    )
    op.drop_column("dirigentes", "pesos_last_modified_by")

    # 2. CHECK + 1. pesos_target_politico
    op.drop_constraint(
        "ck_dirigentes_pesos_target_politico_shape",
        "dirigentes",
        type_="check",
    )
    op.drop_column("dirigentes", "pesos_target_politico")
