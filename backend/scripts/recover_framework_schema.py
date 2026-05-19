"""Recovery script para schema framework_matrix (drift detectado 2026-05-09).

La migration f7a8b9c0d1e2_political_framework.py tiene `down_revision='d5d6d7d8d9e0'`
que no encadena con el chain actual (head: phb1_pesos_target_politico). Como
resultado nunca se aplicó. Algunas columnas se filtraron por otras vías
(dirigentes.rol_politico, social_posts.target_politico) pero las 4 tablas
framework_* + 9 columnas social_posts siguen faltando.

Este script crea las piezas missing con SQL idempotente CREATE IF NOT EXISTS,
sin tocar alembic_version. Documentado como schema drift recovery.

Usage:
    docker exec crece-backend python scripts/recover_framework_schema.py
"""
from __future__ import annotations

import asyncio
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

DDL_STATEMENTS = [
    # contexto_politico
    """
    CREATE TABLE IF NOT EXISTS contexto_politico (
        id SERIAL PRIMARY KEY,
        ambito VARCHAR(20) NOT NULL,
        entidad VARCHAR(80),
        partido_gobernante VARCHAR(20) NOT NULL,
        vigente_desde DATE NOT NULL,
        vigente_hasta DATE,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_contexto_ambito_entidad ON contexto_politico(ambito, entidad)",

    # framework_matrix_defaults
    """
    CREATE TABLE IF NOT EXISTS framework_matrix_defaults (
        id SERIAL PRIMARY KEY,
        version VARCHAR(20) NOT NULL,
        rol VARCHAR(20) NOT NULL,
        tono VARCHAR(30) NOT NULL,
        target VARCHAR(30) NOT NULL,
        score_politico SMALLINT NOT NULL,
        descripcion VARCHAR(200),
        created_at TIMESTAMPTZ DEFAULT NOW(),
        CONSTRAINT uq_framework_defaults UNIQUE (version, rol, tono, target)
    )
    """,

    # framework_overrides_org
    """
    CREATE TABLE IF NOT EXISTS framework_overrides_org (
        id SERIAL PRIMARY KEY,
        org_id INTEGER NOT NULL REFERENCES organizaciones(id) ON DELETE CASCADE,
        rol VARCHAR(20) NOT NULL,
        tono VARCHAR(30) NOT NULL,
        target VARCHAR(30) NOT NULL,
        score_politico SMALLINT NOT NULL,
        modified_by_user_id INTEGER NOT NULL REFERENCES users(id),
        modified_at TIMESTAMPTZ DEFAULT NOW(),
        CONSTRAINT uq_framework_overrides UNIQUE (org_id, rol, tono, target)
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_framework_overrides_org ON framework_overrides_org(org_id)",

    # framework_audit_log
    """
    CREATE TABLE IF NOT EXISTS framework_audit_log (
        id SERIAL PRIMARY KEY,
        org_id INTEGER NOT NULL REFERENCES organizaciones(id) ON DELETE CASCADE,
        rol VARCHAR(20) NOT NULL,
        tono VARCHAR(30) NOT NULL,
        target VARCHAR(30) NOT NULL,
        score_before SMALLINT,
        score_after SMALLINT NOT NULL,
        score_default SMALLINT NOT NULL,
        changed_by_user_id INTEGER NOT NULL REFERENCES users(id),
        changed_at TIMESTAMPTZ DEFAULT NOW(),
        razon TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_framework_audit_org ON framework_audit_log(org_id)",

    # social_posts columns (9 missing — todas con IF NOT EXISTS pattern)
    "ALTER TABLE social_posts ADD COLUMN IF NOT EXISTS tono_discurso VARCHAR(30)",
    "ALTER TABLE social_posts ADD COLUMN IF NOT EXISTS sentimiento_politico_ajustado SMALLINT",
    "ALTER TABLE social_posts ADD COLUMN IF NOT EXISTS controversy_score FLOAT",
    "ALTER TABLE social_posts ADD COLUMN IF NOT EXISTS toxicity_score FLOAT",
    "ALTER TABLE social_posts ADD COLUMN IF NOT EXISTS topics_jsonb JSONB",
    "ALTER TABLE social_posts ADD COLUMN IF NOT EXISTS platform_adjusted_sentiment FLOAT",
    "ALTER TABLE social_posts ADD COLUMN IF NOT EXISTS llm_razon TEXT",
    "ALTER TABLE social_posts ADD COLUMN IF NOT EXISTS llm_modelo VARCHAR(50)",
    "ALTER TABLE social_posts ADD COLUMN IF NOT EXISTS llm_processed_at TIMESTAMPTZ",
]


async def main() -> int:
    eng = create_async_engine(os.environ["DATABASE_URL"], echo=False)
    Session = async_sessionmaker(eng, expire_on_commit=False)

    applied = 0
    skipped = 0
    async with Session() as db:
        for ddl in DDL_STATEMENTS:
            label = ddl.strip().split("\n")[0][:80]
            try:
                await db.execute(text(ddl))
                applied += 1
                print(f"  ✓ {label}")
            except Exception as e:
                # Si falla por estado ya consistente, contar como skipped
                msg = str(e).split("\n")[0][:120]
                if "already exists" in msg.lower():
                    skipped += 1
                    print(f"  ~ {label} (already exists)")
                else:
                    print(f"  ✗ {label}: {msg}")
                    return 1
        await db.commit()

    print(f"\nDDL applied={applied} skipped={skipped}")

    # Validación post
    async with Session() as db:
        for tab in ("contexto_politico", "framework_matrix_defaults",
                    "framework_overrides_org", "framework_audit_log"):
            r = await db.execute(text(
                f"SELECT COUNT(*) FROM information_schema.tables WHERE table_name='{tab}'"
            ))
            print(f"  {tab}: {'OK' if r.scalar() else 'MISSING'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
