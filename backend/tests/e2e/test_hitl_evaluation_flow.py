"""E2E tests Sprint S9 · Flujo HITL completo end-to-end.

Cubre:
- Happy path completo: sample → patch → confirm → progress → audit
- Escalación de privilegios (VIEWER cross-dirigente → 403)
- Confirmación implícita vs edit explícita (from==to vs from!=to)
- off_topic flag independiente de nlp_tono
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import Role, create_access_token, hash_password
from app.models.dirigente import Dirigente
from app.models.hitl_audit import HitlEditsLog
from app.models.social import Platform, PostType, SocialPost, SocialProfile
from app.models.user import User
from tests.conftest import auth_headers

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
async def two_dirigentes(db_session: AsyncSession) -> dict:
    """Crear dirigente_a (Solano-like) y dirigente_b para probar cross-access."""
    dir_a = Dirigente(full_name="Rafael Solano", cargo="Regidor", partido="MC", estado="CDMX")
    dir_b = Dirigente(full_name="Otro Dirigente", cargo="Diputado", partido="MC", estado="JAL")
    db_session.add_all([dir_a, dir_b])
    await db_session.flush()

    profile_a = SocialProfile(
        dirigente_id=dir_a.id,
        platform=Platform.TWITTER,
        handle="@rafael_solano",
        followers_count=500,
        posts_count=2,
    )
    db_session.add(profile_a)
    await db_session.flush()

    # 2 posts para dir_a
    post_a1 = SocialPost(
        profile_id=profile_a.id,
        platform_post_id="e2e_post_1",
        content="Post E2E 1 Solano",
        post_type=PostType.TEXT,
        published_at=datetime.now(UTC) - timedelta(days=1),
        likes=5,
        comments=4,
        shares=0,
        views=50,
        target_politico="gobierno",
    )
    post_a2 = SocialPost(
        profile_id=profile_a.id,
        platform_post_id="e2e_post_2",
        content="Post E2E 2 Solano",
        post_type=PostType.TEXT,
        published_at=datetime.now(UTC) - timedelta(hours=2),
        likes=2,
        comments=1,
        shares=0,
        views=20,
        target_politico="oposicion",
    )
    db_session.add_all([post_a1, post_a2])
    await db_session.flush()

    # Profile and post for dir_b
    profile_b = SocialProfile(
        dirigente_id=dir_b.id,
        platform=Platform.INSTAGRAM,
        handle="@otro_dirigente",
        followers_count=300,
        posts_count=1,
    )
    db_session.add(profile_b)
    await db_session.flush()

    post_b = SocialPost(
        profile_id=profile_b.id,
        platform_post_id="e2e_post_b",
        content="Post Dirigente B",
        post_type=PostType.TEXT,
        published_at=datetime.now(UTC) - timedelta(hours=5),
        likes=1,
        comments=1,
        shares=0,
        views=10,
        target_politico="ciudadania",
    )
    db_session.add(post_b)
    await db_session.flush()

    # 4 comments para post_a1 (todos unreviewed, tono=ataque)
    comment_ids_a1 = []
    for i in range(4):
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
                "pid": post_a1.id,
                "cid": f"e2e_c_a1_{i}",
                "content": f"Comentario A1 {i}",
                "hash": f"hash_a1_{i}_" + "0" * 50,
                "tono": "ataque",
                "target": "gobierno",
                "pub": datetime.now(UTC) - timedelta(hours=i),
            },
        )

    # 1 comment para post_b (dir_b)
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
            "pid": post_b.id,
            "cid": "e2e_c_b_0",
            "content": "Comentario B dirigente ajeno",
            "hash": "hash_b_0_" + "0" * 55,
            "tono": "informativo",
            "target": "ciudadania",
            "pub": datetime.now(UTC) - timedelta(hours=1),
        },
    )
    await db_session.commit()

    # Fetch comment ids for dir_a
    rows_a = (
        await db_session.execute(
            text(
                "SELECT id FROM social_comments WHERE parent_post_id = :pid ORDER BY id"
            ),
            {"pid": post_a1.id},
        )
    ).fetchall()
    comment_ids_a1 = [r[0] for r in rows_a]

    row_b = (
        await db_session.execute(
            text(
                "SELECT id FROM social_comments WHERE platform_comment_id = 'e2e_c_b_0'"
            ),
        )
    ).first()
    comment_id_b = row_b[0]

    return {
        "dir_a_id": dir_a.id,
        "dir_b_id": dir_b.id,
        "profile_a_id": profile_a.id,
        "post_a1_id": post_a1.id,
        "post_a2_id": post_a2.id,
        "post_b_id": post_b.id,
        "comment_ids_a1": comment_ids_a1,
        "comment_id_b": comment_id_b,
    }


@pytest.fixture
async def viewer_a(db_session: AsyncSession, two_dirigentes: dict) -> User:
    """VIEWER atado a dirigente_a."""
    user = User(
        email="e2e_viewer_a@crece.mx",
        hashed_password=hash_password("pass"),
        full_name="Viewer A E2E",
        role=Role.VIEWER,
        dirigente_id=two_dirigentes["dir_a_id"],
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def viewer_b(db_session: AsyncSession, two_dirigentes: dict) -> User:
    """VIEWER atado a dirigente_b."""
    user = User(
        email="e2e_viewer_b@crece.mx",
        hashed_password=hash_password("pass"),
        full_name="Viewer B E2E",
        role=Role.VIEWER,
        dirigente_id=two_dirigentes["dir_b_id"],
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def token_viewer_a(viewer_a: User) -> str:
    return create_access_token(
        data={"sub": str(viewer_a.id), "role": viewer_a.role.value}
    )


@pytest.fixture
def token_viewer_b(viewer_b: User) -> str:
    return create_access_token(
        data={"sub": str(viewer_b.id), "role": viewer_b.role.value}
    )


# ──────────────────────────────────────────────────────────────────────────────
# Test 1 · Happy path E2E completo
# ──────────────────────────────────────────────────────────────────────────────


async def test_e2e_happy_path_full_flow(
    client: AsyncClient,
    db_session: AsyncSession,
    two_dirigentes: dict,
    token_viewer_a: str,
    admin_token: str,
) -> None:
    """Flujo completo: sample → patch → confirm → progress → audit."""
    did = two_dirigentes["dir_a_id"]
    cids = two_dirigentes["comment_ids_a1"]
    headers_v = auth_headers(token_viewer_a)
    headers_a = auth_headers(admin_token)

    # 1. GET sample — viewer puede ver su propio dirigente
    r = await client.get(
        f"/api/v1/hitl/sample?dirigente_id={did}&n_comments=50&n_posts=10",
        headers=headers_v,
    )
    assert r.status_code == 200, r.text
    body = r.json()

    assert "posts" in body and "comments" in body
    assert "progress" in body and "system_proposal_summary" in body
    assert body["progress"]["pending_total"] > 0

    comments = body["comments"]
    assert len(comments) >= 4

    for c in comments:
        assert "id" in c
        assert "content" in c
        assert "nlp_tono" in c
        assert "nlp_target" in c
        assert "review_status" in c
        assert c["review_status"] == "unreviewed"

    # 2. PATCH first comment: change tono ataque → critico
    cid_edit = cids[0]
    with patch(
        "app.api.v1.endpoints.hitl_evaluation.recompute_score_comment",
        new=AsyncMock(return_value=55),
    ):
        r2 = await client.patch(
            f"/api/v1/hitl/comments/{cid_edit}",
            json={"tono": "critico", "reason": "es critica no ataque"},
            headers=headers_v,
        )
    assert r2.status_code == 200, r2.text
    assert r2.json()["review_status"] == "edited"
    assert r2.json()["new_score"] == 55

    # Verify DB: nlp_tono changed, review_status=edited
    row_c = (
        await db_session.execute(
            text("SELECT nlp_tono, review_status FROM social_comments WHERE id = :cid"),
            {"cid": cid_edit},
        )
    ).first()
    assert row_c[0] == "critico"
    assert row_c[1] == "edited"

    # Verify audit row: from_tono=ataque, to_tono=critica
    audit_rows = (
        await db_session.execute(
            text(
                "SELECT from_tono, to_tono, actor_id FROM hitl_edits_log WHERE entity_id = :eid AND entity_type = 'comment'"
            ),
            {"eid": cid_edit},
        )
    ).fetchall()
    assert len(audit_rows) == 1
    assert audit_rows[0][0] == "ataque"
    assert audit_rows[0][1] == "critico"

    # 3. POST confirm second comment
    cid_confirm = cids[1]
    r3 = await client.post(
        f"/api/v1/hitl/comments/{cid_confirm}/confirm",
        headers=headers_v,
    )
    assert r3.status_code == 200, r3.text
    assert r3.json()["review_status"] == "confirmed"

    # Verify DB: review_status=confirmed
    row_conf = (
        await db_session.execute(
            text("SELECT review_status FROM social_comments WHERE id = :cid"),
            {"cid": cid_confirm},
        )
    ).first()
    assert row_conf[0] == "confirmed"

    # Verify audit: from==to (confirm implicit)
    audit_conf = (
        await db_session.execute(
            text(
                "SELECT from_tono, to_tono FROM hitl_edits_log WHERE entity_id = :eid AND entity_type = 'comment'"
            ),
            {"eid": cid_confirm},
        )
    ).first()
    assert audit_conf[0] == audit_conf[1]  # from_tono == to_tono

    # 4. GET sample with include_reviewed=false — reviewed items must not appear
    r4 = await client.get(
        f"/api/v1/hitl/sample?dirigente_id={did}&include_reviewed=false&n_comments=50",
        headers=headers_v,
    )
    assert r4.status_code == 200, r4.text
    body4 = r4.json()
    reviewed_ids = {c["id"] for c in body4["comments"]}
    assert cid_edit not in reviewed_ids
    assert cid_confirm not in reviewed_ids
    assert body4["progress"]["reviewed_total"] == 2

    # 5. GET audit with ADMIN — sees both rows DESC
    r5 = await client.get(f"/api/v1/hitl/audit/{did}", headers=headers_a)
    assert r5.status_code == 200, r5.text
    body5 = r5.json()
    assert body5["count"] == 2
    times = [row["edited_at"] for row in body5["rows"]]
    assert times == sorted(times, reverse=True)


# ──────────────────────────────────────────────────────────────────────────────
# Test 2 · Escalación de privilegios
# ──────────────────────────────────────────────────────────────────────────────


async def test_privilege_escalation_viewer_cross_dirigente(
    client: AsyncClient,
    two_dirigentes: dict,
    token_viewer_a: str,
    token_viewer_b: str,
    admin_token: str,
) -> None:
    """VIEWER A no puede operar sobre datos de VIEWER B, y viceversa."""
    did_a = two_dirigentes["dir_a_id"]
    did_b = two_dirigentes["dir_b_id"]
    cid_b = two_dirigentes["comment_id_b"]

    # VIEWER_A intenta PATCH comment de dirigente B → 403
    r1 = await client.patch(
        f"/api/v1/hitl/comments/{cid_b}",
        json={"tono": "informativo"},
        headers=auth_headers(token_viewer_a),
    )
    assert r1.status_code == 403, r1.text

    # VIEWER_A intenta GET audit de dirigente B → 403
    r2 = await client.get(
        f"/api/v1/hitl/audit/{did_b}",
        headers=auth_headers(token_viewer_a),
    )
    assert r2.status_code == 403, r2.text

    # VIEWER_B intenta GET sample de dirigente A → 403
    r3 = await client.get(
        f"/api/v1/hitl/sample?dirigente_id={did_a}",
        headers=auth_headers(token_viewer_b),
    )
    assert r3.status_code == 403, r3.text

    # ADMIN puede PATCH y GET cualquier dirigente
    with patch(
        "app.api.v1.endpoints.hitl_evaluation.recompute_score_comment",
        new=AsyncMock(return_value=0),
    ):
        r4 = await client.patch(
            f"/api/v1/hitl/comments/{cid_b}",
            json={"tono": "informativo", "reason": "admin reclasifica"},
            headers=auth_headers(admin_token),
        )
    assert r4.status_code == 200, r4.text

    r5 = await client.get(
        f"/api/v1/hitl/audit/{did_a}",
        headers=auth_headers(admin_token),
    )
    assert r5.status_code == 200, r5.text


# ──────────────────────────────────────────────────────────────────────────────
# Test 3 · Confirmación implícita vs edit explícita
# ──────────────────────────────────────────────────────────────────────────────


async def test_confirm_vs_edit_audit_diff(
    client: AsyncClient,
    db_session: AsyncSession,
    two_dirigentes: dict,
    token_viewer_a: str,
) -> None:
    """Confirm → from==to; Edit → from!=to cuando el tono cambia."""
    cids = two_dirigentes["comment_ids_a1"]
    headers = auth_headers(token_viewer_a)

    # Confirm → review_status=confirmed, from_tono==to_tono
    cid_conf = cids[2]
    r1 = await client.post(
        f"/api/v1/hitl/comments/{cid_conf}/confirm",
        headers=headers,
    )
    assert r1.status_code == 200, r1.text
    assert r1.json()["review_status"] == "confirmed"

    audit_conf = (
        await db_session.execute(
            text(
                "SELECT from_tono, to_tono, from_target, to_target "
                "FROM hitl_edits_log WHERE entity_id = :eid AND entity_type = 'comment'",
            ),
            {"eid": cid_conf},
        )
    ).first()
    assert audit_conf is not None
    assert audit_conf[0] == audit_conf[1]  # from_tono == to_tono
    assert audit_conf[2] == audit_conf[3]  # from_target == to_target

    # Edit → review_status=edited, from_tono != to_tono
    cid_edit = cids[3]
    with patch(
        "app.api.v1.endpoints.hitl_evaluation.recompute_score_comment",
        new=AsyncMock(return_value=10),
    ):
        r2 = await client.patch(
            f"/api/v1/hitl/comments/{cid_edit}",
            json={"tono": "propositivo", "reason": "realmente propositivo"},
            headers=headers,
        )
    assert r2.status_code == 200, r2.text
    assert r2.json()["review_status"] == "edited"

    audit_edit = (
        await db_session.execute(
            text(
                "SELECT from_tono, to_tono FROM hitl_edits_log "
                "WHERE entity_id = :eid AND entity_type = 'comment'",
            ),
            {"eid": cid_edit},
        )
    ).first()
    assert audit_edit is not None
    assert audit_edit[0] == "ataque"
    assert audit_edit[1] == "propositivo"
    assert audit_edit[0] != audit_edit[1]


# ──────────────────────────────────────────────────────────────────────────────
# Test 4 · off_topic flag independiente de nlp_tono
# ──────────────────────────────────────────────────────────────────────────────


async def test_off_topic_flag_independent_of_nlp_tono(
    client: AsyncClient,
    db_session: AsyncSession,
    two_dirigentes: dict,
    token_viewer_a: str,
) -> None:
    """off_topic=True se registra en audit_log pero NO modifica nlp_tono si no se envía."""
    cids = two_dirigentes["comment_ids_a1"]
    cid = cids[0]
    headers = auth_headers(token_viewer_a)

    # Capturar nlp_tono original antes del PATCH
    original = (
        await db_session.execute(
            text("SELECT nlp_tono FROM social_comments WHERE id = :cid"),
            {"cid": cid},
        )
    ).first()
    original_tono = original[0]

    with patch(
        "app.api.v1.endpoints.hitl_evaluation.recompute_score_comment",
        new=AsyncMock(return_value=0),
    ):
        r = await client.patch(
            f"/api/v1/hitl/comments/{cid}",
            json={"off_topic": True, "reason": "es spam"},
            headers=headers,
        )
    assert r.status_code == 200, r.text

    # nlp_tono no debe cambiar (no se envió tono en el body)
    after = (
        await db_session.execute(
            text("SELECT nlp_tono FROM social_comments WHERE id = :cid"),
            {"cid": cid},
        )
    ).first()
    assert after[0] == original_tono

    # audit_log tiene off_topic=TRUE
    audit = (
        await db_session.execute(
            text(
                "SELECT off_topic FROM hitl_edits_log "
                "WHERE entity_id = :eid AND entity_type = 'comment' "
                "ORDER BY id DESC LIMIT 1",
            ),
            {"eid": cid},
        )
    ).first()
    assert audit is not None
    assert audit[0] is True
