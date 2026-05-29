"""Tests para endpoints de dashboard de perfiles observados (Sprint A · PLAN-2026-05-17).

Cubre 3 endpoints introducidos en commit f449262:
- GET /api/v1/aceptacion/watched-profiles/timeline
- GET /api/v1/aceptacion/watched-profiles/top-posts
- GET /api/v1/aceptacion/watched-profiles/interactions-summary

Casos por endpoint: happy path, RBAC (404 dirigente inexistente, 403 viewer ajeno),
edge cases (sin posts, ventana parcial vs completa, reaction_type_quality).

NO usa mocks de BD ni datos sintéticos arbitrarios — todo seeding contra schema real.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dirigente import Dirigente
from app.models.organizacion import Organizacion, TipoOrganizacion
from app.models.social import Platform, PostType, SocialPost, SocialProfile
from app.models.user import User
from app.models.watched_profile import WatchedLikeEvent, WatchedProfile, compute_watched_hash
from tests.conftest import auth_headers

BASE = "/api/v1/aceptacion/watched-profiles"


# ── social_comments no tiene modelo SQLAlchemy; conftest.create_all no la crea.
# Garantizamos su existencia en BD de test antes de cada test del módulo.
# asyncpg no acepta multi-statement en un mismo execute() → lista de DDLs.
SOCIAL_COMMENTS_DDLS = [
    """CREATE TABLE IF NOT EXISTS social_comments (
        id SERIAL PRIMARY KEY,
        parent_post_id INTEGER NOT NULL REFERENCES social_posts(id) ON DELETE CASCADE,
        platform_comment_id VARCHAR(255) NOT NULL UNIQUE,
        content TEXT NOT NULL,
        author_hash VARCHAR(64) NOT NULL,
        likes INTEGER NOT NULL DEFAULT 0,
        published_at TIMESTAMPTZ NULL,
        nlp_tono VARCHAR(30) NULL,
        nlp_target VARCHAR(30) NULL,
        nlp_polaridad SMALLINT NULL,
        nlp_model_version VARCHAR(50) NULL,
        is_reply_to_comment BOOLEAN NOT NULL DEFAULT FALSE,
        parent_comment_id INTEGER NULL REFERENCES social_comments(id) ON DELETE SET NULL,
        es_follower BOOLEAN NULL,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    )""",
    "CREATE INDEX IF NOT EXISTS ix_social_comments_parent_post_id ON social_comments(parent_post_id)",
    "CREATE INDEX IF NOT EXISTS ix_social_comments_author_hash ON social_comments(author_hash)",
    "CREATE INDEX IF NOT EXISTS ix_social_comments_author_hash_post ON social_comments(author_hash, parent_post_id)",
    "CREATE INDEX IF NOT EXISTS ix_social_comments_published_at ON social_comments(published_at)",
]


@pytest.fixture(autouse=True)
async def _ensure_social_comments_table(db_session: AsyncSession) -> None:
    """conftest.create_all no incluye social_comments (no tiene modelo SQLAlchemy).
    Esta tabla la maneja Alembic en prod; aquí la creamos idempotente para el test.
    """
    for ddl in SOCIAL_COMMENTS_DDLS:
        await db_session.execute(text(ddl))
    # TRUNCATE entre tests para aislamiento
    await db_session.execute(text("TRUNCATE social_comments RESTART IDENTITY CASCADE"))
    await db_session.commit()


# ── Helpers ──────────────────────────────────────────────────────────


async def _seed_organizacion(db: AsyncSession, *, slug: str = "org-test") -> Organizacion:
    """Crea una organización para tests que necesitan dirigente.org_id."""
    org = Organizacion(
        nombre=f"Org {slug}",
        slug=slug,
        tipo=TipoOrganizacion.PARTIDO,
    )
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return org


async def _seed_dirigente(
    db: AsyncSession, *, full_name: str = "Saymi", org_id: int | None = None
) -> Dirigente:
    d = Dirigente(
        full_name=full_name,
        cargo="Secretaria de Turismo",
        partido="MC",
        estado="Oaxaca",
        org_id=org_id,
    )
    db.add(d)
    await db.commit()
    await db.refresh(d)
    return d


async def _seed_profile(
    db: AsyncSession, dirigente: Dirigente, *, platform: Platform = Platform.FACEBOOK
) -> SocialProfile:
    p = SocialProfile(
        dirigente_id=dirigente.id,
        platform=platform,
        handle="saymi.oax",
        url="https://facebook.com/saymi.oax",
        followers_count=240_000,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


async def _seed_post(
    db: AsyncSession,
    profile: SocialProfile,
    *,
    published_at: datetime,
    content: str = "Post de prueba",
    likes: int = 0,
    platform_post_id: str | None = None,
    url: str | None = None,
) -> SocialPost:
    sp = SocialPost(
        profile_id=profile.id,
        platform_post_id=platform_post_id or f"fb_{int(published_at.timestamp())}",
        content=content,
        post_type=PostType.TEXT,
        published_at=published_at,
        likes=likes,
        raw_data={"url": url} if url else None,
    )
    db.add(sp)
    await db.commit()
    await db.refresh(sp)
    return sp


async def _seed_watched_profile(
    db: AsyncSession,
    dirigente: Dirigente,
    *,
    external_id: str = "external_user_1",
    source: str = "cliente_seed",
) -> WatchedProfile:
    wp = WatchedProfile(
        dirigente_observador_id=dirigente.id,
        org_id=dirigente.org_id,
        platform="FACEBOOK",
        profile_external_id=external_id,
        profile_handle=external_id,
        source=source,
        tags=[],
        author_hash=compute_watched_hash("FACEBOOK", external_id),
    )
    db.add(wp)
    await db.commit()
    await db.refresh(wp)
    return wp


async def _seed_reaction(
    db: AsyncSession,
    watched: WatchedProfile,
    post: SocialPost,
    *,
    reaction_type: str = "like",
) -> WatchedLikeEvent:
    ev = WatchedLikeEvent(
        watched_profile_id=watched.id,
        post_id=post.id,
        reaction_type=reaction_type,
        source="apify_reactions",
    )
    db.add(ev)
    await db.commit()
    await db.refresh(ev)
    return ev


async def _seed_comment(
    db: AsyncSession,
    post: SocialPost,
    *,
    content: str = "Buen trabajo",
    nlp_polaridad: int | None = None,
    nlp_tono: str | None = None,
    author_hash: str = "deadbeef",
    platform_comment_id: str | None = None,
) -> int:
    """Inserta un comment vía SQL — SocialComment no tiene modelo SQLAlchemy registrado.

    Retorna el id del comment insertado.
    """
    pcid = platform_comment_id or f"c_{post.id}_{author_hash}_{nlp_polaridad}"
    row = (
        await db.execute(
            text(
                """
                INSERT INTO social_comments (
                  parent_post_id, platform_comment_id, content, author_hash, likes,
                  published_at, nlp_polaridad, nlp_tono, is_reply_to_comment
                ) VALUES (
                  :pid, :pcid, :content, :ah, 0,
                  NOW(), :pol, :tono, false
                ) RETURNING id
                """
            ),
            {
                "pid": post.id,
                "pcid": pcid,
                "content": content,
                "ah": author_hash,
                "pol": nlp_polaridad,
                "tono": nlp_tono,
            },
        )
    ).first()
    await db.commit()
    return int(row[0])


# ── /timeline ────────────────────────────────────────────────────────


async def test_timeline_empty_dirigente_returns_empty_array(
    client: AsyncClient, db_session: AsyncSession, admin_token: str, admin_user: User
) -> None:
    """Dirigente sin posts ni reactions → 200 con array vacío."""
    d = await _seed_dirigente(db_session)
    resp = await client.get(
        f"{BASE}/timeline?dirigente_id={d.id}&days=44",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == []


async def test_timeline_buckets_count_posts_reactions_comments(
    client: AsyncClient, db_session: AsyncSession, admin_token: str, admin_user: User
) -> None:
    """Un post con N reactions y M comments → 1 bucket con counts correctos."""
    d = await _seed_dirigente(db_session)
    p = await _seed_profile(db_session, d)
    pub = datetime.now(UTC) - timedelta(days=10)  # ventana "complete"
    post = await _seed_post(db_session, p, published_at=pub, likes=42)

    # 2 reactions desde 2 watched profiles distintos
    w1 = await _seed_watched_profile(db_session, d, external_id="u1")
    w2 = await _seed_watched_profile(db_session, d, external_id="u2")
    await _seed_reaction(db_session, w1, post)
    await _seed_reaction(db_session, w2, post)

    # 3 comments sobre el mismo post
    await _seed_comment(db_session, post, author_hash="aa")
    await _seed_comment(db_session, post, author_hash="bb")
    await _seed_comment(db_session, post, author_hash="cc")

    resp = await client.get(
        f"{BASE}/timeline?dirigente_id={d.id}&days=44",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 1
    item = body[0]
    assert item["date"] == pub.date().isoformat()
    assert item["n_posts"] == 1
    assert item["n_reactions"] == 2
    assert item["n_comments"] == 3
    assert item["window_quality"] == "complete"


async def test_timeline_marks_recent_buckets_as_partial(
    client: AsyncClient, db_session: AsyncSession, admin_token: str, admin_user: User
) -> None:
    """Posts publicados en últimos 3 días → window_quality='partial' (acumulando)."""
    d = await _seed_dirigente(db_session)
    p = await _seed_profile(db_session, d)
    recent = datetime.now(UTC) - timedelta(days=1)
    await _seed_post(db_session, p, published_at=recent, content="Reciente")

    resp = await client.get(
        f"{BASE}/timeline?dirigente_id={d.id}&days=44",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["window_quality"] == "partial"


async def test_timeline_ignores_posts_outside_window(
    client: AsyncClient, db_session: AsyncSession, admin_token: str, admin_user: User
) -> None:
    """Posts más viejos que `days` no aparecen en la respuesta."""
    d = await _seed_dirigente(db_session)
    p = await _seed_profile(db_session, d)
    old = datetime.now(UTC) - timedelta(days=60)
    in_window = datetime.now(UTC) - timedelta(days=10)
    await _seed_post(db_session, p, published_at=old, content="Viejo")
    await _seed_post(db_session, p, published_at=in_window, content="Dentro")

    resp = await client.get(
        f"{BASE}/timeline?dirigente_id={d.id}&days=30",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["date"] == in_window.date().isoformat()


async def test_timeline_404_on_missing_dirigente(
    client: AsyncClient, admin_token: str, admin_user: User
) -> None:
    resp = await client.get(
        f"{BASE}/timeline?dirigente_id=99999&days=44",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 404


async def test_timeline_403_for_viewer_other_org(
    client: AsyncClient,
    db_session: AsyncSession,
    viewer_token: str,
    viewer_user: User,
) -> None:
    """Viewer SIN org coincidente con el dirigente → 403."""
    # viewer fixture no tiene org_id; dirigente con org_id distinto → no coincide
    org = await _seed_organizacion(db_session, slug="org-403-timeline")
    d = await _seed_dirigente(db_session, org_id=org.id)
    resp = await client.get(
        f"{BASE}/timeline?dirigente_id={d.id}&days=44",
        headers=auth_headers(viewer_token),
    )
    assert resp.status_code == 403


async def test_timeline_validates_days_range(
    client: AsyncClient, db_session: AsyncSession, admin_token: str, admin_user: User
) -> None:
    """days < 7 o > 120 → 422 validation."""
    d = await _seed_dirigente(db_session)
    for bad in (5, 121, 0):
        resp = await client.get(
            f"{BASE}/timeline?dirigente_id={d.id}&days={bad}",
            headers=auth_headers(admin_token),
        )
        assert resp.status_code == 422, f"days={bad} debió fallar validación"


# ── /top-posts ──────────────────────────────────────────────────────


async def test_top_posts_winners_returns_positive_polarity_posts(
    client: AsyncClient, db_session: AsyncSession, admin_token: str, admin_user: User
) -> None:
    """Posts con AVG(nlp_polaridad) > 0 y ≥3 classified comments aparecen como winners."""
    d = await _seed_dirigente(db_session)
    p = await _seed_profile(db_session, d)
    post = await _seed_post(
        db_session,
        p,
        published_at=datetime.now(UTC) - timedelta(days=5),
        content="Inauguramos nueva escuela en Oaxaca",
        likes=120,
        url="https://facebook.com/saymi.oax/posts/123",
    )
    # 4 comments positivos, polaridad +1 y +2
    for i in range(4):
        await _seed_comment(
            db_session,
            post,
            nlp_polaridad=1 + (i % 2),
            content=f"Excelente trabajo Sec. #{i}",
            author_hash=f"hash_pos_{i}",
        )

    resp = await client.get(
        f"{BASE}/top-posts?dirigente_id={d.id}&kind=winners&limit=3&days=30",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 1
    item = body[0]
    assert item["post_id"] == post.id
    assert item["avg_polaridad"] is not None and item["avg_polaridad"] > 0
    assert item["n_classified_comments"] == 4
    assert item["likes"] == 120
    assert item["post_url"] == "https://facebook.com/saymi.oax/posts/123"
    # sample_quotes: positivos (polaridad >= 1)
    assert len(item["sample_quotes"]) > 0
    for q in item["sample_quotes"]:
        assert q["polaridad"] >= 1


async def test_top_posts_losers_returns_negative_polarity_posts(
    client: AsyncClient, db_session: AsyncSession, admin_token: str, admin_user: User
) -> None:
    """Posts con AVG(nlp_polaridad) < 0 aparecen como losers; quotes con polaridad <= -1."""
    d = await _seed_dirigente(db_session)
    p = await _seed_profile(db_session, d)
    post = await _seed_post(
        db_session,
        p,
        published_at=datetime.now(UTC) - timedelta(days=5),
        content="Anuncio política controversial",
        likes=200,
    )
    for i in range(3):
        await _seed_comment(
            db_session,
            post,
            nlp_polaridad=-2 if i % 2 == 0 else -1,
            content=f"No estoy de acuerdo #{i}",
            author_hash=f"hash_neg_{i}",
        )

    resp = await client.get(
        f"{BASE}/top-posts?dirigente_id={d.id}&kind=losers&limit=3&days=30",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 1
    item = body[0]
    assert item["avg_polaridad"] is not None and item["avg_polaridad"] < 0
    for q in item["sample_quotes"]:
        assert q["polaridad"] <= -1


async def test_top_posts_excludes_posts_with_less_than_3_classified(
    client: AsyncClient, db_session: AsyncSession, admin_token: str, admin_user: User
) -> None:
    """Posts con < 3 comments clasificados no aparecen (HAVING ≥ 3)."""
    d = await _seed_dirigente(db_session)
    p = await _seed_profile(db_session, d)
    post = await _seed_post(
        db_session, p, published_at=datetime.now(UTC) - timedelta(days=5), likes=10
    )
    # solo 2 classified comments
    await _seed_comment(db_session, post, nlp_polaridad=2, author_hash="x1")
    await _seed_comment(db_session, post, nlp_polaridad=1, author_hash="x2")
    # 5 sin clasificar
    for i in range(5):
        await _seed_comment(db_session, post, nlp_polaridad=None, author_hash=f"u{i}")

    resp = await client.get(
        f"{BASE}/top-posts?dirigente_id={d.id}&kind=winners&limit=3&days=30",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json() == []


async def test_top_posts_empty_when_no_data(
    client: AsyncClient, db_session: AsyncSession, admin_token: str, admin_user: User
) -> None:
    d = await _seed_dirigente(db_session)
    resp = await client.get(
        f"{BASE}/top-posts?dirigente_id={d.id}&kind=winners",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json() == []


async def test_top_posts_404_on_missing_dirigente(
    client: AsyncClient, admin_token: str, admin_user: User
) -> None:
    resp = await client.get(
        f"{BASE}/top-posts?dirigente_id=99999&kind=winners",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 404


async def test_top_posts_validates_kind_enum(
    client: AsyncClient, db_session: AsyncSession, admin_token: str, admin_user: User
) -> None:
    d = await _seed_dirigente(db_session)
    resp = await client.get(
        f"{BASE}/top-posts?dirigente_id={d.id}&kind=invalid",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422


# ── /interactions-summary ────────────────────────────────────────────


async def test_interactions_summary_empty_dirigente(
    client: AsyncClient, db_session: AsyncSession, admin_token: str, admin_user: User
) -> None:
    d = await _seed_dirigente(db_session)
    resp = await client.get(
        f"{BASE}/interactions-summary?dirigente_id={d.id}&days=44",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["dirigente_id"] == d.id
    assert body["window_days"] == 44
    assert body["total_reactions"] == 0
    assert body["total_comments"] == 0
    assert body["comments_classified"] == 0
    assert body["comments_classified_pct"] == 0.0
    assert body["posts_in_window"] == 0
    assert body["by_reaction_type"] == {}
    # sin reactions, queda como placeholder_like_only (non_like=0 → True por regla del endpoint)
    assert body["reaction_type_quality"] == "placeholder_like_only"


async def test_interactions_summary_counts_aggregates(
    client: AsyncClient, db_session: AsyncSession, admin_token: str, admin_user: User
) -> None:
    """Total reactions, comments, classified % y posts_in_window calculados correctamente."""
    d = await _seed_dirigente(db_session)
    p = await _seed_profile(db_session, d)
    pub = datetime.now(UTC) - timedelta(days=10)
    post = await _seed_post(db_session, p, published_at=pub, likes=42)

    w = await _seed_watched_profile(db_session, d, external_id="u1")
    await _seed_reaction(db_session, w, post, reaction_type="like")

    # 4 comments, 2 con nlp_tono poblado → 50%
    await _seed_comment(db_session, post, nlp_tono="positivo", author_hash="a1")
    await _seed_comment(db_session, post, nlp_tono="negativo", author_hash="a2")
    await _seed_comment(db_session, post, author_hash="a3")
    await _seed_comment(db_session, post, author_hash="a4")

    resp = await client.get(
        f"{BASE}/interactions-summary?dirigente_id={d.id}&days=44",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_reactions"] == 1
    assert body["total_comments"] == 4
    assert body["comments_classified"] == 2
    assert body["comments_classified_pct"] == 50.0
    assert body["posts_in_window"] == 1


async def test_interactions_summary_reaction_quality_fully_classified_when_non_like(
    client: AsyncClient, db_session: AsyncSession, admin_token: str, admin_user: User
) -> None:
    """Si existe alguna reacción != 'like', quality='fully_classified'."""
    d = await _seed_dirigente(db_session)
    p = await _seed_profile(db_session, d)
    post = await _seed_post(
        db_session, p, published_at=datetime.now(UTC) - timedelta(days=5)
    )
    w = await _seed_watched_profile(db_session, d, external_id="u1")
    await _seed_reaction(db_session, w, post, reaction_type="love")

    resp = await client.get(
        f"{BASE}/interactions-summary?dirigente_id={d.id}",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["reaction_type_quality"] == "fully_classified"
    assert body["by_reaction_type"]["love"] == 1


async def test_interactions_summary_reaction_quality_placeholder_when_only_likes(
    client: AsyncClient, db_session: AsyncSession, admin_token: str, admin_user: User
) -> None:
    """Solo 'like' → placeholder_like_only (estado Hugo RADAR pre-Sprint 9)."""
    d = await _seed_dirigente(db_session)
    p = await _seed_profile(db_session, d)
    post = await _seed_post(
        db_session, p, published_at=datetime.now(UTC) - timedelta(days=5)
    )
    w1 = await _seed_watched_profile(db_session, d, external_id="u1")
    w2 = await _seed_watched_profile(db_session, d, external_id="u2")
    await _seed_reaction(db_session, w1, post, reaction_type="like")
    await _seed_reaction(db_session, w2, post, reaction_type="like")

    resp = await client.get(
        f"{BASE}/interactions-summary?dirigente_id={d.id}",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["reaction_type_quality"] == "placeholder_like_only"
    assert body["by_reaction_type"] == {"like": 2}


async def test_interactions_summary_404_on_missing_dirigente(
    client: AsyncClient, admin_token: str, admin_user: User
) -> None:
    resp = await client.get(
        f"{BASE}/interactions-summary?dirigente_id=99999",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 404


async def test_interactions_summary_403_for_viewer_other_org(
    client: AsyncClient,
    db_session: AsyncSession,
    viewer_token: str,
    viewer_user: User,
) -> None:
    org = await _seed_organizacion(db_session, slug="org-403-isummary")
    d = await _seed_dirigente(db_session, org_id=org.id)
    resp = await client.get(
        f"{BASE}/interactions-summary?dirigente_id={d.id}",
        headers=auth_headers(viewer_token),
    )
    assert resp.status_code == 403


# ── /top-fans ────────────────────────────────────────────────────────


async def test_top_fans_calculates_correct_score_and_orders_properly(
    client: AsyncClient, db_session: AsyncSession, admin_token: str, admin_user: User
) -> None:
    """Verifica que el endpoint /top-fans calcule correctamente el score (likes*1 + comments*2.5) y ordene de forma decreciente."""
    d = await _seed_dirigente(db_session)
    p = await _seed_profile(db_session, d)
    
    # 3 posts diferentes para no violar el unique constraint uq_watched_like_post_type
    post1 = await _seed_post(db_session, p, published_at=datetime.now(UTC) - timedelta(days=5), platform_post_id="post_1")
    post2 = await _seed_post(db_session, p, published_at=datetime.now(UTC) - timedelta(days=5), platform_post_id="post_2")
    post3 = await _seed_post(db_session, p, published_at=datetime.now(UTC) - timedelta(days=5), platform_post_id="post_3")

    # Perfil 1: 3 likes, 0 comments -> score = 3.0
    w1 = await _seed_watched_profile(db_session, d, external_id="fan_like_only")
    await _seed_reaction(db_session, w1, post1)
    await _seed_reaction(db_session, w1, post2)
    await _seed_reaction(db_session, w1, post3)

    # Perfil 2: 1 like, 2 comments -> score = 1*1.0 + 2*2.5 = 6.0
    w2 = await _seed_watched_profile(db_session, d, external_id="fan_mixed")
    await _seed_reaction(db_session, w2, post1)
    await _seed_comment(db_session, post1, author_hash=w2.author_hash)
    await _seed_comment(db_session, post2, author_hash=w2.author_hash)

    resp = await client.get(
        f"{BASE}/top-fans?dirigente_id={d.id}&limit=5",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 2

    # El score más alto (6.0) debe estar primero
    assert body[0]["profile_external_id"] == "fan_mixed"
    assert body[0]["n_likes"] == 1
    assert body[0]["n_comments"] == 2
    assert body[0]["score"] == 6.0

    # El score más bajo (3.0) debe estar segundo
    assert body[1]["profile_external_id"] == "fan_like_only"
    assert body[1]["n_likes"] == 3
    assert body[1]["n_comments"] == 0
    assert body[1]["score"] == 3.0


async def test_top_fans_filters_by_platform_and_source(
    client: AsyncClient, db_session: AsyncSession, admin_token: str, admin_user: User
) -> None:
    """Verifica que los filtros de plataforma y origen funcionen correctamente."""
    d = await _seed_dirigente(db_session)

    # w1 es de tipo cliente_seed y FACEBOOK
    w1 = await _seed_watched_profile(db_session, d, external_id="seed_fb", source="cliente_seed")
    # w2 es de tipo auto_suggested (cambiado manual post-seed)
    w2 = await _seed_watched_profile(db_session, d, external_id="auto_fb", source="auto_suggested")

    # w3 es de INSTAGRAM
    w3 = WatchedProfile(
        dirigente_observador_id=d.id,
        org_id=d.org_id,
        platform="INSTAGRAM",
        profile_external_id="auto_ig",
        profile_handle="auto_ig",
        source="auto_suggested",
        tags=[],
        author_hash=compute_watched_hash("INSTAGRAM", "auto_ig"),
    )
    db_session.add(w3)
    await db_session.commit()

    # Filtro por plataforma: INSTAGRAM
    resp = await client.get(
        f"{BASE}/top-fans?dirigente_id={d.id}&platform=INSTAGRAM",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["profile_external_id"] == "auto_ig"

    # Filtro por source: cliente_seed
    resp2 = await client.get(
        f"{BASE}/top-fans?dirigente_id={d.id}&source=cliente_seed",
        headers=auth_headers(admin_token),
    )
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert len(body2) == 1
    assert body2[0]["profile_external_id"] == "seed_fb"


async def test_top_fans_rbac_and_errors(
    client: AsyncClient, db_session: AsyncSession, admin_token: str, viewer_token: str
) -> None:
    """Prueba controles de acceso y respuestas de error para /top-fans."""
    # 404 dirigente inexistente
    resp = await client.get(
        f"{BASE}/top-fans?dirigente_id=99999",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 404

    # 403 viewer sin acceso a la organización del dirigente
    org = await _seed_organizacion(db_session, slug="org-rbac-top-fans")
    d = await _seed_dirigente(db_session, org_id=org.id)
    resp2 = await client.get(
        f"{BASE}/top-fans?dirigente_id={d.id}",
        headers=auth_headers(viewer_token),
    )
    assert resp2.status_code == 403

