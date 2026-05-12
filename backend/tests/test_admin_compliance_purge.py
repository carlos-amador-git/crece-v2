"""Tests for Sprint S1 T7 — ARCO LFPDPPP purge-hash endpoint (D-18).

Cubre:
1. Happy path: 5 social_comments con hash X → purga 5 + audit row creado
2. Idempotencia: hash sin datos → 200 con counts=0 + audit registrado
3. Validación: hash inválido (30 chars) → 422 Validation Error
4. Seguridad: sin auth → 401 · rol no-admin → 403
5. Audit listing (GET /purge-audit) funciona solo para admin
"""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dirigente import Dirigente
from app.models.social import Platform, PostType, SocialPost, SocialProfile
from tests.conftest import auth_headers


# `social_comments` no está modelada en SQLAlchemy (drift intencional doc. en
# migración 402acb98d2d4 + s1m1_sprint_s1_schema). `Base.metadata.create_all()`
# del conftest NO la crea, así que la creamos aquí por SQL directo — una vez
# por sesión, respetando la truncación que hace el fixture `setup_database`.
_SOCIAL_COMMENTS_DDL = """
CREATE TABLE IF NOT EXISTS social_comments (
    id              SERIAL PRIMARY KEY,
    parent_post_id  INTEGER NOT NULL REFERENCES social_posts(id) ON DELETE CASCADE,
    platform_comment_id VARCHAR(255) NOT NULL UNIQUE,
    content         TEXT NOT NULL,
    author_hash     VARCHAR(64) NOT NULL,
    likes           INTEGER NOT NULL DEFAULT 0,
    published_at    TIMESTAMP WITH TIME ZONE,
    nlp_tono        VARCHAR(30),
    nlp_target      VARCHAR(30),
    nlp_polaridad   SMALLINT,
    nlp_model_version VARCHAR(50),
    is_reply_to_comment BOOLEAN NOT NULL DEFAULT FALSE,
    parent_comment_id INTEGER REFERENCES social_comments(id) ON DELETE SET NULL,
    es_follower     BOOLEAN,
    data_source     VARCHAR(40),
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
)
"""
_SOCIAL_COMMENTS_IDX = (
    "CREATE INDEX IF NOT EXISTS ix_social_comments_author_hash "
    "ON social_comments (author_hash)"
)


@pytest.fixture(autouse=True)
async def _ensure_social_comments_table(db_session: AsyncSession) -> None:
    """Crea `social_comments` en la DB de test si falta (drift vs. ORM).

    El fixture autouse `setup_database` del conftest trunca tablas modeladas,
    pero si `social_comments` ya existe, el TRUNCATE CASCADE la limpia
    automáticamente (porque social_posts la referencia).
    """
    await db_session.execute(text(_SOCIAL_COMMENTS_DDL))
    await db_session.execute(text(_SOCIAL_COMMENTS_IDX))
    await db_session.commit()


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_hash(commenter_id: str, salt: str = "test-salt") -> str:
    """Produce SHA-256 hex lowercase — mismo formato que producción."""
    return hashlib.sha256(f"TWITTER:{commenter_id}:{salt}".encode()).hexdigest()


async def _seed_post_and_comments(
    db: AsyncSession,
    author_hash: str,
    n_comments: int = 5,
) -> int:
    """Crea 1 dirigente + profile + post + N comments con el mismo author_hash.

    Retorna el post_id para referencia.
    """
    dirigente = Dirigente(
        full_name="Dirigente T7",
        cargo="Diputado",
        partido="MC",
        estado="CDMX",
    )
    db.add(dirigente)
    await db.flush()

    profile = SocialProfile(
        dirigente_id=dirigente.id,
        platform=Platform.TWITTER,
        handle="@dirigente_t7",
        followers_count=1000,
        posts_count=1,
    )
    db.add(profile)
    await db.flush()

    now = datetime.now(UTC)
    post = SocialPost(
        profile_id=profile.id,
        platform_post_id="tw_t7_post_1",
        content="Post de prueba para ARCO T7",
        post_type=PostType.TEXT,
        published_at=now - timedelta(days=1),
        likes=10,
        comments=n_comments,
        shares=0,
        views=100,
        engagement_rate=0.01,
        is_political=True,
    )
    db.add(post)
    await db.flush()

    # Insertar comments con el hash objetivo usando SQL directo
    # (no hay modelo SQLAlchemy para social_comments — pre-S1 drift intencional)
    for i in range(n_comments):
        await db.execute(
            text(
                "INSERT INTO social_comments "
                "(parent_post_id, platform_comment_id, content, author_hash, "
                " likes, published_at, created_at, updated_at) "
                "VALUES (:pid, :cid, :content, :ah, 0, NOW(), NOW(), NOW())"
            ),
            {
                "pid": post.id,
                "cid": f"tw_comment_t7_{i}",
                "content": f"Comentario T7 #{i}",
                "ah": author_hash,
            },
        )

    # También 2 comments con otro hash para verificar que NO se tocan
    other_hash = _make_hash("otro_usuario")
    for i in range(2):
        await db.execute(
            text(
                "INSERT INTO social_comments "
                "(parent_post_id, platform_comment_id, content, author_hash, "
                " likes, published_at, created_at, updated_at) "
                "VALUES (:pid, :cid, :content, :ah, 0, NOW(), NOW(), NOW())"
            ),
            {
                "pid": post.id,
                "cid": f"tw_comment_other_{i}",
                "content": f"Comentario de otro usuario #{i}",
                "ah": other_hash,
            },
        )

    await db.commit()
    return post.id


# ---------------------------------------------------------------------------
# 1. Happy path — 5 comments, purga completa, audit row insertada
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_purge_hash_happy_path_5_comments(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_token: str,
) -> None:
    target_hash = _make_hash("alejandro_pinha_public_id")
    await _seed_post_and_comments(db_session, target_hash, n_comments=5)

    response = await client.post(
        "/api/v1/admin/compliance/purge-hash",
        json={
            "author_hash": target_hash,
            "justificacion": "Folio ARCO-2026-0042 · solicitud cancelación titular validada INE",
        },
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["purged"]["social_comments"] == 5
    assert body["purged"]["social_posts"] == 0
    assert body["purged"]["vectors"] == 0
    assert body["author_hash"] == target_hash
    assert isinstance(body["audit_id"], int) and body["audit_id"] > 0
    assert body["timestamp"]

    # Verificar cascada: 0 comments con el hash purgado, 2 del otro hash intactos
    remaining_target = (await db_session.execute(
        text("SELECT COUNT(*) FROM social_comments WHERE author_hash = :h"),
        {"h": target_hash},
    )).scalar()
    assert remaining_target == 0

    remaining_total = (await db_session.execute(
        text("SELECT COUNT(*) FROM social_comments"),
    )).scalar()
    assert remaining_total == 2  # los del otro hash intactos

    # Verificar audit row persistida con contadores correctos
    audit_row = (await db_session.execute(
        text(
            "SELECT admin_user_id, author_hash, rows_deleted_social_comments, "
            "rows_deleted_social_posts, rows_deleted_vectors, justificacion "
            "FROM compliance_purge_audit WHERE id = :id"
        ),
        {"id": body["audit_id"]},
    )).fetchone()
    assert audit_row is not None
    assert audit_row[1] == target_hash
    assert audit_row[2] == 5
    assert audit_row[3] == 0
    assert audit_row[4] == 0
    assert "ARCO-2026-0042" in audit_row[5]


# ---------------------------------------------------------------------------
# 2. Idempotencia — hash sin datos → counts=0 + audit registrado
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_purge_hash_idempotent_no_data(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_token: str,
) -> None:
    phantom_hash = _make_hash("usuario_que_nunca_comento")

    response = await client.post(
        "/api/v1/admin/compliance/purge-hash",
        json={
            "author_hash": phantom_hash,
            "justificacion": "Folio ARCO-2026-0099 — solicitud preventiva sin data previa",
        },
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["purged"]["social_comments"] == 0
    assert body["purged"]["social_posts"] == 0
    assert body["purged"]["vectors"] == 0

    # Audit row también se crea aunque counts sean 0
    audit_count = (await db_session.execute(
        text("SELECT COUNT(*) FROM compliance_purge_audit WHERE author_hash = :h"),
        {"h": phantom_hash},
    )).scalar()
    assert audit_count == 1


# ---------------------------------------------------------------------------
# 3. Validación — hash malformado → 422
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_purge_hash_invalid_hash_short(
    client: AsyncClient,
    admin_token: str,
) -> None:
    response = await client.post(
        "/api/v1/admin/compliance/purge-hash",
        json={
            "author_hash": "a1b2c3d4e5f6" * 2,  # 24 chars, no 64
            "justificacion": "Folio ARCO-2026-0100",
        },
        headers=auth_headers(admin_token),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_purge_hash_invalid_hash_non_hex(
    client: AsyncClient,
    admin_token: str,
) -> None:
    # 64 chars pero con caracteres no-hex
    bad = "z" * 64
    response = await client.post(
        "/api/v1/admin/compliance/purge-hash",
        json={
            "author_hash": bad,
            "justificacion": "Folio ARCO-2026-0101 — debería fallar por non-hex",
        },
        headers=auth_headers(admin_token),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_purge_hash_missing_justificacion(
    client: AsyncClient,
    admin_token: str,
) -> None:
    response = await client.post(
        "/api/v1/admin/compliance/purge-hash",
        json={
            "author_hash": _make_hash("x"),
            "justificacion": "corta",  # <10 chars
        },
        headers=auth_headers(admin_token),
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# 4. Seguridad — sin auth / no-admin
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_purge_hash_without_auth_401(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/admin/compliance/purge-hash",
        json={
            "author_hash": _make_hash("u"),
            "justificacion": "Folio ARCO test sin auth",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_purge_hash_analyst_forbidden_403(
    client: AsyncClient,
    analyst_token: str,
) -> None:
    response = await client.post(
        "/api/v1/admin/compliance/purge-hash",
        json={
            "author_hash": _make_hash("u"),
            "justificacion": "Folio ARCO — analyst debería recibir 403",
        },
        headers=auth_headers(analyst_token),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_purge_hash_viewer_forbidden_403(
    client: AsyncClient,
    viewer_token: str,
) -> None:
    response = await client.post(
        "/api/v1/admin/compliance/purge-hash",
        json={
            "author_hash": _make_hash("u"),
            "justificacion": "Folio ARCO — viewer debería recibir 403",
        },
        headers=auth_headers(viewer_token),
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# 5. GET /purge-audit — listado visible solo para admin
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_purge_audit_list_admin(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_token: str,
) -> None:
    # Primero crear una entrada via endpoint
    h = _make_hash("audit_list_test")
    await client.post(
        "/api/v1/admin/compliance/purge-hash",
        json={
            "author_hash": h,
            "justificacion": "Folio ARCO-list-test — verificar listing",
        },
        headers=auth_headers(admin_token),
    )

    response = await client.get(
        "/api/v1/admin/compliance/purge-audit",
        headers=auth_headers(admin_token),
    )
    assert response.status_code == 200
    rows = response.json()
    assert isinstance(rows, list)
    assert len(rows) >= 1
    # Hash nunca se expone completo, solo prefijo
    assert rows[0]["author_hash_prefix"].endswith("…")
    assert len(rows[0]["author_hash_prefix"]) == 17  # 16 + ellipsis


@pytest.mark.asyncio
async def test_purge_audit_list_viewer_forbidden(
    client: AsyncClient,
    viewer_token: str,
) -> None:
    response = await client.get(
        "/api/v1/admin/compliance/purge-audit",
        headers=auth_headers(viewer_token),
    )
    assert response.status_code == 403
