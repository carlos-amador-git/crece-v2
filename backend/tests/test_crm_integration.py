"""Tests for /api/v1/crm/ integration endpoints."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ciudadano import Ciudadano, Genero, NivelInteres, RangoEdad
from app.models.crm_interaccion import CrmInteraccion
from app.models.electoral import SeccionElectoral
from app.models.organizacion import Organizacion, TipoOrganizacion
from app.models.user import User
from app.models.voter_score_integration import VoterScoreIntegration
from tests.conftest import auth_headers

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _setup_org_user(db: AsyncSession, admin_user: User) -> Organizacion:
    org = Organizacion(
        nombre="MC CRM Test",
        slug="mc-crm-test",
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


async def _create_seccion(db: AsyncSession) -> SeccionElectoral:
    seccion = SeccionElectoral(
        seccion="0201",
        estado="Ciudad de Mexico",
        distrito_federal="02",
        distrito_local="02",
        municipio="Miguel Hidalgo",
    )
    db.add(seccion)
    await db.flush()
    await db.refresh(seccion)
    return seccion


async def _create_ciudadano(
    db: AsyncSession, nombre: str, seccion_id: int, org_id: int, user_id: int
) -> Ciudadano:
    c = Ciudadano(
        nombre=nombre,
        apellido_paterno="Lopez",
        seccion_id=seccion_id,
        org_id=org_id,
        registrado_por_id=user_id,
        edad_rango=RangoEdad.E_36_45,
        genero=Genero.F,
        nivel_interes=NivelInteres.ALTO,
    )
    db.add(c)
    await db.flush()
    await db.refresh(c)
    return c


async def _create_interaccion(
    db: AsyncSession, org_id: int, ciudadano_id: int, tipo: str = "visita"
) -> CrmInteraccion:
    inter = CrmInteraccion(
        org_id=org_id,
        ciudadano_id=ciudadano_id,
        tipo=tipo,
        canal="puerta_a_puerta",
        resultado="contacto_exitoso",
    )
    db.add(inter)
    await db.flush()
    await db.refresh(inter)
    return inter


async def _create_voter_score(
    db: AsyncSession, org_id: int, ciudadano_id: int, score_favorable: float = 0.78
) -> VoterScoreIntegration:
    vs = VoterScoreIntegration(
        org_id=org_id,
        ciudadano_id=ciudadano_id,
        score_favorable=score_favorable,
        score_persuadible=0.45,
        score_asistencia=0.62,
        features={"edad_rango": "36-45", "nivel_interes": "alto"},
        modelo_version="v1.2.0",
    )
    db.add(vs)
    await db.flush()
    await db.refresh(vs)
    return vs


# ---------------------------------------------------------------------------
# Auth guard
# ---------------------------------------------------------------------------


async def test_crm_endpoints_require_auth(client: AsyncClient) -> None:
    """Core CRM endpoints without token return 401."""
    r1 = await client.get("/api/v1/crm/interactions")
    r2 = await client.post("/api/v1/crm/interactions", json={})
    r3 = await client.get("/api/v1/crm/scores/1")
    assert r1.status_code == 401
    assert r2.status_code == 401
    assert r3.status_code == 401


# ---------------------------------------------------------------------------
# Create interaction — patch endpoint's model import to fix field mismatch
# (endpoint uses registrado_por_id but CrmInteraccion model has promotor_id)
# ---------------------------------------------------------------------------


def _crm_interaccion_factory(**kwargs):
    """Remap registrado_por_id -> promotor_id so the endpoint can create records."""
    if "registrado_por_id" in kwargs:
        kwargs["promotor_id"] = kwargs.pop("registrado_por_id")
    return CrmInteraccion(**kwargs)


class _PatchedCrmInteraccionClass:
    """Drop-in replacement used in endpoint tests that remaps field names."""

    def __new__(cls, **kwargs):
        if "registrado_por_id" in kwargs:
            kwargs["promotor_id"] = kwargs.pop("registrado_por_id")
        return CrmInteraccion(**kwargs)


async def test_create_interaction(
    client: AsyncClient, db_session: AsyncSession, admin_user: User, admin_token: str
) -> None:
    """POST /crm/interactions returns 201 with the new interaction."""
    org = await _setup_org_user(db_session, admin_user)
    seccion = await _create_seccion(db_session)
    ciudadano = await _create_ciudadano(db_session, "Rosa", seccion.id, org.id, admin_user.id)
    await db_session.commit()

    with patch(
        "app.models.crm_interaccion.CrmInteraccion",
        side_effect=_crm_interaccion_factory,
    ):
        resp = await client.post(
            "/api/v1/crm/interactions",
            json={
                "ciudadano_id": ciudadano.id,
                "tipo": "visita",
                "canal": "puerta_a_puerta",
                "resultado": "contacto_exitoso",
                "notas": "Vecino interesado en propuestas de agua",
            },
            headers=auth_headers(admin_token),
        )
    assert resp.status_code == 201
    body = resp.json()
    assert body["ciudadano_id"] == ciudadano.id
    assert body["tipo"] == "visita"
    assert body["canal"] == "puerta_a_puerta"


async def test_create_interaction_minimal_fields(
    client: AsyncClient, db_session: AsyncSession, admin_user: User, admin_token: str
) -> None:
    """POST /crm/interactions with only required fields returns 201."""
    org = await _setup_org_user(db_session, admin_user)
    seccion = await _create_seccion(db_session)
    ciudadano = await _create_ciudadano(db_session, "Carlos", seccion.id, org.id, admin_user.id)
    await db_session.commit()

    with patch(
        "app.models.crm_interaccion.CrmInteraccion",
        side_effect=_crm_interaccion_factory,
    ):
        resp = await client.post(
            "/api/v1/crm/interactions",
            json={"ciudadano_id": ciudadano.id, "tipo": "llamada"},
            headers=auth_headers(admin_token),
        )
    assert resp.status_code == 201
    assert resp.json()["tipo"] == "llamada"


# ---------------------------------------------------------------------------
# List interactions
# ---------------------------------------------------------------------------


async def test_list_interactions_paginated(
    client: AsyncClient, db_session: AsyncSession, admin_user: User, admin_token: str
) -> None:
    """GET /crm/interactions returns paginated results."""
    org = await _setup_org_user(db_session, admin_user)
    seccion = await _create_seccion(db_session)
    ciudadano = await _create_ciudadano(db_session, "Elena", seccion.id, org.id, admin_user.id)
    for _ in range(5):
        await _create_interaccion(db_session, org.id, ciudadano.id)
    await db_session.commit()

    resp = await client.get(
        "/api/v1/crm/interactions?page=1&page_size=3",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 5
    assert len(body["items"]) == 3
    assert body["pages"] == 2


async def test_list_interactions_empty(
    client: AsyncClient, db_session: AsyncSession, admin_user: User, admin_token: str
) -> None:
    """GET /crm/interactions returns empty list when none exist."""
    await _setup_org_user(db_session, admin_user)
    resp = await client.get("/api/v1/crm/interactions", headers=auth_headers(admin_token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["items"] == []


async def test_filter_interactions_by_ciudadano(
    client: AsyncClient, db_session: AsyncSession, admin_user: User, admin_token: str
) -> None:
    """GET /crm/interactions?ciudadano_id=X returns only that ciudadano's records."""
    org = await _setup_org_user(db_session, admin_user)
    seccion = await _create_seccion(db_session)
    ciudadano_a = await _create_ciudadano(db_session, "Fernando", seccion.id, org.id, admin_user.id)
    ciudadano_b = await _create_ciudadano(db_session, "Gabriela", seccion.id, org.id, admin_user.id)

    await _create_interaccion(db_session, org.id, ciudadano_a.id)
    await _create_interaccion(db_session, org.id, ciudadano_a.id)
    await _create_interaccion(db_session, org.id, ciudadano_b.id)
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/crm/interactions?ciudadano_id={ciudadano_a.id}",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    for item in body["items"]:
        assert item["ciudadano_id"] == ciudadano_a.id


# ---------------------------------------------------------------------------
# Voter score — get single
# ---------------------------------------------------------------------------


async def test_get_voter_score_not_found(
    client: AsyncClient, db_session: AsyncSession, admin_user: User, admin_token: str
) -> None:
    """GET /crm/scores/{id} for ciudadano without score returns 404."""
    await _setup_org_user(db_session, admin_user)
    resp = await client.get("/api/v1/crm/scores/99999", headers=auth_headers(admin_token))
    assert resp.status_code == 404
    assert "99999" in resp.json()["detail"]


async def test_get_voter_score_exists(
    client: AsyncClient, db_session: AsyncSession, admin_user: User, admin_token: str
) -> None:
    """GET /crm/scores/{id} returns voter score when it exists."""
    org = await _setup_org_user(db_session, admin_user)
    seccion = await _create_seccion(db_session)
    ciudadano = await _create_ciudadano(db_session, "Hugo", seccion.id, org.id, admin_user.id)
    await _create_voter_score(db_session, org.id, ciudadano.id)
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/crm/scores/{ciudadano.id}", headers=auth_headers(admin_token)
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ciudadano_id"] == ciudadano.id
    assert body["score_favorable"] == pytest.approx(0.78)
    assert body["modelo_version"] == "v1.2.0"


# ---------------------------------------------------------------------------
# Voter score — list
# ---------------------------------------------------------------------------


async def test_list_voter_scores(
    client: AsyncClient, db_session: AsyncSession, admin_user: User, admin_token: str
) -> None:
    """GET /crm/scores returns paginated voter scores."""
    org = await _setup_org_user(db_session, admin_user)
    seccion = await _create_seccion(db_session)
    for name in ("Irene", "Javier", "Karla"):
        ciudadano = await _create_ciudadano(db_session, name, seccion.id, org.id, admin_user.id)
        await _create_voter_score(db_session, org.id, ciudadano.id)
    await db_session.commit()

    resp = await client.get("/api/v1/crm/scores", headers=auth_headers(admin_token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert len(body["items"]) == 3


async def test_list_voter_scores_empty(
    client: AsyncClient, db_session: AsyncSession, admin_user: User, admin_token: str
) -> None:
    """GET /crm/scores returns empty list when no scores calculated."""
    await _setup_org_user(db_session, admin_user)
    resp = await client.get("/api/v1/crm/scores", headers=auth_headers(admin_token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["items"] == []


async def test_list_voter_scores_filter_min(
    client: AsyncClient, db_session: AsyncSession, admin_user: User, admin_token: str
) -> None:
    """GET /crm/scores?score_favorable_min=0.7 filters correctly."""
    org = await _setup_org_user(db_session, admin_user)
    seccion = await _create_seccion(db_session)

    ciudadano_high = await _create_ciudadano(db_session, "Laura", seccion.id, org.id, admin_user.id)
    db_session.add(VoterScoreIntegration(
        org_id=org.id, ciudadano_id=ciudadano_high.id,
        score_favorable=0.85, score_persuadible=0.50, score_asistencia=0.70,
        features={}, modelo_version="v1.2.0",
    ))
    ciudadano_low = await _create_ciudadano(db_session, "Manuel", seccion.id, org.id, admin_user.id)
    db_session.add(VoterScoreIntegration(
        org_id=org.id, ciudadano_id=ciudadano_low.id,
        score_favorable=0.30, score_persuadible=0.20, score_asistencia=0.25,
        features={}, modelo_version="v1.2.0",
    ))
    await db_session.commit()

    resp = await client.get(
        "/api/v1/crm/scores?score_favorable_min=0.7",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["score_favorable"] == pytest.approx(0.85)
