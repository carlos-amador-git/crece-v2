"""Sprint S1 consolidated schema migration.

Revision ID: s1m1_sprint_s1_schema
Revises: 3d6fe3f1660d
Create Date: 2026-04-19 00:00:00.000000

Sprint S1 Backend Foundations — schema consolidado (MASTER §5 S1).

Cambios:

1. `dirigentes` extendida con 4 columnas:
   - data_fidelity_tier JSONB (map {plataforma: T1/T2/T3/N-A}, seed desde settings_fidelity.json)
   - estrato_politico VARCHAR(20) CHECK (Nano/Micro/Mid/Macro/Mega)
   - competidor_directo_ids INTEGER[] (array FK a dirigentes.id)
   - data_origin VARCHAR(10) CHECK (T1/T2/T3/N-A), default T3 scraping

2. `social_profile_snapshots` extendida con:
   - data_origin_checkpoint TIMESTAMP TZ — marca transición T3→T1 post-OAuth (§4.5 D-17)

3. `social_posts` extendida con:
   - topics_extracted JSONB — output Gemma 3:12b topic extractor (T5)

4. Tabla nueva `recomendaciones_plan_ia` (18 columnas + 3 índices) — §6.3.2 MASTER, D-17
   · FK: plan_ia_id→planes_ia, dirigente_id→dirigentes, org_id→organizaciones,
         post_ejecutor_id→social_posts

5. Tabla nueva `compliance_purge_audit` (D-18 ARCO LFPDPPP)

6. Tabla nueva `llm_health_log` (D-21 Coolify dual-mode)

NOTA: migration hand-written (NO autogenerate) porque existen tablas pre-S1 sin modelo
SQLAlchemy (encuestas_publicas, social_comments, resultados_electorales_seccion) que un
autogenerate borraría. Se respeta ese drift intencionalmente.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 's1m1_sprint_s1_schema'
down_revision = '3d6fe3f1660d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =========================================================================
    # 1. Extend `dirigentes`
    # =========================================================================
    op.add_column(
        'dirigentes',
        sa.Column('data_fidelity_tier', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        'dirigentes',
        sa.Column('estrato_politico', sa.String(20), nullable=True),
    )
    op.create_check_constraint(
        'ck_dirigentes_estrato_politico',
        'dirigentes',
        "estrato_politico IS NULL OR estrato_politico IN ('Nano','Micro','Mid','Macro','Mega')",
    )
    op.add_column(
        'dirigentes',
        sa.Column(
            'competidor_directo_ids',
            postgresql.ARRAY(sa.Integer()),
            nullable=False,
            server_default='{}',
        ),
    )
    op.add_column(
        'dirigentes',
        sa.Column(
            'data_origin',
            sa.String(10),
            nullable=False,
            server_default='T3',
        ),
    )
    op.create_check_constraint(
        'ck_dirigentes_data_origin',
        'dirigentes',
        "data_origin IN ('T1','T2','T3','N-A')",
    )

    # =========================================================================
    # 2. Extend `social_profile_snapshots`
    # =========================================================================
    op.add_column(
        'social_profile_snapshots',
        sa.Column('data_origin_checkpoint', sa.DateTime(timezone=True), nullable=True),
    )

    # =========================================================================
    # 3. Extend `social_posts`
    # =========================================================================
    op.add_column(
        'social_posts',
        sa.Column('topics_extracted', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    # =========================================================================
    # 4. Create `recomendaciones_plan_ia` (MASTER §6.3.2, D-17)
    # =========================================================================
    op.create_table(
        'recomendaciones_plan_ia',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            'plan_ia_id',
            sa.Integer,
            sa.ForeignKey('planes_ia.id', ondelete='CASCADE'),
            nullable=True,
            index=True,
        ),
        sa.Column(
            'dirigente_id',
            sa.Integer,
            sa.ForeignKey('dirigentes.id', ondelete='CASCADE'),
            nullable=False,
            index=True,
        ),
        sa.Column(
            'org_id',
            sa.Integer,
            sa.ForeignKey('organizaciones.id', ondelete='CASCADE'),
            nullable=False,
            index=True,
        ),
        sa.Column('tipo', sa.String(20), nullable=False),
        sa.Column('accion_texto', sa.Text, nullable=False),
        sa.Column('ventana_inicio', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ventana_fin', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ventana_duracion_dias', sa.Integer, nullable=False, server_default='14'),
        sa.Column('criterio_exito', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('principio_conductual', sa.String(100), nullable=True),
        sa.Column('evidencia_respaldo', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('estado', sa.String(20), nullable=False, server_default='propuesta'),
        sa.Column(
            'post_ejecutor_id',
            sa.Integer,
            sa.ForeignKey('social_posts.id', ondelete='SET NULL'),
            nullable=True,
        ),
        sa.Column('metricas_predichas', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('metricas_observadas', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('veredicto', sa.String(20), nullable=True),
        sa.Column(
            'veredicto_editado_por_cliente',
            sa.Boolean,
            nullable=False,
            server_default=sa.text('false'),
        ),
        sa.Column('veredicto_original', sa.String(20), nullable=True),
        sa.Column('notas_cliente', sa.Text, nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text('NOW()'),
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text('NOW()'),
        ),
        sa.CheckConstraint(
            "tipo IN ('start','stop','continue')",
            name='ck_recom_tipo',
        ),
        sa.CheckConstraint(
            "estado IN ('propuesta','aprobada','rechazada','modificada','ejecutada','completada','fallida')",
            name='ck_recom_estado',
        ),
        sa.CheckConstraint(
            "veredicto IS NULL OR veredicto IN ('exitosa','parcial','fallida')",
            name='ck_recom_veredicto',
        ),
    )
    op.create_index(
        'idx_recom_dirigente_estado',
        'recomendaciones_plan_ia',
        ['dirigente_id', 'estado'],
    )
    op.create_index(
        'idx_recom_ventana_activa',
        'recomendaciones_plan_ia',
        ['ventana_fin'],
        postgresql_where=sa.text("estado = 'ejecutada'"),
    )
    op.create_index(
        'idx_recom_veredicto',
        'recomendaciones_plan_ia',
        ['dirigente_id', 'veredicto'],
        postgresql_where=sa.text("estado = 'completada'"),
    )

    # =========================================================================
    # 5. Create `compliance_purge_audit` (D-18 ARCO LFPDPPP)
    # =========================================================================
    op.create_table(
        'compliance_purge_audit',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            'admin_user_id',
            sa.Integer,
            sa.ForeignKey('users.id', ondelete='RESTRICT'),
            nullable=False,
            index=True,
        ),
        sa.Column('author_hash', sa.String(64), nullable=False),
        sa.Column(
            'rows_deleted_social_comments',
            sa.Integer,
            nullable=False,
            server_default='0',
        ),
        sa.Column(
            'rows_deleted_social_posts',
            sa.Integer,
            nullable=False,
            server_default='0',
        ),
        sa.Column(
            'rows_deleted_vectors',
            sa.Integer,
            nullable=False,
            server_default='0',
        ),
        sa.Column('justificacion', sa.Text, nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text('NOW()'),
        ),
    )
    op.create_index(
        'idx_purge_audit_hash',
        'compliance_purge_audit',
        ['author_hash', 'created_at'],
        postgresql_ops={'created_at': 'DESC'},
    )
    op.create_index(
        'idx_purge_audit_admin',
        'compliance_purge_audit',
        ['admin_user_id', 'created_at'],
        postgresql_ops={'created_at': 'DESC'},
    )

    # =========================================================================
    # 6. Create `llm_health_log` (D-21 Coolify dual-mode)
    # =========================================================================
    op.create_table(
        'llm_health_log',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('provider', sa.String(20), nullable=False),
        sa.Column('layer', sa.String(20), nullable=False),
        sa.Column('latency_ms', sa.Integer, nullable=True),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('error_text', sa.Text, nullable=True),
        sa.Column('model', sa.String(50), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text('NOW()'),
        ),
        sa.CheckConstraint(
            "provider IN ('mac_m4_primary','coolify_vps_failover')",
            name='ck_llm_health_provider',
        ),
        sa.CheckConstraint(
            "layer IN ('ping','inference_warm','inference_cold','prewarm')",
            name='ck_llm_health_layer',
        ),
        sa.CheckConstraint(
            "status IN ('ok','degraded','fail','timeout')",
            name='ck_llm_health_status',
        ),
    )
    op.create_index(
        'idx_llm_health_provider_time',
        'llm_health_log',
        ['provider', 'created_at'],
        postgresql_ops={'created_at': 'DESC'},
    )
    op.create_index(
        'idx_llm_health_status',
        'llm_health_log',
        ['status', 'created_at'],
        postgresql_ops={'created_at': 'DESC'},
        postgresql_where=sa.text("status != 'ok'"),
    )


def downgrade() -> None:
    # 6. llm_health_log
    op.drop_index('idx_llm_health_status', table_name='llm_health_log')
    op.drop_index('idx_llm_health_provider_time', table_name='llm_health_log')
    op.drop_table('llm_health_log')

    # 5. compliance_purge_audit
    op.drop_index('idx_purge_audit_admin', table_name='compliance_purge_audit')
    op.drop_index('idx_purge_audit_hash', table_name='compliance_purge_audit')
    op.drop_table('compliance_purge_audit')

    # 4. recomendaciones_plan_ia
    op.drop_index('idx_recom_veredicto', table_name='recomendaciones_plan_ia')
    op.drop_index('idx_recom_ventana_activa', table_name='recomendaciones_plan_ia')
    op.drop_index('idx_recom_dirigente_estado', table_name='recomendaciones_plan_ia')
    op.drop_table('recomendaciones_plan_ia')

    # 3. social_posts.topics_extracted
    op.drop_column('social_posts', 'topics_extracted')

    # 2. social_profile_snapshots.data_origin_checkpoint
    op.drop_column('social_profile_snapshots', 'data_origin_checkpoint')

    # 1. dirigentes (orden inverso)
    op.drop_constraint('ck_dirigentes_data_origin', 'dirigentes', type_='check')
    op.drop_column('dirigentes', 'data_origin')
    op.drop_column('dirigentes', 'competidor_directo_ids')
    op.drop_constraint('ck_dirigentes_estrato_politico', 'dirigentes', type_='check')
    op.drop_column('dirigentes', 'estrato_politico')
    op.drop_column('dirigentes', 'data_fidelity_tier')
