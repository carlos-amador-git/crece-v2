"""Tests S3 recompute helpers (matriz v2 lookup).

Cubre los criterios de aceptación del plan:
- match en matriz → score correcto
- miss en matriz → score=0 (NO None)
- comment con runner vocab → mapper aplica
- comment con v2 vocab → lookup directo (passthrough idempotente)
- post-level recompute usa contexto='post_dirigente'
- idempotencia (correr 2 veces da mismo resultado)
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.score_recompute import (
    recompute_dirigente_aggregate,
    recompute_score_comment,
    recompute_score_post,
)


# ─── Fixtures helpers ────────────────────────────────────────────────────────

async def _ensure_alembic_columns(db: AsyncSession) -> None:
    """Schema gaps · `Base.metadata.create_all` no ejecuta migrations.

    Estas columnas existen en producción vía Alembic pero no en el modelo
    SQLAlchemy actual · las agregamos manualmente al test DB para que el
    helper score_recompute pueda hacer SELECT/INSERT sin romper.

    Idempotente: ADD COLUMN IF NOT EXISTS.
    """
    await db.execute(text(
        "ALTER TABLE social_posts ADD COLUMN IF NOT EXISTS "
        "tono_discurso VARCHAR(30)"
    ))
    await db.execute(text(
        "ALTER TABLE social_comments ADD COLUMN IF NOT EXISTS "
        "nlp_tono VARCHAR(30)"
    ))
    await db.execute(text(
        "ALTER TABLE social_comments ADD COLUMN IF NOT EXISTS "
        "nlp_target VARCHAR(30)"
    ))
    await db.commit()


async def _ensure_matrix_table(db: AsyncSession) -> None:
    """`framework_matrix_defaults` se crea vía Alembic, no via Base.metadata.

    Los tests usan `Base.metadata.create_all` que NO ejecuta migrations, por
    eso esta tabla no existe en el test DB. La creamos aquí con el schema
    mínimo necesario · idempotente.
    """
    await db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS framework_matrix_defaults (
                id SERIAL PRIMARY KEY,
                version VARCHAR(20) NOT NULL,
                rol VARCHAR(20) NOT NULL,
                tono VARCHAR(30) NOT NULL,
                target VARCHAR(30) NOT NULL,
                contexto VARCHAR(20) NOT NULL DEFAULT 'post_dirigente',
                score_politico SMALLINT NOT NULL,
                descripcion VARCHAR(200),
                created_at TIMESTAMPTZ DEFAULT now(),
                CONSTRAINT uq_framework_defaults_v2_test
                    UNIQUE (version, rol, tono, target, contexto)
            )
            """
        )
    )
    # Limpia rows previos · TRUNCATE de conftest no borra esta tabla manual
    await db.execute(text("DELETE FROM framework_matrix_defaults"))
    await db.commit()


async def _seed_matrix(db: AsyncSession) -> None:
    """Insert mínima de framework_matrix_defaults para los tests."""
    await _ensure_matrix_table(db)
    rules = [
        # comment_tercero (oposicion)
        ("oposicion", "celebratorio", "dirigente", "comment_tercero", 1),
        ("oposicion", "ataque", "dirigente", "comment_tercero", -1),
        ("oposicion", "celebratorio", "autopromocion", "comment_tercero", 0),
        ("oposicion", "personal", "dirigente", "comment_tercero", 0),
        # post_dirigente (oposicion)
        ("oposicion", "critico", "gobierno", "post_dirigente", 1),
        ("oposicion", "celebratorio", "ciudadania", "post_dirigente", 0),
    ]
    for rol, tono, target, contexto, score in rules:
        await db.execute(
            text(
                """INSERT INTO framework_matrix_defaults
                   (version, rol, tono, target, contexto, score_politico)
                   VALUES ('v1', :rol, :tono, :target, :contexto, :score)"""
            ),
            {"rol": rol, "tono": tono, "target": target,
             "contexto": contexto, "score": score},
        )
    await db.commit()


async def _seed_dirigente_with_post_and_comment(
    db: AsyncSession,
    *,
    rol_politico: str = "oposicion",
    nlp_tono: str | None = "celebratorio",
    nlp_target: str | None = "dirigente",
    post_tono: str = "critico",
    post_target: str = "gobierno",
    comment_content: str = "Vamos Maynez!",
) -> tuple[int, int, int]:
    """Insert dirigente + profile + post + comment. Retorna (did, pid, cid)."""
    await _ensure_alembic_columns(db)
    did = (
        await db.execute(
            text(
                """INSERT INTO dirigentes
                   (full_name, cargo, partido, estado, rol_politico,
                    sync_status, created_at, updated_at)
                   VALUES ('Test Dirigente', 'Diputado', 'MC', 'CDMX',
                           :rol, 'ready', NOW(), NOW())
                   RETURNING id"""
            ),
            {"rol": rol_politico},
        )
    ).scalar_one()

    profile_id = (
        await db.execute(
            text(
                """INSERT INTO social_profiles
                   (dirigente_id, platform, handle, followers_count,
                    following_count, posts_count, data_source, is_confirmed)
                   VALUES (:did, 'INSTAGRAM', '@test', 100, 10, 5,
                           'automated_scraper', true)
                   RETURNING id"""
            ),
            {"did": did},
        )
    ).scalar_one()

    pid = (
        await db.execute(
            text(
                """INSERT INTO social_posts
                   (profile_id, platform_post_id, content, post_type,
                    published_at, likes, comments, shares, views,
                    engagement_rate, is_political, scraped_at,
                    tono_discurso, target_politico)
                   VALUES (:pid, 'p_test_001', 'post content', 'TEXT',
                           :now, 0, 0, 0, 0, 0.0, true, :now,
                           :ptono, :ptarget)
                   RETURNING id"""
            ),
            {"pid": profile_id, "now": datetime.now(UTC),
             "ptono": post_tono, "ptarget": post_target},
        )
    ).scalar_one()

    cid = (
        await db.execute(
            text(
                """INSERT INTO social_comments
                   (parent_post_id, platform_comment_id, content,
                    author_hash, likes, nlp_tono, nlp_target)
                   VALUES (:pid, 'c_test_001', :content, 'h0', 0,
                           :tono, :target)
                   RETURNING id"""
            ),
            {"pid": pid, "content": comment_content,
             "tono": nlp_tono, "target": nlp_target},
        )
    ).scalar_one()

    await db.commit()
    return did, pid, cid


# ─── Comment recompute ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_match_v2_vocab_celebratorio_dirigente(
    db_session: AsyncSession,
):
    """Comment con vocab v2 directo → passthrough mapper → score correcto."""
    await _seed_matrix(db_session)
    _, _, cid = await _seed_dirigente_with_post_and_comment(
        db_session,
        nlp_tono="celebratorio",
        nlp_target="dirigente",
    )

    score = await recompute_score_comment(db_session, cid)

    assert score == 1


@pytest.mark.asyncio
async def test_miss_returns_zero_not_none(db_session: AsyncSession):
    """Comment cuya combinación no existe en la matriz → score=0 (no None)."""
    await _seed_matrix(db_session)
    _, _, cid = await _seed_dirigente_with_post_and_comment(
        db_session,
        # informativo+ciudadania no está seeded → miss
        nlp_tono="informativo",
        nlp_target="ciudadania",
    )

    score = await recompute_score_comment(db_session, cid)

    assert score == 0
    assert isinstance(score, int)


@pytest.mark.asyncio
async def test_runner_vocab_maps_via_v3(db_session: AsyncSession):
    """Comment con runner-vocab antiguo (elogio) → mapper traduce a celebratorio."""
    await _seed_matrix(db_session)
    _, _, cid = await _seed_dirigente_with_post_and_comment(
        db_session,
        nlp_tono="elogio",          # runner antiguo
        nlp_target="dirigente_post", # runner antiguo
    )

    score = await recompute_score_comment(db_session, cid)

    # mapper: elogio→celebratorio · dirigente_post→dirigente · matriz devuelve 1
    assert score == 1


@pytest.mark.asyncio
async def test_v2_vocab_passthrough_idempotent(db_session: AsyncSession):
    """Comment ya en v2 vocab debe dar el mismo score que su equivalente runner."""
    await _seed_matrix(db_session)
    _, _, cid_v2 = await _seed_dirigente_with_post_and_comment(
        db_session,
        nlp_tono="ataque",      # idéntico runner ↔ v2
        nlp_target="dirigente",  # ya v2
    )
    score = await recompute_score_comment(db_session, cid_v2)
    assert score == -1  # ataque + dirigente + oposicion + comment_tercero


@pytest.mark.asyncio
async def test_idempotency_two_calls(db_session: AsyncSession):
    """Llamar dos veces produce mismo resultado · cero side-effects."""
    await _seed_matrix(db_session)
    _, _, cid = await _seed_dirigente_with_post_and_comment(
        db_session,
        nlp_tono="celebratorio",
        nlp_target="dirigente",
    )

    s1 = await recompute_score_comment(db_session, cid)
    s2 = await recompute_score_comment(db_session, cid)
    s3 = await recompute_score_comment(db_session, cid)

    assert s1 == s2 == s3 == 1


@pytest.mark.asyncio
async def test_comment_without_nlp_returns_zero(db_session: AsyncSession):
    """Comment sin nlp_tono/nlp_target → 0 (no excepción)."""
    await _seed_matrix(db_session)
    _, _, cid = await _seed_dirigente_with_post_and_comment(
        db_session,
        nlp_tono=None,
        nlp_target=None,
    )

    score = await recompute_score_comment(db_session, cid)

    assert score == 0


@pytest.mark.asyncio
async def test_comment_inexistente_returns_zero(db_session: AsyncSession):
    """comment_id inexistente → 0 (no excepción)."""
    score = await recompute_score_comment(db_session, 999999)
    assert score == 0


# ─── Post recompute ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_post_uses_post_dirigente_contexto(db_session: AsyncSession):
    """recompute_score_post hace lookup con contexto='post_dirigente'."""
    await _seed_matrix(db_session)
    _, pid, _ = await _seed_dirigente_with_post_and_comment(
        db_session,
        post_tono="critico",
        post_target="gobierno",
    )

    score = await recompute_score_post(db_session, pid)

    # critico+gobierno+oposicion+post_dirigente → 1
    assert score == 1


@pytest.mark.asyncio
async def test_post_target_no_determinado_returns_zero(
    db_session: AsyncSession,
):
    """target_politico='no_determinado' (D-23-G fallback) → 0 sin lookup."""
    await _seed_matrix(db_session)
    _, pid, _ = await _seed_dirigente_with_post_and_comment(
        db_session,
        post_tono="critico",
        post_target="no_determinado",
    )

    score = await recompute_score_post(db_session, pid)

    assert score == 0


# ─── Aggregate ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_aggregate_returns_counts_dict(db_session: AsyncSession):
    """recompute_dirigente_aggregate devuelve dict con conteos esperados."""
    await _seed_matrix(db_session)
    did, _, _ = await _seed_dirigente_with_post_and_comment(
        db_session,
        nlp_tono="celebratorio",
        nlp_target="dirigente",
    )

    result = await recompute_dirigente_aggregate(db_session, did)

    assert result["dirigente_id"] == did
    assert result["total_comments_evaluados"] == 1
    assert result["score_positivo"] == 1
    assert result["score_negativo"] == 0
    assert result["score_cero"] == 0
    assert result["score_promedio"] == 1.0
