"""add ciudadanos_legacy + promotores_legacy (Ruta C D-DATA-01)

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-04-11 14:00:00.000000

Tablas paralelas al CRM v2 (`ciudadanos`, `users`) para preservar el
snapshot del CRECE Oracle APEX legacy sin forzar los enums/FKs de v2.

Scope Ruta C: import filtrado a 3 alcaldías piloto (Cuauhtémoc, Benito
Juárez, Miguel Hidalgo) = ~9,723 ciudadanos + sus promotores asignados.
Datos PII: protegidos por RLS (`org_id`) y por convención, este schema
es tenant-scoped desde el día 1.

NOTA: A diferencia de la RLS sobre `dirigentes`/`users` existente, aquí
`org_id` es NOT NULL y la policy NO incluye el bypass por NULL (los
ciudadanos legacy siempre pertenecen a una org — por default la MC CDMX
root, id=3).
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ─── ciudadanos_legacy ───────────────────────────────────────────
    op.create_table(
        "ciudadanos_legacy",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("legacy_id", sa.String(length=50), nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("alcaldia_id", sa.Integer(), nullable=True),
        sa.Column("unidad_territorial_id", sa.Integer(), nullable=True),
        sa.Column("promotor_legacy_id", sa.Integer(), nullable=True),
        # Identidad
        sa.Column("nombre", sa.String(length=255), nullable=True),
        sa.Column("apellido_paterno", sa.String(length=255), nullable=True),
        sa.Column("apellido_materno", sa.String(length=255), nullable=True),
        sa.Column("fecha_nacimiento", sa.Date(), nullable=True),
        sa.Column("edad", sa.Integer(), nullable=True),
        sa.Column("sexo", sa.String(length=10), nullable=True),
        sa.Column("identidad_de_genero", sa.String(length=50), nullable=True),
        # PII contacto
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("phone_01", sa.String(length=30), nullable=True),
        sa.Column("phone_02", sa.String(length=30), nullable=True),
        sa.Column("whatsapp", sa.String(length=30), nullable=True),
        # Dirección
        sa.Column("calle", sa.String(length=255), nullable=True),
        sa.Column("numero", sa.String(length=50), nullable=True),
        sa.Column("numero_interior", sa.String(length=50), nullable=True),
        sa.Column("colonia_texto", sa.String(length=255), nullable=True),
        sa.Column("codigo_postal", sa.String(length=10), nullable=True),
        sa.Column("municipio_texto", sa.String(length=255), nullable=True),
        sa.Column("direccion_libre", sa.Text(), nullable=True),
        sa.Column("manzana", sa.String(length=50), nullable=True),
        # Geo
        sa.Column("latitud", sa.Float(), nullable=True),
        sa.Column("longitud", sa.Float(), nullable=True),
        sa.Column("latitud_cd", sa.Float(), nullable=True),
        sa.Column("longitud_cd", sa.Float(), nullable=True),
        # Territorial
        sa.Column("seccion", sa.String(length=10), nullable=True),
        sa.Column("cabecera_territorial", sa.String(length=255), nullable=True),
        # Electoral / clasificación
        sa.Column("clave_electoral", sa.String(length=30), nullable=True),
        sa.Column("origen_ciudadano", sa.String(length=50), nullable=True),
        sa.Column("rol", sa.String(length=50), nullable=True),
        sa.Column("ocupacion", sa.String(length=255), nullable=True),
        sa.Column("nivel_educativo", sa.String(length=100), nullable=True),
        sa.Column("nivel_participacion", sa.String(length=50), nullable=True),
        sa.Column("disposicion_tiempo", sa.String(length=100), nullable=True),
        sa.Column("temas_de_interes", sa.Text(), nullable=True),
        sa.Column("red_social", sa.String(length=50), nullable=True),
        sa.Column("red_social_descripcion", sa.String(length=500), nullable=True),
        sa.Column("residencia_si_no", sa.String(length=5), nullable=True),
        # Estado CRM
        sa.Column("contactado", sa.String(length=10), nullable=True),
        sa.Column("respuesta", sa.Text(), nullable=True),
        sa.Column("lista", sa.String(length=50), nullable=True),
        sa.Column("aprobado", sa.String(length=10), nullable=True),
        sa.Column("procesado", sa.String(length=10), nullable=True),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("id_mc", sa.String(length=50), nullable=True),
        # Metadata Oracle APEX
        sa.Column("username_legacy", sa.String(length=100), nullable=True),
        sa.Column("project_id_legacy", sa.String(length=50), nullable=True),
        sa.Column("created_legacy", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_legacy", sa.String(length=100), nullable=True),
        sa.Column("updated_legacy", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_by_legacy", sa.String(length=100), nullable=True),
        sa.Column("raw_data", postgresql.JSONB(), nullable=True),
        sa.Column(
            "imported_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["org_id"], ["organizaciones.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["alcaldia_id"], ["alcaldias_cdmx.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["unidad_territorial_id"],
            ["unidades_territoriales.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("legacy_id", name="uq_cl_legacy_id"),
    )
    op.create_index("ix_cl_legacy_id", "ciudadanos_legacy", ["legacy_id"])
    op.create_index("ix_cl_org_id", "ciudadanos_legacy", ["org_id"])
    op.create_index("ix_cl_alcaldia_id", "ciudadanos_legacy", ["alcaldia_id"])
    op.create_index(
        "ix_cl_unidad_territorial_id",
        "ciudadanos_legacy",
        ["unidad_territorial_id"],
    )
    op.create_index("ix_cl_seccion", "ciudadanos_legacy", ["seccion"])
    op.create_index(
        "ix_cl_promotor_legacy_id",
        "ciudadanos_legacy",
        ["promotor_legacy_id"],
    )

    # RLS — estricta desde el día 1
    op.execute("ALTER TABLE ciudadanos_legacy ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE ciudadanos_legacy FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY ciudadanos_legacy_org_isolation ON ciudadanos_legacy
        USING (org_id::text = current_setting('app.current_org_id', true))
        """
    )
    op.execute(
        """
        CREATE POLICY ciudadanos_legacy_org_insert ON ciudadanos_legacy
        FOR INSERT
        WITH CHECK (org_id::text = current_setting('app.current_org_id', true))
        """
    )

    # ─── promotores_legacy ───────────────────────────────────────────
    op.create_table(
        "promotores_legacy",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("legacy_user_id", sa.String(length=50), nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("alcaldia_id", sa.Integer(), nullable=True),
        sa.Column("user_name", sa.String(length=100), nullable=False),
        sa.Column("password_hash_legacy", sa.String(length=200), nullable=True),
        sa.Column("project_id_legacy", sa.String(length=50), nullable=True),
        sa.Column("enabled", sa.String(length=5), nullable=True),
        sa.Column("super_promotor", sa.String(length=5), nullable=True),
        sa.Column("mega_promotor", sa.String(length=5), nullable=True),
        sa.Column("super_promotor_cdmx", sa.String(length=5), nullable=True),
        sa.Column("distrito_federal", sa.String(length=10), nullable=True),
        sa.Column("distritos", sa.String(length=100), nullable=True),
        sa.Column("distrito_local", sa.String(length=10), nullable=True),
        sa.Column(
            "imported_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["org_id"], ["organizaciones.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["alcaldia_id"], ["alcaldias_cdmx.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("legacy_user_id", name="uq_pl_legacy_user_id"),
        sa.UniqueConstraint("user_name", name="uq_pl_user_name"),
    )
    op.create_index("ix_pl_legacy_user_id", "promotores_legacy", ["legacy_user_id"])
    op.create_index("ix_pl_org_id", "promotores_legacy", ["org_id"])
    op.create_index("ix_pl_alcaldia_id", "promotores_legacy", ["alcaldia_id"])
    op.create_index("ix_pl_user_name", "promotores_legacy", ["user_name"])

    op.execute("ALTER TABLE promotores_legacy ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE promotores_legacy FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY promotores_legacy_org_isolation ON promotores_legacy
        USING (org_id::text = current_setting('app.current_org_id', true))
        """
    )

    # Ahora que promotores_legacy existe, le agregamos la FK deferida
    op.create_foreign_key(
        "ciudadanos_legacy_promotor_fk",
        "ciudadanos_legacy",
        "promotores_legacy",
        ["promotor_legacy_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ciudadanos_legacy_promotor_fk",
        "ciudadanos_legacy",
        type_="foreignkey",
    )
    op.execute("DROP POLICY IF EXISTS promotores_legacy_org_isolation ON promotores_legacy")
    op.execute("ALTER TABLE promotores_legacy DISABLE ROW LEVEL SECURITY")
    for idx in [
        "ix_pl_user_name",
        "ix_pl_alcaldia_id",
        "ix_pl_org_id",
        "ix_pl_legacy_user_id",
    ]:
        op.drop_index(idx, table_name="promotores_legacy")
    op.drop_table("promotores_legacy")

    op.execute("DROP POLICY IF EXISTS ciudadanos_legacy_org_insert ON ciudadanos_legacy")
    op.execute("DROP POLICY IF EXISTS ciudadanos_legacy_org_isolation ON ciudadanos_legacy")
    op.execute("ALTER TABLE ciudadanos_legacy DISABLE ROW LEVEL SECURITY")
    for idx in [
        "ix_cl_promotor_legacy_id",
        "ix_cl_seccion",
        "ix_cl_unidad_territorial_id",
        "ix_cl_alcaldia_id",
        "ix_cl_org_id",
        "ix_cl_legacy_id",
    ]:
        op.drop_index(idx, table_name="ciudadanos_legacy")
    op.drop_table("ciudadanos_legacy")
