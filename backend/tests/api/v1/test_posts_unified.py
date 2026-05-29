"""Tests · endpoint BFF /api/v1/posts/unified · C7 audit-full 2026-05-19.

Cubre 4 views (feed/top/comentarios/fans), filtros (platform/date), paginación,
y auth (401/403). Sigue patrón test_tono_discurso.py / test_watched_profiles_dashboard.py.

Sin mocks ni SQLite — usa BD test Postgres (asyncpg dialect-compatible).
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import text

from app.core.security import Role, create_access_token, hash_password
from app.models.dirigente import Dirigente
from app.models.organizacion import Organizacion, TipoOrganizacion
from app.models.social import DataSource, Platform, PostType, SocialPost, SocialProfile
from app.models.user import User
from tests.conftest import _get_test_engine, auth_headers

BASE = "/api/v1/posts/unified"


@pytest.fixture(autouse=True)
async def _ensure_social_schema_current():
    """Asegura que social_posts.tono_discurso existe (column drift fix).

    El fixture global setup_database skipea create_all cuando las tablas
    ya existen. Si el modelo agregó columnas nuevas (caso #1 tono_discurso
    2026-05-19), la BD test queda con schema obsoleto y SELECT falla con
    UndefinedColumnError. Forzamos un ALTER TABLE idempotente.
    """
    engine = _get_test_engine()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "ALTER TABLE social_posts "
                "ADD COLUMN IF NOT EXISTS tono_discurso VARCHAR(30) NULL"
            )
        )
    yield


# ============================================================================
# Helpers seeding
# ============================================================================


async def _seed_org(db: AsyncSession, slug: str = "org-unif") -> Organizacion:
    org = Organizacion(
        nombre=f"Org {slug}",
        slug=slug,
        tipo=TipoOrganizacion.PARTIDO,
        is_active=True,
    )
    db.add(org)
    await db.flush()
    return org


async def _seed_dirigente(
    db: AsyncSession, org_id: int, full_name: str = "D Unif"
) -> Dirigente:
    d = Dirigente(
        full_name=full_name,
        cargo="Test",
        partido="MC",
        estado="Oaxaca",
        org_id=org_id,
    )
    db.add(d)
    await db.flush()
    return d


async def _seed_profile(
    db: AsyncSession,
    dirigente_id: int,
    platform: Platform = Platform.FACEBOOK,
    handle: str = "test.handle",
) -> SocialProfile:
    p = SocialProfile(
        dirigente_id=dirigente_id,
        platform=platform,
        handle=handle,
        url=f"https://example.com/{handle}",
        followers_count=1000,
        data_source=DataSource.AUTOMATED_SCRAPER,
    )
    db.add(p)
    await db.flush()
    return p


async def _seed_post(
    db: AsyncSession,
    profile_id: int,
    *,
    published_at: datetime | None = None,
    content: str = "Contenido válido de prueba con suficiente longitud para superar filtros.",
    likes: int = 10,
    comments: int = 2,
    shares: int = 1,
    views: int | None = 100,
    engagement_rate: float = 0.05,
    tono: str | None = None,
) -> SocialPost:
    pub = published_at or datetime.now(UTC) - timedelta(days=1)
    post = SocialPost(
        profile_id=profile_id,
        platform_post_id=f"pu_{uuid4().hex[:16]}",
        post_type=PostType.TEXT,
        content=content,
        published_at=pub,
        likes=likes,
        comments=comments,
        shares=shares,
        views=views,
        engagement_rate=engagement_rate,
        is_political=True,
        tono_discurso=tono,
        scraped_at=datetime.now(UTC),
    )
    db.add(post)
    await db.flush()
    return post


async def _seed_org_dirigente_with_user_token(
    db: AsyncSession,
    *,
    slug: str,
    user_email: str,
    role: Role = Role.ANALYST,
) -> tuple[Organizacion, Dirigente, User, str]:
    """Setup completo · usuario asociado al org del dirigente."""
    org = await _seed_org(db, slug=slug)
    dirigente = await _seed_dirigente(db, org.id, full_name=f"D {slug}")
    user = User(
        email=user_email,
        hashed_password=hash_password("pwd"),
        full_name=f"User {slug}",
        role=role,
        org_id=org.id,
    )
    db.add(user)
    await db.flush()
    token = create_access_token(data={"sub": str(user.id), "role": user.role.value})
    return org, dirigente, user, token


# ============================================================================
# Auth
# ============================================================================


@pytest.mark.asyncio
async def test_unified_requires_auth(client: AsyncClient):
    """Sin Authorization → 401."""
    resp = await client.get(BASE, params={"dirigente_id": 1, "view": "feed"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unified_forbidden_for_other_org(
    client: AsyncClient, db_session: AsyncSession
):
    """User analyst de otra org → 403."""
    org_a, dirigente_a, _, _ = await _seed_org_dirigente_with_user_token(
        db_session, slug="org-a", user_email="usera@crece.mx"
    )
    _, _, _, token_b = await _seed_org_dirigente_with_user_token(
        db_session, slug="org-b", user_email="userb@crece.mx"
    )
    await db_session.commit()

    resp = await client.get(
        BASE,
        params={"dirigente_id": dirigente_a.id, "view": "feed"},
        headers=auth_headers(token_b),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_unified_404_dirigente_no_existe(
    client: AsyncClient, db_session: AsyncSession, admin_token: str
):
    """Dirigente inexistente → 404."""
    resp = await client.get(
        BASE,
        params={"dirigente_id": 99999, "view": "feed"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 404


# ============================================================================
# View=feed
# ============================================================================


@pytest.mark.asyncio
async def test_unified_feed_returns_posts(
    client: AsyncClient, db_session: AsyncSession, admin_token: str
):
    """View=feed devuelve posts del dirigente con shape canónico."""
    org = await _seed_org(db_session, "feed-basic")
    dirigente = await _seed_dirigente(db_session, org.id)
    profile = await _seed_profile(db_session, dirigente.id)
    pub = datetime.now(UTC) - timedelta(days=1)
    await _seed_post(db_session, profile.id, published_at=pub, likes=50)
    await _seed_post(db_session, profile.id, published_at=pub, likes=20)
    await db_session.commit()

    resp = await client.get(
        BASE,
        params={"dirigente_id": dirigente.id, "view": "feed"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["view"] == "feed"
    assert data["dirigente_id"] == dirigente.id
    assert data["total"] == 2
    assert len(data["items"]) == 2
    item = data["items"][0]
    assert "id" in item
    assert "published_at" in item
    assert "platform" in item
    assert "likes_publicos" in item
    assert "data_source" in item


@pytest.mark.asyncio
async def test_unified_feed_empty_when_no_posts(
    client: AsyncClient, db_session: AsyncSession, admin_token: str
):
    """Dirigente sin posts → total=0 items=[]."""
    org = await _seed_org(db_session, "feed-empty")
    dirigente = await _seed_dirigente(db_session, org.id, "Empty D")
    await db_session.commit()

    resp = await client.get(
        BASE,
        params={"dirigente_id": dirigente.id, "view": "feed"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


# ============================================================================
# Filtros · platform + date
# ============================================================================


@pytest.mark.asyncio
async def test_unified_filter_platform(
    client: AsyncClient, db_session: AsyncSession, admin_token: str
):
    """Filtro platform=FACEBOOK → solo posts de FB."""
    org = await _seed_org(db_session, "filt-plat")
    dirigente = await _seed_dirigente(db_session, org.id)
    fb_prof = await _seed_profile(
        db_session, dirigente.id, platform=Platform.FACEBOOK, handle="d.fb"
    )
    ig_prof = await _seed_profile(
        db_session, dirigente.id, platform=Platform.INSTAGRAM, handle="d.ig"
    )
    pub = datetime.now(UTC) - timedelta(days=1)
    await _seed_post(db_session, fb_prof.id, published_at=pub)
    await _seed_post(db_session, fb_prof.id, published_at=pub)
    await _seed_post(db_session, ig_prof.id, published_at=pub)
    await db_session.commit()

    resp = await client.get(
        BASE,
        params={"dirigente_id": dirigente.id, "view": "feed", "platform": "FACEBOOK"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert all(item["platform"] == "FACEBOOK" for item in data["items"])


@pytest.mark.asyncio
async def test_unified_filter_date_from(
    client: AsyncClient, db_session: AsyncSession, admin_token: str
):
    """Filtro date_from → solo posts ≥ fecha."""
    org = await _seed_org(db_session, "filt-df")
    dirigente = await _seed_dirigente(db_session, org.id)
    profile = await _seed_profile(db_session, dirigente.id)
    base = datetime.now(UTC)
    await _seed_post(db_session, profile.id, published_at=base - timedelta(days=10))
    await _seed_post(db_session, profile.id, published_at=base - timedelta(days=3))
    await _seed_post(db_session, profile.id, published_at=base - timedelta(days=1))
    await db_session.commit()

    cutoff = (base - timedelta(days=5)).date().isoformat()
    resp = await client.get(
        BASE,
        params={"dirigente_id": dirigente.id, "view": "feed", "date_from": cutoff},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2  # solo 3d y 1d están dentro


@pytest.mark.asyncio
async def test_unified_filter_combo_platform_and_date(
    client: AsyncClient, db_session: AsyncSession, admin_token: str
):
    """Filtros platform AND date_from se combinan correctamente."""
    org = await _seed_org(db_session, "filt-combo")
    dirigente = await _seed_dirigente(db_session, org.id)
    fb = await _seed_profile(
        db_session, dirigente.id, platform=Platform.FACEBOOK, handle="combo.fb"
    )
    ig = await _seed_profile(
        db_session, dirigente.id, platform=Platform.INSTAGRAM, handle="combo.ig"
    )
    base = datetime.now(UTC)
    # FB viejo (excluido por date_from)
    await _seed_post(db_session, fb.id, published_at=base - timedelta(days=20))
    # FB reciente (incluido)
    await _seed_post(db_session, fb.id, published_at=base - timedelta(days=2))
    # IG reciente (excluido por platform)
    await _seed_post(db_session, ig.id, published_at=base - timedelta(days=2))
    await db_session.commit()

    cutoff = (base - timedelta(days=10)).date().isoformat()
    resp = await client.get(
        BASE,
        params={
            "dirigente_id": dirigente.id,
            "view": "feed",
            "platform": "FACEBOOK",
            "date_from": cutoff,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["platform"] == "FACEBOOK"


# ============================================================================
# Paginación
# ============================================================================


@pytest.mark.asyncio
async def test_unified_pagination_per_page(
    client: AsyncClient, db_session: AsyncSession, admin_token: str
):
    """per_page=2 → 2 items por página, total y pages correctos."""
    org = await _seed_org(db_session, "page-pp")
    dirigente = await _seed_dirigente(db_session, org.id)
    profile = await _seed_profile(db_session, dirigente.id)
    base = datetime.now(UTC)
    for i in range(5):
        await _seed_post(db_session, profile.id, published_at=base - timedelta(days=i))
    await db_session.commit()

    resp = await client.get(
        BASE,
        params={
            "dirigente_id": dirigente.id,
            "view": "feed",
            "per_page": 2,
            "page": 1,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert data["per_page"] == 2
    assert data["page"] == 1
    assert data["pages"] == 3  # ceil(5/2)
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_unified_pagination_page_offset(
    client: AsyncClient, db_session: AsyncSession, admin_token: str
):
    """page=2 con per_page=2 → items 3-4 (offset correcto, sin duplicados)."""
    org = await _seed_org(db_session, "page-off")
    dirigente = await _seed_dirigente(db_session, org.id)
    profile = await _seed_profile(db_session, dirigente.id)
    base = datetime.now(UTC)
    for i in range(5):
        await _seed_post(db_session, profile.id, published_at=base - timedelta(days=i))
    await db_session.commit()

    resp_p1 = await client.get(
        BASE,
        params={"dirigente_id": dirigente.id, "view": "feed", "per_page": 2, "page": 1},
        headers=auth_headers(admin_token),
    )
    resp_p2 = await client.get(
        BASE,
        params={"dirigente_id": dirigente.id, "view": "feed", "per_page": 2, "page": 2},
        headers=auth_headers(admin_token),
    )
    ids_p1 = {item["id"] for item in resp_p1.json()["items"]}
    ids_p2 = {item["id"] for item in resp_p2.json()["items"]}
    assert ids_p1.isdisjoint(ids_p2), "page 1 y 2 no deben solaparse"


# ============================================================================
# View=top
# ============================================================================


@pytest.mark.asyncio
async def test_unified_top_orders_by_engagement(
    client: AsyncClient, db_session: AsyncSession, admin_token: str
):
    """View=top ordena posts por engagement_rate desc."""
    org = await _seed_org(db_session, "top-order")
    dirigente = await _seed_dirigente(db_session, org.id)
    profile = await _seed_profile(db_session, dirigente.id)
    pub = datetime.now(UTC) - timedelta(days=1)
    await _seed_post(db_session, profile.id, published_at=pub, engagement_rate=0.05, likes=10)
    await _seed_post(db_session, profile.id, published_at=pub, engagement_rate=0.25, likes=100)
    await _seed_post(db_session, profile.id, published_at=pub, engagement_rate=0.15, likes=50)
    await db_session.commit()

    resp = await client.get(
        BASE,
        params={"dirigente_id": dirigente.id, "view": "top"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["view"] == "top"
    assert len(data["items"]) == 3
    likes_in_order = [item["likes_publicos"] for item in data["items"]]
    # El top debe estar primero
    assert likes_in_order[0] == 100


# ============================================================================
# View=comentarios
# ============================================================================


@pytest.mark.asyncio
async def test_unified_comentarios_returns_view(
    client: AsyncClient, db_session: AsyncSession, admin_token: str
):
    """View=comentarios responde 200 con shape canónico."""
    org = await _seed_org(db_session, "coms")
    dirigente = await _seed_dirigente(db_session, org.id)
    profile = await _seed_profile(db_session, dirigente.id)
    pub = datetime.now(UTC) - timedelta(days=1)
    await _seed_post(db_session, profile.id, published_at=pub, comments=5)
    await db_session.commit()

    resp = await client.get(
        BASE,
        params={"dirigente_id": dirigente.id, "view": "comentarios"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["view"] == "comentarios"
    # Endpoint puede filtrar por umbral de comments → asegurar shape solamente
    assert "items" in data and "total" in data


# ============================================================================
# View=fans
# ============================================================================


@pytest.mark.asyncio
async def test_unified_fans_empty_when_no_radar_events(
    client: AsyncClient, db_session: AsyncSession, admin_token: str
):
    """View=fans sin watched_like_events → vacío (no debe levantar 500)."""
    org = await _seed_org(db_session, "fans-empty")
    dirigente = await _seed_dirigente(db_session, org.id)
    profile = await _seed_profile(db_session, dirigente.id)
    pub = datetime.now(UTC) - timedelta(days=1)
    await _seed_post(db_session, profile.id, published_at=pub)
    await db_session.commit()

    resp = await client.get(
        BASE,
        params={"dirigente_id": dirigente.id, "view": "fans"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["view"] == "fans"
    assert data["total"] == 0
    assert data["items"] == []
