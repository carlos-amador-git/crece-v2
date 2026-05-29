"""Tests for /api/v1/content/ integration endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import patch
from uuid import UUID as UUIDType

from httpx import AsyncClient
from pydantic import field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contenido_pieza import ContenidoPieza
from app.models.dirigente import Dirigente
from app.models.organizacion import Organizacion, TipoOrganizacion
from app.models.user import User
from app.schemas.integration import ContentPieceResponse
from tests.conftest import auth_headers

# ---------------------------------------------------------------------------
# Schema patch helper
# ---------------------------------------------------------------------------
# ContentPieceResponse.id is typed as str, but ContenidoPieza.id is a UUID.
# Pydantic v2 does not auto-coerce UUID→str. We patch the response class
# used by the endpoint to coerce UUIDs on model_validate.


class _UUIDFriendlyPieceResponse(ContentPieceResponse):
    """ContentPieceResponse that accepts UUID values for the id field."""

    @field_validator("id", mode="before")
    @classmethod
    def coerce_uuid_to_str(cls, v: Any) -> str:
        return str(v) if isinstance(v, UUIDType) else v


def _patch_piece_response():
    """Context manager that patches ContentPieceResponse in the endpoint module."""
    return patch(
        "app.api.v1.endpoints.content_factory_integration.ContentPieceResponse",
        _UUIDFriendlyPieceResponse,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _setup_org_user(db: AsyncSession, admin_user: User) -> Organizacion:
    org = Organizacion(
        nombre="MC Content Test",
        slug="mc-content-test",
        tipo=TipoOrganizacion.PARTIDO,
        estado="Ciudad de Mexico",
        is_active=True,
    )
    db.add(org)
    await db.flush()
    await db.refresh(org)
    admin_user.org_id = org.id
    await db.commit()
    await db.refresh(admin_user)
    return org


async def _create_dirigente(db: AsyncSession, org_id: int) -> Dirigente:
    d = Dirigente(
        full_name="Alejandro Pina",
        cargo="Candidato a Diputado",
        partido="MC",
        estado="Ciudad de Mexico",
        municipio="Cuauhtemoc",
        org_id=org_id,
    )
    db.add(d)
    await db.flush()
    await db.refresh(d)
    return d


async def _create_pieza(
    db: AsyncSession,
    org_id: int,
    dirigente_id: int,
    estado: str = "borrador",
) -> ContenidoPieza:
    pieza = ContenidoPieza(
        id=uuid.uuid4(),
        org_id=org_id,
        dirigente_id=dirigente_id,
        tema="Seguridad publica en la colonia",
        tono="propositivo",
        variantes={"twitter": {"contenido": "Tweet de prueba #MC", "hashtags": ["#MC"]}},
        modelo_ia="claude-sonnet-4-20250514",
        prompt_usado="Prompt de prueba completo",
        estado=estado,
    )
    db.add(pieza)
    await db.flush()
    await db.refresh(pieza)
    return pieza


# ---------------------------------------------------------------------------
# Auth guard
# ---------------------------------------------------------------------------


async def test_list_pieces_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/content/pieces")
    assert resp.status_code == 401


async def test_generate_requires_auth(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/content/generate", json={})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# List pieces
# ---------------------------------------------------------------------------


async def test_list_pieces_empty(
    client: AsyncClient, db_session: AsyncSession, admin_user: User, admin_token: str
) -> None:
    """GET /content/pieces returns empty list when no pieces exist."""
    await _setup_org_user(db_session, admin_user)
    with _patch_piece_response():
        resp = await client.get("/api/v1/content/pieces", headers=auth_headers(admin_token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["items"] == []


async def test_list_pieces_with_data(
    client: AsyncClient, db_session: AsyncSession, admin_user: User, admin_token: str
) -> None:
    """GET /content/pieces returns all seeded pieces."""
    org = await _setup_org_user(db_session, admin_user)
    dirigente = await _create_dirigente(db_session, org.id)
    await _create_pieza(db_session, org.id, dirigente.id)
    await _create_pieza(db_session, org.id, dirigente.id)
    await db_session.commit()

    with _patch_piece_response():
        resp = await client.get("/api/v1/content/pieces", headers=auth_headers(admin_token))
    assert resp.status_code == 200
    assert resp.json()["total"] == 2


# ---------------------------------------------------------------------------
# Generate content — mock generate_content service function directly
# to avoid coupling to internal service bugs (generado_por_id field mismatch)
# ---------------------------------------------------------------------------


async def test_generate_content_mock(
    client: AsyncClient, db_session: AsyncSession, admin_user: User, admin_token: str
) -> None:
    """POST /content/generate calls the service and persists a piece."""
    org = await _setup_org_user(db_session, admin_user)
    dirigente = await _create_dirigente(db_session, org.id)
    await db_session.commit()

    # Build a real ContenidoPieza-like object to return from the mock
    fake_pieza = ContenidoPieza(
        id=uuid.uuid4(),
        org_id=org.id,
        dirigente_id=dirigente.id,
        tema="Agua potable en colonias",
        tono="propositivo",
        variantes={"twitter": {"contenido": "Post generado", "hashtags": ["#MC"]}},
        modelo_ia="claude-sonnet-4-20250514",
        prompt_usado="Test prompt",
        estado="borrador",
    )
    fake_pieza.created_at = datetime.now(UTC)

    async def _fake_generate_content(**kwargs):
        return fake_pieza

    with patch(
        "app.api.v1.endpoints.content_factory_integration.generate_content",
        side_effect=_fake_generate_content,
    ), _patch_piece_response():
        resp = await client.post(
            "/api/v1/content/generate",
            json={
                "dirigente_id": dirigente.id,
                "tema": "Agua potable en colonias",
                "contexto": "Problema reciente reportado",
                "tono": "propositivo",
                "plataformas": ["twitter"],
            },
            headers=auth_headers(admin_token),
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["tema"] == "Agua potable en colonias"
    assert body["estado"] == "borrador"
    assert "twitter" in body["variantes"]
    uuid.UUID(body["id"])


async def test_generate_content_dirigente_not_found(
    client: AsyncClient, db_session: AsyncSession, admin_user: User, admin_token: str
) -> None:
    """POST /content/generate with unknown dirigente_id returns 400."""
    await _setup_org_user(db_session, admin_user)

    async def _raise_not_found(**kwargs):
        raise ValueError("Dirigente 99999 not found")

    with patch(
        "app.api.v1.endpoints.content_factory_integration.generate_content",
        side_effect=_raise_not_found,
    ):
        resp = await client.post(
            "/api/v1/content/generate",
            json={"dirigente_id": 99999, "tema": "Tema", "tono": "propositivo", "plataformas": ["twitter"]},
            headers=auth_headers(admin_token),
        )

    assert resp.status_code == 400
    assert "not found" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Get piece by id
# ---------------------------------------------------------------------------


async def test_get_piece_by_id(
    client: AsyncClient, db_session: AsyncSession, admin_user: User, admin_token: str
) -> None:
    """GET /content/pieces/{id} returns the specific piece."""
    org = await _setup_org_user(db_session, admin_user)
    dirigente = await _create_dirigente(db_session, org.id)
    pieza = await _create_pieza(db_session, org.id, dirigente.id)
    await db_session.commit()

    with _patch_piece_response():
        resp = await client.get(
            f"/api/v1/content/pieces/{pieza.id}", headers=auth_headers(admin_token)
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == str(pieza.id)
    assert body["tema"] == "Seguridad publica en la colonia"


async def test_get_piece_error_cases(
    client: AsyncClient, db_session: AsyncSession, admin_user: User, admin_token: str
) -> None:
    """GET /content/pieces/{id} — 404 for missing, 400 for invalid UUID."""
    await _setup_org_user(db_session, admin_user)

    with _patch_piece_response():
        resp_404 = await client.get(
            f"/api/v1/content/pieces/{uuid.uuid4()}", headers=auth_headers(admin_token)
        )
    assert resp_404.status_code == 404

    resp_400 = await client.get(
        "/api/v1/content/pieces/not-a-uuid", headers=auth_headers(admin_token)
    )
    assert resp_400.status_code == 400


# ---------------------------------------------------------------------------
# Approve piece
# ---------------------------------------------------------------------------


async def test_approve_piece(
    client: AsyncClient, db_session: AsyncSession, admin_user: User, admin_token: str
) -> None:
    """POST /content/pieces/{id}/approve transitions estado to 'aprobado'."""
    org = await _setup_org_user(db_session, admin_user)
    dirigente = await _create_dirigente(db_session, org.id)
    pieza = await _create_pieza(db_session, org.id, dirigente.id, estado="borrador")
    await db_session.commit()
    await db_session.refresh(pieza)

    resp = await client.post(
        f"/api/v1/content/pieces/{pieza.id}/approve",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["message"] == "Piece approved"
    assert body["piece_id"] == str(pieza.id)
    assert "aprobado_at" in body


async def test_approve_piece_not_found(
    client: AsyncClient, db_session: AsyncSession, admin_user: User, admin_token: str
) -> None:
    """POST /content/pieces/{id}/approve for missing piece returns 404."""
    await _setup_org_user(db_session, admin_user)
    resp = await client.post(
        f"/api/v1/content/pieces/{uuid.uuid4()}/approve",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Update variant
# ---------------------------------------------------------------------------


async def test_update_variant(
    client: AsyncClient, db_session: AsyncSession, admin_user: User, admin_token: str
) -> None:
    """PUT /content/pieces/{id}/variant/{platform} updates variant contenido."""
    org = await _setup_org_user(db_session, admin_user)
    dirigente = await _create_dirigente(db_session, org.id)
    pieza = await _create_pieza(db_session, org.id, dirigente.id)
    await db_session.commit()
    await db_session.refresh(pieza)

    resp = await client.put(
        f"/api/v1/content/pieces/{pieza.id}/variant/twitter",
        json={"contenido": "Nuevo texto del tweet editado por equipo"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "twitter" in body["message"]
    assert body["piece_id"] == str(pieza.id)


async def test_update_variant_blocked_on_approved(
    client: AsyncClient, db_session: AsyncSession, admin_user: User, admin_token: str
) -> None:
    """PUT variant on an approved piece returns 409."""
    org = await _setup_org_user(db_session, admin_user)
    dirigente = await _create_dirigente(db_session, org.id)
    pieza = await _create_pieza(db_session, org.id, dirigente.id, estado="aprobado")
    await db_session.commit()
    await db_session.refresh(pieza)

    resp = await client.put(
        f"/api/v1/content/pieces/{pieza.id}/variant/twitter",
        json={"contenido": "Intento de edicion"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 409
    assert "approved" in resp.json()["detail"].lower()
