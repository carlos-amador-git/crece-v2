"""Tests for dirigentes CRUD, diagnostico (IPD), and social-summary endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dirigente import Dirigente
from app.models.organizacion import Organizacion, TipoOrganizacion
from app.models.social import (
    Platform,
    PostType,
    SentimentLabel,
    SocialPost,
    SocialProfile,
)
from app.models.user import User
from tests.conftest import auth_headers

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_org(db: AsyncSession, org_id: int | None = None) -> Organizacion:
    """Crea una organización de prueba (FK requerida por dirigentes.org_id)."""
    suffix = org_id if org_id is not None else "auto"
    org = Organizacion(
        nombre=f"Org Test {suffix}",
        slug=f"org-test-{suffix}",
        tipo=TipoOrganizacion.PARTIDO,
    )
    if org_id is not None:
        org.id = org_id
    db.add(org)
    await db.flush()
    await db.refresh(org)
    return org


async def _create_dirigente(db: AsyncSession, **overrides) -> Dirigente:
    defaults = {
        "full_name": "Alejandro Pina",
        "cargo": "Diputado Local",
        "partido": "MC",
        "estado": "CDMX",
        "municipio": "Benito Juarez",
    }
    defaults.update(overrides)
    d = Dirigente(**defaults)
    db.add(d)
    await db.flush()
    await db.refresh(d)
    return d


async def _create_profile_with_posts(
    db: AsyncSession,
    dirigente_id: int,
    platform: Platform = Platform.TWITTER,
    followers: int = 3000,
    posts_count: int = 30,
    engagement_rate: float = 0.02,
) -> SocialProfile:
    profile = SocialProfile(
        dirigente_id=dirigente_id,
        platform=platform,
        handle=f"@test_{platform.value}",
        followers_count=followers,
        posts_count=posts_count,
    )
    db.add(profile)
    await db.flush()
    await db.refresh(profile)

    now = datetime.now(UTC)
    for i in range(posts_count):
        post = SocialPost(
            profile_id=profile.id,
            platform_post_id=f"{platform.value}_post_{dirigente_id}_{i}",
            content=f"Test post {i} on {platform.value}",
            post_type=PostType.TEXT,
            published_at=now - timedelta(days=i),
            likes=100,
            comments=10,
            shares=5,
            views=1000,
            engagement_rate=engagement_rate,
            sentiment_score=0.5,
            sentiment_label=SentimentLabel.POSITIVE,
            is_political=True,
        )
        db.add(post)

    await db.flush()
    return profile


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


async def test_list_dirigentes(
    client: AsyncClient, db_session: AsyncSession, admin_token: str, admin_user: User
) -> None:
    """GET /dirigentes returns paginated results."""
    await _create_dirigente(db_session, full_name="Persona A", estado="CDMX")
    await _create_dirigente(db_session, full_name="Persona B", estado="Jalisco")
    await db_session.commit()

    resp = await client.get(
        "/api/v1/dirigentes/",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2


async def test_list_dirigentes_filter_estado(
    client: AsyncClient, db_session: AsyncSession, admin_token: str, admin_user: User
) -> None:
    """Filtering by estado narrows results."""
    await _create_dirigente(db_session, full_name="A", estado="CDMX")
    await _create_dirigente(db_session, full_name="B", estado="Jalisco")
    await db_session.commit()

    resp = await client.get(
        "/api/v1/dirigentes/?estado=CDMX",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["estado"] == "CDMX"


async def test_list_dirigentes_search(
    client: AsyncClient, db_session: AsyncSession, admin_token: str, admin_user: User
) -> None:
    """Search by name substring works via ilike."""
    await _create_dirigente(db_session, full_name="Alejandro Pina", estado="CDMX")
    await _create_dirigente(db_session, full_name="Rafael Solano", estado="CDMX")
    await db_session.commit()

    resp = await client.get(
        "/api/v1/dirigentes/?search=Alejandro",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


async def test_create_dirigente(
    client: AsyncClient, db_session: AsyncSession, admin_token: str, admin_user: User
) -> None:
    """Admin can create a dirigente."""
    await _create_org(db_session, org_id=3)  # default org (D16) para el FK
    await db_session.commit()
    resp = await client.post(
        "/api/v1/dirigentes/",
        json={
            "full_name": "Maria Lopez",
            "cargo": "Alcaldesa",
            "partido": "MC",
            "estado": "Nuevo Leon",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["full_name"] == "Maria Lopez"
    assert body["id"] is not None


async def test_create_dirigente_org_id_explicit(
    client: AsyncClient, db_session: AsyncSession, admin_token: str, admin_user: User
) -> None:
    """BUG-CRECE-1: org_id explícito en el payload se persiste."""
    org = await _create_org(db_session)
    await db_session.commit()
    resp = await client.post(
        "/api/v1/dirigentes/",
        json={
            "full_name": "Hanna de Lamadrid",
            "cargo": "Politico",
            "partido": "MORENA",
            "estado": "CDMX",
            "org_id": org.id,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 201
    d = await db_session.get(Dirigente, resp.json()["id"])
    assert d is not None
    assert d.org_id == org.id


async def test_create_dirigente_org_id_never_null(
    client: AsyncClient, db_session: AsyncSession, admin_token: str, admin_user: User
) -> None:
    """BUG-CRECE-1: sin org_id en payload ni en el creador, cae al default 3 (D16)."""
    await _create_org(db_session, org_id=3)
    await db_session.commit()
    resp = await client.post(
        "/api/v1/dirigentes/",
        json={
            "full_name": "Sin Org",
            "cargo": "Test",
            "estado": "CDMX",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 201
    d = await db_session.get(Dirigente, resp.json()["id"])
    assert d is not None
    assert d.org_id == 3


async def test_update_dirigente_org_id_reassign(
    client: AsyncClient, db_session: AsyncSession, admin_token: str, admin_user: User
) -> None:
    """BUG-CRECE-1: PATCH puede reasignar org (reparar huérfanos org_id=NULL)."""
    org = await _create_org(db_session)
    d = await _create_dirigente(db_session, org_id=None)
    await db_session.commit()

    resp = await client.patch(
        f"/api/v1/dirigentes/{d.id}",
        json={"org_id": org.id},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    await db_session.refresh(d)
    assert d.org_id == org.id


async def test_create_dirigente_analyst_cross_org_forbidden(
    client: AsyncClient, db_session: AsyncSession, analyst_token: str, analyst_user: User
) -> None:
    """BUG-CRECE-1 hardening: analyst NO puede crear en una org ajena (403)."""
    org = await _create_org(db_session)
    await db_session.commit()
    resp = await client.post(
        "/api/v1/dirigentes/",
        json={
            "full_name": "Cross Org Intento",
            "cargo": "Test",
            "estado": "CDMX",
            "org_id": org.id,
        },
        headers=auth_headers(analyst_token),
    )
    assert resp.status_code == 403


async def test_create_dirigente_analyst_defaults_org(
    client: AsyncClient, db_session: AsyncSession, analyst_token: str, analyst_user: User
) -> None:
    """BUG-CRECE-1 hardening: analyst sin org_id en payload cae al default, no NULL."""
    await _create_org(db_session, org_id=3)
    await db_session.commit()
    resp = await client.post(
        "/api/v1/dirigentes/",
        json={
            "full_name": "Analyst Default Org",
            "cargo": "Test",
            "estado": "CDMX",
        },
        headers=auth_headers(analyst_token),
    )
    assert resp.status_code == 201
    d = await db_session.get(Dirigente, resp.json()["id"])
    assert d is not None
    assert d.org_id == 3


async def test_update_dirigente_org_id_analyst_forbidden(
    client: AsyncClient, db_session: AsyncSession, analyst_token: str, analyst_user: User
) -> None:
    """BUG-CRECE-1 hardening: analyst NO puede reasignar org vía PATCH (403)."""
    org = await _create_org(db_session)
    d = await _create_dirigente(db_session, org_id=None)
    await db_session.commit()
    resp = await client.patch(
        f"/api/v1/dirigentes/{d.id}",
        json={"org_id": org.id},
        headers=auth_headers(analyst_token),
    )
    assert resp.status_code == 403
    await db_session.refresh(d)
    assert d.org_id is None


async def test_create_dirigente_viewer_forbidden(
    client: AsyncClient, viewer_token: str, viewer_user: User
) -> None:
    """Viewers cannot create dirigentes."""
    resp = await client.post(
        "/api/v1/dirigentes/",
        json={
            "full_name": "Not Allowed",
            "cargo": "Test",
            "estado": "CDMX",
        },
        headers=auth_headers(viewer_token),
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Get single
# ---------------------------------------------------------------------------


async def test_get_dirigente(
    client: AsyncClient, db_session: AsyncSession, admin_token: str, admin_user: User
) -> None:
    d = await _create_dirigente(db_session)
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/dirigentes/{d.id}",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["full_name"] == d.full_name


async def test_get_dirigente_not_found(
    client: AsyncClient, admin_token: str, admin_user: User
) -> None:
    resp = await client.get(
        "/api/v1/dirigentes/99999",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


async def test_update_dirigente(
    client: AsyncClient, db_session: AsyncSession, admin_token: str, admin_user: User
) -> None:
    d = await _create_dirigente(db_session)
    await db_session.commit()

    resp = await client.patch(
        f"/api/v1/dirigentes/{d.id}",
        json={"cargo": "Senador"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["cargo"] == "Senador"


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


async def test_delete_dirigente(
    client: AsyncClient, db_session: AsyncSession, admin_token: str, admin_user: User
) -> None:
    d = await _create_dirigente(db_session)
    await db_session.commit()

    resp = await client.delete(
        f"/api/v1/dirigentes/{d.id}",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 204

    # Confirm it is gone
    resp2 = await client.get(
        f"/api/v1/dirigentes/{d.id}",
        headers=auth_headers(admin_token),
    )
    assert resp2.status_code == 404


async def test_delete_dirigente_viewer_forbidden(
    client: AsyncClient,
    db_session: AsyncSession,
    viewer_token: str,
    viewer_user: User,
) -> None:
    """Only admins can delete -- analyst is also excluded."""
    d = await _create_dirigente(db_session)
    await db_session.commit()

    resp = await client.delete(
        f"/api/v1/dirigentes/{d.id}",
        headers=auth_headers(viewer_token),
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Diagnostico (IPD)
# ---------------------------------------------------------------------------


async def test_get_diagnostico(
    client: AsyncClient, db_session: AsyncSession, admin_token: str, admin_user: User
) -> None:
    """IPD is computed from social profiles and posts."""
    d = await _create_dirigente(db_session)
    await _create_profile_with_posts(
        db_session, d.id, Platform.TWITTER, followers=5000, posts_count=15
    )
    await _create_profile_with_posts(
        db_session, d.id, Platform.FACEBOOK, followers=10000, posts_count=20
    )
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/dirigentes/{d.id}/diagnostico",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["dirigente_id"] == d.id
    assert 0.0 <= body["ipd_score"] <= 10.0
    assert "twitter" in body["platform_scores"]
    assert "facebook" in body["platform_scores"]
    assert body["total_followers"] == 15000
    assert isinstance(body["recommendations"], list)


async def test_get_diagnostico_no_profiles(
    client: AsyncClient, db_session: AsyncSession, admin_token: str, admin_user: User
) -> None:
    """A dirigente with no social profiles gets IPD 0."""
    d = await _create_dirigente(db_session)
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/dirigentes/{d.id}/diagnostico",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ipd_score"] == 0.0
    assert body["total_followers"] == 0
    assert len(body["recommendations"]) > 0


# ---------------------------------------------------------------------------
# Social summary
# ---------------------------------------------------------------------------


async def test_get_social_summary(
    client: AsyncClient, db_session: AsyncSession, admin_token: str, admin_user: User
) -> None:
    """Social summary aggregates across all profiles."""
    d = await _create_dirigente(db_session)
    await _create_profile_with_posts(
        db_session, d.id, Platform.TWITTER, followers=3000, posts_count=10
    )
    await _create_profile_with_posts(
        db_session, d.id, Platform.INSTAGRAM, followers=2000, posts_count=5
    )
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/dirigentes/{d.id}/social-summary",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["dirigente_id"] == d.id
    assert body["total_followers"] == 5000
    assert body["total_posts"] == 15
    assert body["avg_engagement"] >= 0
    assert isinstance(body["top_platforms"], list)
    assert len(body["top_platforms"]) == 2


async def test_get_social_summary_not_found(
    client: AsyncClient, admin_token: str, admin_user: User
) -> None:
    resp = await client.get(
        "/api/v1/dirigentes/99999/social-summary",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 404
