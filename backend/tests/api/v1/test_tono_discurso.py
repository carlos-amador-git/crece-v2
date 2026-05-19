"""Tests para endpoints tono_discurso (matriz polaridad v2 · #1 plan deuda 2026-05-19).

Cubre 2 endpoints introducidos hoy:
- GET /api/v1/social/tono-discurso-timeline
- GET /api/v1/social/tono-discurso-coverage

Patrón seguido de tests/api/v1/test_watched_profiles_dashboard.py · seeding
real contra schema, sin mocks ni datos sintéticos arbitrarios.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dirigente import Dirigente
from app.models.organizacion import Organizacion, TipoOrganizacion
from app.models.social import Platform, PostType, SocialPost, SocialProfile
from app.models.user import User
from tests.conftest import auth_headers

BASE_TIMELINE = "/api/v1/social/tono-discurso-timeline"
BASE_COVERAGE = "/api/v1/social/tono-discurso-coverage"


async def _seed_org(db: AsyncSession, slug: str = "org-tono") -> Organizacion:
    org = Organizacion(
        nombre=f"Org {slug}",
        slug=slug,
        tipo=TipoOrganizacion.PARTIDO,
        activa=True,
    )
    db.add(org)
    await db.flush()
    return org


async def _seed_dirigente(db: AsyncSession, org_id: int, full_name: str = "D Tono") -> Dirigente:
    d = Dirigente(
        full_name=full_name,
        cargo="Test",
        partido="MORENA",
        estado="Oaxaca",
        org_id=org_id,
    )
    db.add(d)
    await db.flush()
    return d


async def _seed_profile(
    db: AsyncSession, dirigente_id: int, platform: Platform = Platform.FACEBOOK
) -> SocialProfile:
    p = SocialProfile(
        dirigente_id=dirigente_id,
        platform=platform,
        handle="tono.test",
        profile_url="https://example.com",
        followers_count=1000,
        active=True,
    )
    db.add(p)
    await db.flush()
    return p


async def _seed_post(
    db: AsyncSession,
    profile_id: int,
    *,
    published_at: datetime,
    content: str = "Contenido válido de prueba con suficiente longitud para superar filtros NLP.",
    tono: str | None = "neutral",
) -> SocialPost:
    post = SocialPost(
        profile_id=profile_id,
        platform_post_id=f"test_{published_at.timestamp()}",
        post_type=PostType.TEXT,
        content=content,
        published_at=published_at,
        likes=10,
        comments=2,
        shares=0,
        views=100,
        engagement_rate=0.12,
        is_political=True,
        tono_discurso=tono,
        scraped_at=datetime.now(UTC),
    )
    db.add(post)
    await db.flush()
    return post


@pytest.mark.asyncio
async def test_tono_timeline_empty_when_no_posts(
    client: AsyncClient, db_session: AsyncSession, admin_user: User
):
    """Sin posts en BD → timeline retorna array vacío."""
    org = await _seed_org(db_session, "empty-tono")
    dirigente = await _seed_dirigente(db_session, org.id, "Empty Tono")
    await db_session.commit()

    resp = await client.get(
        BASE_TIMELINE,
        params={"dirigente_id": dirigente.id},
        headers=auth_headers(admin_user),
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_tono_timeline_groups_by_day_and_tono(
    client: AsyncClient, db_session: AsyncSession, admin_user: User
):
    """Posts con distintos tonos → timeline agrega por día y tono."""
    org = await _seed_org(db_session, "groupby-tono")
    dirigente = await _seed_dirigente(db_session, org.id, "Group By Tono")
    profile = await _seed_profile(db_session, dirigente.id)

    pub = datetime.now(UTC) - timedelta(days=5)
    await _seed_post(db_session, profile.id, published_at=pub, tono="neutral")
    await _seed_post(db_session, profile.id, published_at=pub, tono="neutral")
    await _seed_post(db_session, profile.id, published_at=pub, tono="positivo")
    await db_session.commit()

    resp = await client.get(
        BASE_TIMELINE,
        params={"dirigente_id": dirigente.id},
        headers=auth_headers(admin_user),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    point = data[0]
    assert point["post_count"] == 3
    assert point["tonos"]["neutral"] == 2
    assert point["tonos"]["positivo"] == 1


@pytest.mark.asyncio
async def test_tono_timeline_excludes_null_tono(
    client: AsyncClient, db_session: AsyncSession, admin_user: User
):
    """Posts con tono_discurso NULL no aparecen en timeline (igual a sentiment legacy)."""
    org = await _seed_org(db_session, "null-tono")
    dirigente = await _seed_dirigente(db_session, org.id, "Null Tono")
    profile = await _seed_profile(db_session, dirigente.id)

    pub = datetime.now(UTC) - timedelta(days=3)
    await _seed_post(db_session, profile.id, published_at=pub, tono="neutral")
    await _seed_post(db_session, profile.id, published_at=pub, tono=None)
    await db_session.commit()

    resp = await client.get(
        BASE_TIMELINE,
        params={"dirigente_id": dirigente.id},
        headers=auth_headers(admin_user),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["post_count"] == 1
    assert data[0]["tonos"] == {"neutral": 1}


@pytest.mark.asyncio
async def test_tono_timeline_excludes_short_content(
    client: AsyncClient, db_session: AsyncSession, admin_user: User
):
    """Posts con content < 20 chars filtrados (quality filter consistente con sentiment)."""
    org = await _seed_org(db_session, "short-tono")
    dirigente = await _seed_dirigente(db_session, org.id, "Short Tono")
    profile = await _seed_profile(db_session, dirigente.id)

    pub = datetime.now(UTC) - timedelta(days=1)
    await _seed_post(db_session, profile.id, published_at=pub, content="corto", tono="neutral")
    await db_session.commit()

    resp = await client.get(
        BASE_TIMELINE,
        params={"dirigente_id": dirigente.id},
        headers=auth_headers(admin_user),
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_tono_timeline_excludes_retweets_by_default(
    client: AsyncClient, db_session: AsyncSession, admin_user: User
):
    """RTs excluidos por default · pueden incluirse con include_rts=true."""
    org = await _seed_org(db_session, "rt-tono")
    dirigente = await _seed_dirigente(db_session, org.id, "RT Tono")
    profile = await _seed_profile(db_session, dirigente.id, platform=Platform.TWITTER)

    pub = datetime.now(UTC) - timedelta(days=2)
    await _seed_post(
        db_session,
        profile.id,
        published_at=pub,
        content="RT @ejemplo: Original tweet content with sufficient length para filtros.",
        tono="positivo",
    )
    await db_session.commit()

    resp_default = await client.get(
        BASE_TIMELINE,
        params={"dirigente_id": dirigente.id},
        headers=auth_headers(admin_user),
    )
    assert resp_default.json() == []

    resp_with_rts = await client.get(
        BASE_TIMELINE,
        params={"dirigente_id": dirigente.id, "include_rts": "true"},
        headers=auth_headers(admin_user),
    )
    data = resp_with_rts.json()
    assert len(data) == 1


@pytest.mark.asyncio
async def test_tono_coverage_calculates_distribution(
    client: AsyncClient, db_session: AsyncSession, admin_user: User
):
    """Coverage retorna total, classified, passed_filters y distribución."""
    org = await _seed_org(db_session, "cov-tono")
    dirigente = await _seed_dirigente(db_session, org.id, "Cov Tono")
    profile = await _seed_profile(db_session, dirigente.id)

    pub = datetime.now(UTC) - timedelta(days=5)
    # 3 clasificados, 1 sin tono
    await _seed_post(db_session, profile.id, published_at=pub, tono="positivo")
    await _seed_post(db_session, profile.id, published_at=pub, tono="positivo")
    await _seed_post(db_session, profile.id, published_at=pub, tono="neutral")
    await _seed_post(db_session, profile.id, published_at=pub, tono=None)
    await db_session.commit()

    resp = await client.get(
        BASE_COVERAGE,
        params={"dirigente_id": dirigente.id, "days": 30},
        headers=auth_headers(admin_user),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_posts"] == 4
    assert data["classified"] == 3
    assert data["passed_filters"] == 3
    assert data["coverage_pct"] == 75.0
    assert data["tonos_distribution"]["positivo"] == 2
    assert data["tonos_distribution"]["neutral"] == 1


@pytest.mark.asyncio
async def test_tono_endpoints_require_auth(client: AsyncClient):
    """Sin token → 401."""
    for url in [BASE_TIMELINE, BASE_COVERAGE]:
        resp = await client.get(url, params={"dirigente_id": 1})
        assert resp.status_code == 401
