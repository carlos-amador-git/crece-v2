"""Tests Sprint S2 · Editor HITL evaluación NLP — endpoints `/hitl/*`."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import Role, create_access_token, hash_password
from app.models.dirigente import Dirigente
from app.models.hitl_audit import HitlEditsLog
from app.models.social import (
    Platform,
    PostType,
    SocialPost,
    SocialProfile,
)
from app.models.user import User
from tests.conftest import auth_headers

# `social_comments` no está modelada en SQLAlchemy — se crea con DDL directo.
_SOCIAL_COMMENTS_DDL = """
CREATE TABLE IF NOT EXISTS social_comments (
    id                  SERIAL PRIMARY KEY,
    parent_post_id      INTEGER NOT NULL REFERENCES social_posts(id) ON DELETE CASCADE,
    platform_comment_id VARCHAR(255) NOT NULL UNIQUE,
    content             TEXT NOT NULL,
    author_hash         VARCHAR(64) NOT NULL,
    likes               INTEGER NOT NULL DEFAULT 0,
    published_at        TIMESTAMP WITH TIME ZONE,
    nlp_tono            VARCHAR(30),
    nlp_target          VARCHAR(30),
    nlp_polaridad       SMALLINT,
    nlp_model_version   VARCHAR(50),
    is_reply_to_comment BOOLEAN NOT NULL DEFAULT FALSE,
    parent_comment_id   INTEGER REFERENCES social_comments(id) ON DELETE SET NULL,
    es_follower         BOOLEAN,
    data_source         VARCHAR(40),
    last_reviewed_by    INTEGER REFERENCES users(id) ON DELETE SET NULL,
    last_reviewed_at    TIMESTAMP,
    review_status       VARCHAR(20) NOT NULL DEFAULT 'unreviewed',
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW()
)
"""


@pytest.fixture(autouse=True)
async def _ensure_social_comments_table(db_session: AsyncSession) -> None:
    await db_session.execute(text(_SOCIAL_COMMENTS_DDL))
    await db_session.commit()


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
async def seed_data(db_session: AsyncSession) -> dict:
    """Dirigente A + B, profile, post, 3 comments con NLP labels."""
    dir_a = Dirigente(full_name="Dir A", cargo="Diputado", partido="MC", estado="CDMX")
    dir_b = Dirigente(full_name="Dir B", cargo="Senador", partido="MC", estado="JAL")
    db_session.add_all([dir_a, dir_b])
    await db_session.flush()

    profile = SocialProfile(
        dirigente_id=dir_a.id,
        platform=Platform.TWITTER,
        handle="@dir_a",
        followers_count=1000,
        posts_count=1,
    )
    db_session.add(profile)
    await db_session.flush()

    post = SocialPost(
        profile_id=profile.id,
        platform_post_id="tw_hitl_post_1",
        content="Post de prueba HITL",
        post_type=PostType.TEXT,
        published_at=datetime.now(UTC) - timedelta(days=1),
        likes=10,
        comments=3,
        shares=0,
        views=100,
        target_politico="gobierno",
    )
    db_session.add(post)
    await db_session.flush()

    # Insert 3 comments via SQL (no model)
    for i in range(3):
        await db_session.execute(
            text(
                """
                INSERT INTO social_comments
                  (parent_post_id, platform_comment_id, content, author_hash,
                   nlp_tono, nlp_target, published_at)
                VALUES (:pid, :cid, :content, :hash, :tono, :target, :pub)
                """
            ),
            {
                "pid": post.id,
                "cid": f"tw_hitl_comment_{i}",
                "content": f"Comment {i}",
                "hash": f"hash_{i}_" + "0" * 56,
                "tono": "ataque",
                "target": "gobierno",
                "pub": datetime.now(UTC) - timedelta(hours=i),
            },
        )
    await db_session.commit()

    comment_ids = [
        r[0]
        for r in (
            await db_session.execute(
                text("SELECT id FROM social_comments WHERE parent_post_id = :pid ORDER BY id"),
                {"pid": post.id},
            )
        ).fetchall()
    ]

    return {
        "dir_a_id": dir_a.id,
        "dir_b_id": dir_b.id,
        "profile_id": profile.id,
        "post_id": post.id,
        "comment_ids": comment_ids,
    }


@pytest.fixture
async def viewer_user_a(db_session: AsyncSession, seed_data: dict) -> User:
    """VIEWER atado a dirigente A."""
    user = User(
        email="viewer_a@crece.mx",
        hashed_password=hash_password("v"),
        full_name="V A",
        role=Role.VIEWER,
        dirigente_id=seed_data["dir_a_id"],
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def viewer_a_token(viewer_user_a: User) -> str:
    return create_access_token(data={"sub": str(viewer_user_a.id), "role": viewer_user_a.role.value})


# ──────────────────────────────────────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────────────────────────────────────


async def test_get_sample_happy_path(
    client: AsyncClient,
    seed_data: dict,
    viewer_a_token: str,
) -> None:
    resp = await client.get(
        f"/api/v1/hitl/sample?dirigente_id={seed_data['dir_a_id']}&n_comments=10&n_posts=5",
        headers=auth_headers(viewer_a_token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "posts" in body and "comments" in body
    assert "progress" in body and "system_proposal_summary" in body
    assert len(body["comments"]) == 3
    assert len(body["posts"]) == 1
    assert body["progress"]["pending_total"] == 3


async def test_get_sample_estratificado(
    client: AsyncClient,
    seed_data: dict,
    viewer_a_token: str,
) -> None:
    resp = await client.get(
        f"/api/v1/hitl/sample?dirigente_id={seed_data['dir_a_id']}&scope=estratificado",
        headers=auth_headers(viewer_a_token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["comments"]) == 3


async def test_patch_comment_change_tono_writes_audit_and_recomputes(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_data: dict,
    viewer_a_token: str,
) -> None:
    cid = seed_data["comment_ids"][0]
    with patch(
        "app.api.v1.endpoints.hitl_evaluation.recompute_score_comment",
        new=AsyncMock(return_value=42),
    ) as mock_rec:
        resp = await client.patch(
            f"/api/v1/hitl/comments/{cid}",
            json={"tono": "informativo", "reason": "no es ataque"},
            headers=auth_headers(viewer_a_token),
        )
    assert resp.status_code == 200, resp.text
    assert resp.json()["new_score"] == 42
    mock_rec.assert_awaited_once()

    rows = (await db_session.execute(select(HitlEditsLog).where(HitlEditsLog.entity_id == cid))).scalars().all()
    assert len(rows) == 1
    assert rows[0].from_tono == "ataque"
    assert rows[0].to_tono == "informativo"
    assert rows[0].entity_type == "comment"
    assert rows[0].dirigente_id == seed_data["dir_a_id"]


async def test_confirm_comment_writes_audit_from_eq_to(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_data: dict,
    viewer_a_token: str,
) -> None:
    cid = seed_data["comment_ids"][1]
    resp = await client.post(
        f"/api/v1/hitl/comments/{cid}/confirm",
        headers=auth_headers(viewer_a_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["review_status"] == "confirmed"
    rows = (await db_session.execute(select(HitlEditsLog).where(HitlEditsLog.entity_id == cid))).scalars().all()
    assert len(rows) == 1
    assert rows[0].from_tono == rows[0].to_tono
    assert rows[0].from_target == rows[0].to_target


async def test_patch_post_happy_path(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_data: dict,
    viewer_a_token: str,
) -> None:
    pid = seed_data["post_id"]
    with patch(
        "app.api.v1.endpoints.hitl_evaluation.recompute_score_post",
        new=AsyncMock(return_value=7),
    ):
        resp = await client.patch(
            f"/api/v1/hitl/posts/{pid}",
            json={"target": "oposicion", "reason": "reclasificación"},
            headers=auth_headers(viewer_a_token),
        )
    assert resp.status_code == 200, resp.text
    assert resp.json()["new_score"] == 7
    rows = (
        await db_session.execute(
            select(HitlEditsLog).where(HitlEditsLog.entity_id == pid, HitlEditsLog.entity_type == "post")
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].from_target == "gobierno"
    assert rows[0].to_target == "oposicion"


async def test_viewer_403_on_other_dirigente(
    client: AsyncClient,
    seed_data: dict,
    viewer_a_token: str,
) -> None:
    resp = await client.get(
        f"/api/v1/hitl/sample?dirigente_id={seed_data['dir_b_id']}",
        headers=auth_headers(viewer_a_token),
    )
    assert resp.status_code == 403


async def test_no_auth_returns_401(
    client: AsyncClient,
    seed_data: dict,
) -> None:
    resp = await client.get(f"/api/v1/hitl/sample?dirigente_id={seed_data['dir_a_id']}")
    assert resp.status_code == 401


async def test_admin_can_access_any_dirigente(
    client: AsyncClient,
    seed_data: dict,
    admin_token: str,
) -> None:
    resp = await client.get(
        f"/api/v1/hitl/sample?dirigente_id={seed_data['dir_b_id']}",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200


async def test_patch_comment_404_on_missing_id(
    client: AsyncClient,
    seed_data: dict,
    admin_token: str,
) -> None:
    resp = await client.patch(
        "/api/v1/hitl/comments/999999",
        json={"tono": "informativo"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 404


async def test_patch_comment_invalid_tono_returns_422(
    client: AsyncClient,
    seed_data: dict,
    viewer_a_token: str,
) -> None:
    cid = seed_data["comment_ids"][0]
    resp = await client.patch(
        f"/api/v1/hitl/comments/{cid}",
        json={"tono": "este_tono_no_existe"},
        headers=auth_headers(viewer_a_token),
    )
    assert resp.status_code == 422


async def test_get_audit_returns_rows_desc(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_data: dict,
    viewer_a_token: str,
) -> None:
    # Generate 2 audit rows
    cid0 = seed_data["comment_ids"][0]
    cid1 = seed_data["comment_ids"][1]
    with patch(
        "app.api.v1.endpoints.hitl_evaluation.recompute_score_comment",
        new=AsyncMock(return_value=0),
    ):
        await client.patch(
            f"/api/v1/hitl/comments/{cid0}",
            json={"tono": "informativo"},
            headers=auth_headers(viewer_a_token),
        )
        await client.post(
            f"/api/v1/hitl/comments/{cid1}/confirm",
            headers=auth_headers(viewer_a_token),
        )

    resp = await client.get(
        f"/api/v1/hitl/audit/{seed_data['dir_a_id']}",
        headers=auth_headers(viewer_a_token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["count"] == 2
    # DESC by edited_at
    times = [r["edited_at"] for r in body["rows"]]
    assert times == sorted(times, reverse=True)
