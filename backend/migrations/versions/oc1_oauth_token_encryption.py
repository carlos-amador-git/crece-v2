"""Add encrypted OAuth token columns + crypto_version (B-OAUTH-YT-CRYPTO-1).

Schema-only migration. La re-encriptación de filas existentes (id=2 dirigente_id=1
Benjamin) se hace vía script Python standalone que SÍ tiene acceso al servicio
``app.services.pii.encrypt_value`` (recomendación Gemini cross-audit 2026-05-16).

Columnas nuevas:
- ``token_enc BYTEA`` — access_token cifrado con pgcrypto pgp_sym_encrypt
- ``refresh_token_enc BYTEA`` — refresh_token cifrado
- ``crypto_version INT NOT NULL DEFAULT 0`` — 0=plain, 1=pgp_sym_encrypt
- ``encrypted_at TIMESTAMPTZ`` — momento de cifrado

Columnas viejas ``token_hash`` / ``refresh_token_hash`` (nombre histórico) quedan
como nullable durante la transición. Se hará NULL-out posterior una vez el
script de migración haya cifrado todas las filas existentes y se haya validado.

Revision ID: oc1
Revises: al1
Create Date: 2026-05-16
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "oc1"
down_revision = "al1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "oauth_tokens_by_platform",
        sa.Column("token_enc", sa.LargeBinary(), nullable=True),
    )
    op.add_column(
        "oauth_tokens_by_platform",
        sa.Column("refresh_token_enc", sa.LargeBinary(), nullable=True),
    )
    op.add_column(
        "oauth_tokens_by_platform",
        sa.Column(
            "crypto_version",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "oauth_tokens_by_platform",
        sa.Column("encrypted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("oauth_tokens_by_platform", "encrypted_at")
    op.drop_column("oauth_tokens_by_platform", "crypto_version")
    op.drop_column("oauth_tokens_by_platform", "refresh_token_enc")
    op.drop_column("oauth_tokens_by_platform", "token_enc")
