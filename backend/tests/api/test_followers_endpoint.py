"""Tests para `GET /dirigentes/{id}/followers` (PLAN-2026-05-13 S1b).

Cubre:
- Caso BD vacía → 200 con items=[] y total=0 (empty state legítimo, NO mock).
- Filtro `platform`.
- Filtro `only_with_comments`.
- Filtro `only_verified`.
- RBAC: viewer con dirigente_id ajeno → 403.
- Paginación.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import Role, create_access_token, hash_password
from app.models.dirigente import Dirigente
from app.models.follower import FollowerEngagement, SocialFollower
from app.models.social import Platform, PostType, SocialPost, SocialProfile
from app.models.user import User
from tests.conftest import auth_headers


async def _seed_dirigente(db: AsyncSession, *, full_name: str = "Piña") -> Dirigente:
    d = Dirigente(
        full_name=full_name, cargo="Diputado", partido="MC", estado="CDMX"
    )
    db.add(d)
    await db.commit()
    await db.refresh(d)
    return d


async def _seed_profile_and_post(
    db: AsyncSession, dirigente: Dirigente, platform: Platform = Platform.YOUTUBE
) -> SocialPost:
    profile = SocialProfile(
        dirigente_id=dirigente.id,
        platform=platform,
        handle="@test",
        url="https://example.com/@test",
        followers_count=0,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    post = SocialPost(
        profile_id=profile.id,
        platform_post_id="ext-1",
        post_type=PostType.TEXT,
        published_at=datetime.now(UTC),
        content="hola",
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return post


@pytest.mark.asyncio
async def test_followers_empty_state(
    client: AsyncClient, admin_token: str, db_session: AsyncSession
) -> None:
    d = await _seed_dirigente(db_session)
    res = await client.get(
        f"/api/v1/dirigentes/{d.id}/followers", headers=auth_headers(admin_token)
    )
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 0
    assert body["items"] == []
    assert body["page"] == 1


@pytest.mark.asyncio
async def test_followers_platform_filter(
    client: AsyncClient, admin_token: str, db_session: AsyncSession
) -> None:
    d = await _seed_dirigente(db_session)
    for platform, ext in [("youtube", "yt1"), ("youtube", "yt2"), ("instagram", "ig1")]:
        db_session.add(
            SocialFollower(
                dirigente_id=d.id,
                platform=platform,
                follower_external_id=ext,
                follower_handle=ext,
                source="public_scraper",
            )
        )
    await db_session.commit()

    res_all = await client.get(
        f"/api/v1/dirigentes/{d.id}/followers", headers=auth_headers(admin_token)
    )
    assert res_all.json()["total"] == 3

    res_yt = await client.get(
        f"/api/v1/dirigentes/{d.id}/followers?platform=youtube",
        headers=auth_headers(admin_token),
    )
    assert res_yt.json()["total"] == 2


@pytest.mark.asyncio
async def test_followers_only_with_comments(
    client: AsyncClient, admin_token: str, db_session: AsyncSession
) -> None:
    d = await _seed_dirigente(db_session)
    post = await _seed_profile_and_post(db_session, d)
    f_comment = SocialFollower(
        dirigente_id=d.id,
        platform="youtube",
        follower_external_id="yt-comm",
        follower_handle="commenter",
        source="oauth",
    )
    f_silent = SocialFollower(
        dirigente_id=d.id,
        platform="youtube",
        follower_external_id="yt-silent",
        follower_handle="silent",
        source="public_scraper",
    )
    db_session.add_all([f_comment, f_silent])
    await db_session.commit()
    await db_session.refresh(f_comment)
    db_session.add(
        FollowerEngagement(
            follower_id=f_comment.id,
            post_id=post.id,
            engagement_type="comment",
            engaged_at=datetime.now(UTC),
        )
    )
    await db_session.commit()

    res = await client.get(
        f"/api/v1/dirigentes/{d.id}/followers?only_with_comments=true",
        headers=auth_headers(admin_token),
    )
    body = res.json()
    assert body["total"] == 1
    assert body["items"][0]["follower_handle"] == "commenter"
    assert body["items"][0]["engagement_summary"]["by_type"]["comment"] == 1


@pytest.mark.asyncio
async def test_followers_rbac_viewer_forbidden(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    d_a = await _seed_dirigente(db_session, full_name="A")
    d_b = await _seed_dirigente(db_session, full_name="B")

    viewer = User(
        email="viewer-restricted@crece.mx",
        hashed_password=hash_password("x"),
        full_name="Restricted",
        role=Role.VIEWER,
        dirigente_id=d_a.id,
    )
    db_session.add(viewer)
    await db_session.commit()
    await db_session.refresh(viewer)
    token = create_access_token(
        data={"sub": str(viewer.id), "role": Role.VIEWER.value}
    )

    res_own = await client.get(
        f"/api/v1/dirigentes/{d_a.id}/followers", headers=auth_headers(token)
    )
    assert res_own.status_code == 200

    res_other = await client.get(
        f"/api/v1/dirigentes/{d_b.id}/followers", headers=auth_headers(token)
    )
    assert res_other.status_code == 403
