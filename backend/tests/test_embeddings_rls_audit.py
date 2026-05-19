"""S4.8 — Audit RLS multi-tenant sobre search_similar_posts.

Requisito de seguridad crítico del Sprint 4: cuando un endpoint multi-tenant
consulta posts similares por embedding, NUNCA debe retornar un post que
pertenezca a otra organización.

`social_posts` no tiene `org_id` directo — la tenancy se media vía
`social_posts.profile_id → social_profiles.dirigente_id → dirigentes.org_id`.
El fix de S4.8 agrega JOIN explícito y `WHERE d.org_id = :org_id` en la
query. Este test verifica:

    1. La firma de `search_similar_posts` requiere `org_id` (kw-only)
    2. Dados 2 posts de 2 orgs distintas con embeddings idénticos,
       llamar desde org_A devuelve solo el post de org_A
    3. El plan de ejecución del planner aplica el filtro de org_id
       (manual inspección via EXPLAIN, no assert rígido porque el planner
       puede elegir pre-filter o post-filter y ambos son correctos)
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.services import embeddings

FAKE_EMBEDDING_A = [0.1] * 384
FAKE_EMBEDDING_B = [0.11] * 384  # very similar to A


@pytest.fixture
async def db() -> AsyncSession:
    engine = create_async_engine(settings.DATABASE_URL)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture
async def two_orgs_with_posts(db: AsyncSession):
    """Create 2 orgs, 2 dirigentes (one per org), 2 profiles, 2 posts.

    Each post gets a near-identical fake embedding so that a similarity
    search would return both if no org filter were applied.
    """
    await db.execute(
        text(
            "INSERT INTO organizaciones (nombre, slug, tipo, is_active, created_at, updated_at) "
            "VALUES ('RLS Audit Org A', 'rls-audit-a', 'PARTIDO', true, now(), now()) "
            "ON CONFLICT (slug) DO NOTHING"
        )
    )
    await db.execute(
        text(
            "INSERT INTO organizaciones (nombre, slug, tipo, is_active, created_at, updated_at) "
            "VALUES ('RLS Audit Org B', 'rls-audit-b', 'PARTIDO', true, now(), now()) "
            "ON CONFLICT (slug) DO NOTHING"
        )
    )
    await db.commit()

    row_a = (
        await db.execute(text("SELECT id FROM organizaciones WHERE slug='rls-audit-a'"))
    ).scalar_one()
    row_b = (
        await db.execute(text("SELECT id FROM organizaciones WHERE slug='rls-audit-b'"))
    ).scalar_one()

    dir_a = (
        await db.execute(
            text(
                "INSERT INTO dirigentes (full_name, cargo, partido, estado, org_id, created_at, updated_at) "
                "VALUES ('S4.8 Test Dir A', 'cargo', 'MC', 'CDMX', :o, now(), now()) RETURNING id"
            ),
            {"o": row_a},
        )
    ).scalar_one()
    dir_b = (
        await db.execute(
            text(
                "INSERT INTO dirigentes (full_name, cargo, partido, estado, org_id, created_at, updated_at) "
                "VALUES ('S4.8 Test Dir B', 'cargo', 'MC', 'CDMX', :o, now(), now()) RETURNING id"
            ),
            {"o": row_b},
        )
    ).scalar_one()

    prof_a = (
        await db.execute(
            text(
                "INSERT INTO social_profiles (dirigente_id, platform, handle, followers_count, following_count, posts_count) "
                "VALUES (:d, 'TWITTER', 's4_8_a_prof', 10, 0, 0) RETURNING id"
            ),
            {"d": dir_a},
        )
    ).scalar_one()
    prof_b = (
        await db.execute(
            text(
                "INSERT INTO social_profiles (dirigente_id, platform, handle, followers_count, following_count, posts_count) "
                "VALUES (:d, 'TWITTER', 's4_8_b_prof', 10, 0, 0) RETURNING id"
            ),
            {"d": dir_b},
        )
    ).scalar_one()

    post_a = (
        await db.execute(
            text(
                "INSERT INTO social_posts "
                "(profile_id, platform_post_id, content, post_type, published_at, likes, comments, "
                " shares, views, engagement_rate, is_political, embedding, scraped_at) "
                "VALUES (:p, 's4_8_post_a', 'political content A', 'TEXT', now(), 0, 0, 0, 0, 0.0, true, "
                " cast(:emb AS vector), now()) RETURNING id"
            ),
            {"p": prof_a, "emb": str(FAKE_EMBEDDING_A)},
        )
    ).scalar_one()
    post_b = (
        await db.execute(
            text(
                "INSERT INTO social_posts "
                "(profile_id, platform_post_id, content, post_type, published_at, likes, comments, "
                " shares, views, engagement_rate, is_political, embedding, scraped_at) "
                "VALUES (:p, 's4_8_post_b', 'political content B', 'TEXT', now(), 0, 0, 0, 0, 0.0, true, "
                " cast(:emb AS vector), now()) RETURNING id"
            ),
            {"p": prof_b, "emb": str(FAKE_EMBEDDING_B)},
        )
    ).scalar_one()
    await db.commit()

    yield {
        "org_a": row_a,
        "org_b": row_b,
        "post_a": post_a,
        "post_b": post_b,
        "dir_a": dir_a,
        "dir_b": dir_b,
        "prof_a": prof_a,
        "prof_b": prof_b,
    }

    # Cleanup
    await db.execute(text("DELETE FROM social_posts WHERE id IN (:a, :b)"), {"a": post_a, "b": post_b})
    await db.execute(text("DELETE FROM social_profiles WHERE id IN (:a, :b)"), {"a": prof_a, "b": prof_b})
    await db.execute(text("DELETE FROM dirigentes WHERE id IN (:a, :b)"), {"a": dir_a, "b": dir_b})
    await db.execute(text("DELETE FROM organizaciones WHERE slug IN ('rls-audit-a', 'rls-audit-b')"))
    await db.commit()


def test_search_similar_posts_requires_org_id_kw_only() -> None:
    """Calling without org_id raises TypeError (signature enforces kw-only)."""
    import inspect

    sig = inspect.signature(embeddings.search_similar_posts)
    org_param = sig.parameters.get("org_id")
    assert org_param is not None, "org_id must be a parameter"
    assert org_param.kind == inspect.Parameter.KEYWORD_ONLY, (
        "org_id must be KEYWORD_ONLY to prevent accidental positional misuse"
    )
    assert org_param.default is inspect.Parameter.empty, (
        "org_id must be required (no default)"
    )


@pytest.mark.asyncio
async def test_cross_org_leak_is_impossible(
    db: AsyncSession, two_orgs_with_posts, monkeypatch
):
    """Query from org_a must NOT return org_b's post, even with similar embeddings."""
    monkeypatch.setattr(embeddings, "embed_text", lambda _: FAKE_EMBEDDING_A)

    fixture = two_orgs_with_posts

    # Query from org A — should only see post A
    results_a = await embeddings.search_similar_posts(
        db, "query", org_id=fixture["org_a"], limit=10, min_similarity=0.0
    )
    ids_a = {r["id"] for r in results_a}
    assert fixture["post_a"] in ids_a
    assert fixture["post_b"] not in ids_a

    # Query from org B — should only see post B
    results_b = await embeddings.search_similar_posts(
        db, "query", org_id=fixture["org_b"], limit=10, min_similarity=0.0
    )
    ids_b = {r["id"] for r in results_b}
    assert fixture["post_b"] in ids_b
    assert fixture["post_a"] not in ids_b


@pytest.mark.asyncio
async def test_explain_plan_applies_org_filter(
    db: AsyncSession, two_orgs_with_posts
):
    """EXPLAIN must mention the org_id filter in the plan (pre or post HNSW)."""
    fixture = two_orgs_with_posts
    # Use raw query shape identical to search_similar_posts but without
    # embed_text roundtrip.
    plan_result = await db.execute(
        text(
            "EXPLAIN SELECT sp.id FROM social_posts sp "
            "JOIN social_profiles prof ON prof.id = sp.profile_id "
            "JOIN dirigentes d ON d.id = prof.dirigente_id "
            "WHERE d.org_id = :org_id "
            "  AND sp.embedding IS NOT NULL "
            "ORDER BY sp.embedding <=> cast(:emb AS vector) LIMIT 10"
        ),
        {"org_id": fixture["org_a"], "emb": str(FAKE_EMBEDDING_A)},
    )
    plan_lines = [row[0] for row in plan_result.fetchall()]
    plan_text = "\n".join(plan_lines)
    # The org_id filter must appear somewhere in the plan — either as a
    # Filter clause on dirigentes, or pushed into an Index Cond. We don't
    # care which; we only care it's there.
    assert "org_id" in plan_text, f"plan missing org_id filter:\n{plan_text}"
