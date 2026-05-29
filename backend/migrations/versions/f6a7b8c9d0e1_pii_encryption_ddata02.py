r"""D-DATA-02 LFPDPPP — pgcrypto encryption sobre ciudadanos_legacy + data_access_log

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-04-11 16:45:00.000000

Compliance LFPDPPP — encriptación at-rest de PII crítico + audit trail.

Campos encriptados (bytea, NULL when clear column is NULL):
- clave_electoral_enc  (clave INE — ALTA sensibilidad)
- email_enc
- phone_01_enc, phone_02_enc, whatsapp_enc
- fecha_nacimiento_enc

Se mantienen las columnas en claro temporalmente para permitir roll-forward
sin downtime. La intención es que futuras writes usen los métodos de la
service layer (`app.services.pii`) que encriptan al insertar y descifran
con role check al leer. Una vez migrado el código consumidor, las
columnas en claro se borran en un segundo sprint.

Tabla `data_access_log`:
- Registro INSERT-only de acceso a PII (no hay DELETE/UPDATE por diseño)
- `user_id` nullable porque el sistema también puede leer via workers
- `metadata JSONB` para campos adicionales (ej. qué campos se leyeron)
- Sin FK sobre `users.id` para preservar log histórico si el user se borra

NOTA: No se agregan funciones SQL wrapper (encrypt_pii / decrypt_pii)
porque los secretos de pgcrypto quedarían en los logs de `\df+` y
`pg_proc`. Se manejan desde la capa Python con `PII_ENCRYPTION_KEY` del
env.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f6a7b8c9d0e1"
down_revision: str | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ─── Encrypted columns on ciudadanos_legacy ──────────────
    for col in (
        "clave_electoral_enc",
        "email_enc",
        "phone_01_enc",
        "phone_02_enc",
        "whatsapp_enc",
        "fecha_nacimiento_enc",
    ):
        op.add_column(
            "ciudadanos_legacy",
            sa.Column(col, sa.LargeBinary(), nullable=True),
        )

    # ─── data_access_log ─────────────────────────────────────
    op.create_table(
        "data_access_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("org_id", sa.Integer(), nullable=True),
        sa.Column("table_name", sa.String(length=100), nullable=False),
        sa.Column("row_id", sa.String(length=50), nullable=True),
        sa.Column(
            "action",
            sa.String(length=20),
            nullable=False,
            comment="read_pii | decrypt | delete_gdpr | export",
        ),
        sa.Column("fields", postgresql.ARRAY(sa.String(length=50)), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        sa.Column("request_ip", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dal_user_id", "data_access_log", ["user_id"])
    op.create_index("ix_dal_org_id", "data_access_log", ["org_id"])
    op.create_index(
        "ix_dal_table_row",
        "data_access_log",
        ["table_name", "row_id"],
    )
    op.create_index("ix_dal_action", "data_access_log", ["action"])
    op.create_index("ix_dal_created_at", "data_access_log", ["created_at"])

    # data_access_log is INSERT-only by convention. We do NOT grant UPDATE
    # or DELETE to non-superuser roles. Since `crece` dev role is superuser
    # (D-S4-06), policy isn't strict here, but the app-level role in prod
    # must be restricted to INSERT + SELECT.
    op.execute("ALTER TABLE data_access_log ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY dal_org_read ON data_access_log
        FOR SELECT
        USING (org_id IS NULL OR org_id::text = current_setting('app.current_org_id', true))
        """
    )
    op.execute(
        """
        CREATE POLICY dal_org_insert ON data_access_log
        FOR INSERT
        WITH CHECK (org_id IS NULL OR org_id::text = current_setting('app.current_org_id', true))
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS dal_org_insert ON data_access_log")
    op.execute("DROP POLICY IF EXISTS dal_org_read ON data_access_log")
    op.execute("ALTER TABLE data_access_log DISABLE ROW LEVEL SECURITY")
    for idx in (
        "ix_dal_created_at",
        "ix_dal_action",
        "ix_dal_table_row",
        "ix_dal_org_id",
        "ix_dal_user_id",
    ):
        op.drop_index(idx, table_name="data_access_log")
    op.drop_table("data_access_log")
    for col in (
        "fecha_nacimiento_enc",
        "whatsapp_enc",
        "phone_02_enc",
        "phone_01_enc",
        "email_enc",
        "clave_electoral_enc",
    ):
        op.drop_column("ciudadanos_legacy", col)
