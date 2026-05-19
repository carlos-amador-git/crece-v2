"""add dirigente_id to users

Revision ID: d4e7a2c1b8f3
Revises: c3f1a2b4e5d6
Create Date: 2026-04-11 10:00:00.000000

Motivo: el modelo `User` declara `dirigente_id` (FK -> dirigentes.id) desde el
inicio de Fase 2 para auto-scope de dirigentes, pero esa columna nunca fue
creada en una migración. El dev DB la tenía por ALTER TABLE manual y el test DB
se levantaba con `Base.metadata.create_all`, por lo que el desfase pasó
desapercibido. Esta migración lo cierra antes de cualquier reset en producción.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d4e7a2c1b8f3"
down_revision: str | None = "c3f1a2b4e5d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_cols = {col["name"] for col in inspector.get_columns("users")}

    if "dirigente_id" not in existing_cols:
        op.add_column(
            "users",
            sa.Column("dirigente_id", sa.Integer(), nullable=True),
        )

    existing_fks = inspector.get_foreign_keys("users")
    has_dirigente_fk = any(
        "dirigente_id" in (fk.get("constrained_columns") or [])
        and (fk.get("referred_table") == "dirigentes")
        for fk in existing_fks
    )
    if not has_dirigente_fk:
        op.create_foreign_key(
            "fk_users_dirigente_id_dirigentes",
            "users",
            "dirigentes",
            ["dirigente_id"],
            ["id"],
            ondelete="SET NULL",
        )

    existing_indexes = {idx["name"] for idx in inspector.get_indexes("users")}
    if "ix_users_dirigente_id" not in existing_indexes:
        op.create_index(
            "ix_users_dirigente_id",
            "users",
            ["dirigente_id"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing_indexes = {idx["name"] for idx in inspector.get_indexes("users")}
    if "ix_users_dirigente_id" in existing_indexes:
        op.drop_index("ix_users_dirigente_id", table_name="users")

    existing_fks = inspector.get_foreign_keys("users")
    for fk in existing_fks:
        if "dirigente_id" in (fk.get("constrained_columns") or []) and fk.get("referred_table") == "dirigentes":
            op.drop_constraint(fk["name"], "users", type_="foreignkey")
            break

    existing_cols = {col["name"] for col in inspector.get_columns("users")}
    if "dirigente_id" in existing_cols:
        op.drop_column("users", "dirigente_id")
