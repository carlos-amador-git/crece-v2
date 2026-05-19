"""Sprint S5 — Onboarding Wizard schema.

Revision ID: s5m1_onboarding_tables
Revises: s3m1_promesas_dirigente
Create Date: 2026-04-20 00:00:00.000000

Crea el esquema de soporte para el Onboarding Wizard comercial (D-22 · D-23 · §4 tiers · §1.5 perfiles):

1. ``dirigentes.perfil_1_5`` — VARCHAR(30) con CHECK constraint sobre los 4 perfiles §1.5
   (politico_activo, funcionario_gobierno, figura_precampaña, empresario_transicion)
2. ``social_profiles.is_confirmed`` — BOOLEAN DEFAULT FALSE — regla dura D-23: scraping solo
   con confirmación humana explícita del cliente.
3. ``social_profiles.data_source`` ENUM extendido: acepta ``'manual_onboarding'`` como valor
   adicional (input directo de URLs en el wizard).
4. ``oauth_tokens_by_platform`` — NEW TABLE — tokens OAuth cifrados por dirigente × plataforma.
   Se crea con schema productivo completo pero los endpoints S5 escriben stubs (``is_stub=true``)
   hasta Meta App Review (DIFERIDO-02). X queda FUERA del CHECK (D-19 permanente T3).

``competidores`` ya existe (benchmark.py); NO se recrea. D-22 opción B: el cliente declara
competidores en onboarding y se persiste el array de IDs en ``dirigentes.competidor_directo_ids``
más filas ``competidores`` si no existen.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "s5m1_onboarding_tables"
down_revision = "s3m1_promesas_dirigente"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =========================================================================
    # 1. dirigentes.perfil_1_5 (§1.5 MASTER · 4 perfiles onboarding)
    # =========================================================================
    op.add_column(
        "dirigentes",
        sa.Column("perfil_1_5", sa.String(30), nullable=True),
    )
    op.create_check_constraint(
        "ck_dirigentes_perfil_1_5",
        "dirigentes",
        "perfil_1_5 IS NULL OR perfil_1_5 IN ("
        "'politico_activo', 'funcionario_gobierno', "
        "'figura_precampaña', 'empresario_transicion')",
    )

    # =========================================================================
    # 2. social_profiles.is_confirmed (D-23 regla dura · scraping solo si confirmado)
    # =========================================================================
    op.add_column(
        "social_profiles",
        sa.Column(
            "is_confirmed",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
    )
    op.create_index(
        "idx_social_profiles_confirmed",
        "social_profiles",
        ["dirigente_id", "is_confirmed"],
    )

    # =========================================================================
    # 3. Extender enum data_source_enum con 'manual_onboarding'
    # =========================================================================
    # PG requiere commit separado para ALTER TYPE ADD VALUE
    op.execute("ALTER TYPE data_source_enum ADD VALUE IF NOT EXISTS 'manual_onboarding'")

    # =========================================================================
    # 4. oauth_tokens_by_platform
    # =========================================================================
    op.create_table(
        "oauth_tokens_by_platform",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "dirigente_id", sa.Integer,
            sa.ForeignKey("dirigentes.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column(
            "org_id", sa.Integer,
            sa.ForeignKey("organizaciones.id", ondelete="CASCADE"),
            nullable=True, index=True,
        ),
        sa.Column("platform", sa.String(20), nullable=False),
        # Tokens cifrados (pgcrypto en producción · stub sha256 hash placeholder en MVP)
        sa.Column("token_hash", sa.Text, nullable=True),
        sa.Column("refresh_token_hash", sa.Text, nullable=True),
        sa.Column("platform_user_id", sa.String(100), nullable=True),
        sa.Column("platform_username", sa.String(100), nullable=True),
        sa.Column(
            "scopes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_refreshed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "is_stub",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("TRUE"),
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"), nullable=False,
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"), nullable=False,
        ),
        sa.CheckConstraint(
            "platform IN ('instagram','facebook_page','tiktok','youtube')",
            name="ck_oauth_tokens_platform",
        ),
        sa.CheckConstraint(
            "status IN ('active','expired','revoked_by_user','refresh_failed','pending_relink')",
            name="ck_oauth_tokens_status",
        ),
    )
    op.create_index(
        "idx_oauth_tokens_dirigente_platform",
        "oauth_tokens_by_platform",
        ["dirigente_id", "platform"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    # Orden inverso
    op.drop_index(
        "idx_oauth_tokens_dirigente_platform",
        table_name="oauth_tokens_by_platform",
    )
    op.drop_table("oauth_tokens_by_platform")

    op.drop_index("idx_social_profiles_confirmed", table_name="social_profiles")
    op.drop_column("social_profiles", "is_confirmed")

    op.drop_constraint("ck_dirigentes_perfil_1_5", "dirigentes", type_="check")
    op.drop_column("dirigentes", "perfil_1_5")

    # NOTE: no se puede DROP VALUE de un enum en PostgreSQL sin recrear el tipo.
    # Se deja 'manual_onboarding' como residuo en el enum — inocuo.
