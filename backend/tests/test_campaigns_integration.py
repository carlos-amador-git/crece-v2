"""Tests for /api/v1/campaigns/ integration endpoints."""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import patch
from uuid import UUID as UUIDType

import pytest
from httpx import AsyncClient
from pydantic import field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign_integration import Campaign
from app.models.ciudadano import Ciudadano, IntencionVotoCiudadano, RangoEdad, Genero, NivelInteres
from app.models.electoral import SeccionElectoral
from app.models.organizacion import Organizacion, TipoOrganizacion
from app.models.user import User
from app.schemas.integration import CampaignResponse
from tests.conftest import auth_headers


# ---------------------------------------------------------------------------
# Schema patch helper
# ---------------------------------------------------------------------------
# CampaignResponse.id is typed as str, but Campaign.id is a UUID.
# Pydantic v2 does not auto-coerce UUID→str on model_validate.


class _UUIDFriendlyCampaignResponse(CampaignResponse):
    """CampaignResponse that accepts UUID values for the id field."""

    @field_validator("id", mode="before")
    @classmethod
    def coerce_uuid_to_str(cls, v: Any) -> str:
        return str(v) if isinstance(v, UUIDType) else v


def _patch_campaign_response():
    """Context manager that patches CampaignResponse in the endpoint module."""
    return patch(
        "app.api.v1.endpoints.campaigns_integration.CampaignResponse",
        _UUIDFriendlyCampaignResponse,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_org(db: AsyncSession) -> Organizacion:
    org = Organizacion(
        nombre="MC CDMX Test",
        slug="mc-cdmx-test",
        tipo=TipoOrganizacion.PARTIDO,
        estado="Ciudad de Mexico",
        is_active=True,
    )
    db.add(org)
    await db.flush()
    await db.refresh(org)
    return org


async def _create_seccion(db: AsyncSession) -> SeccionElectoral:
    seccion = SeccionElectoral(
        seccion="0101",
        estado="Ciudad de Mexico",
        distrito_federal="01",
        distrito_local="01",
        municipio="Cuauhtemoc",
    )
    db.add(seccion)
    await db.flush()
    await db.refresh(seccion)
    return seccion


async def _create_ciudadano(
    db: AsyncSession,
    nombre: str,
    seccion_id: int,
    org_id: int,
    user_id: int,
    telefono: str | None = "5512345678",
    intencion: IntencionVotoCiudadano | None = IntencionVotoCiudadano.MC,
) -> Ciudadano:
    c = Ciudadano(
        nombre=nombre,
        apellido_paterno="Garcia",
        seccion_id=seccion_id,
        org_id=org_id,
        registrado_por_id=user_id,
        edad_rango=RangoEdad.E_26_35,
        genero=Genero.M,
        nivel_interes=NivelInteres.MEDIO,
        telefono=telefono,
        intencion_voto=intencion,
    )
    db.add(c)
    await db.flush()
    await db.refresh(c)
    return c


async def _setup_org_user(db: AsyncSession, admin_user: User) -> Organizacion:
    """Create org and attach it to admin_user, committing so the endpoint sees the org_id."""
    org = await _create_org(db)
    admin_user.org_id = org.id
    await db.commit()
    await db.refresh(admin_user)
    return org


# ---------------------------------------------------------------------------
# Auth guard
# ---------------------------------------------------------------------------


async def test_campaigns_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/campaigns/")
    assert resp.status_code == 401


async def test_create_campaign_requires_auth(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/campaigns/", json={"nombre": "X", "tipo": "whatsapp"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Create campaign
# ---------------------------------------------------------------------------


async def test_create_campaign(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user: User,
    admin_token: str,
) -> None:
    """POST /campaigns/ creates a campaign and returns 201."""
    await _setup_org_user(db_session, admin_user)

    payload = {
        "nombre": "Campaña Lunes",
        "tipo": "whatsapp",
        "segmentacion": {"secciones": ["0101"]},
        "tipo_nudge": "informativo",
    }
    resp = await client.post(
        "/api/v1/campaigns/", json=payload, headers=auth_headers(admin_token)
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["nombre"] == "Campaña Lunes"
    assert body["tipo"] == "whatsapp"
    assert body["estado"] == "borrador"
    assert body["total_destinatarios"] == 0
    uuid.UUID(body["id"])  # Must be a valid UUID string


# ---------------------------------------------------------------------------
# List campaigns
# ---------------------------------------------------------------------------


async def test_list_campaigns_empty(
    client: AsyncClient, db_session: AsyncSession, admin_user: User, admin_token: str
) -> None:
    """GET /campaigns/ returns empty list when no campaigns exist."""
    await _setup_org_user(db_session, admin_user)
    with _patch_campaign_response():
        resp = await client.get("/api/v1/campaigns/", headers=auth_headers(admin_token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["items"] == []


async def test_list_campaigns_returns_paginated(
    client: AsyncClient, db_session: AsyncSession, admin_user: User, admin_token: str
) -> None:
    """GET /campaigns/ returns correct pagination metadata."""
    org = await _setup_org_user(db_session, admin_user)
    for i in range(3):
        db_session.add(Campaign(
            id=uuid.uuid4(), org_id=org.id,
            nombre=f"Campaña {i}", tipo="whatsapp", creado_por_id=admin_user.id,
        ))
    await db_session.commit()

    with _patch_campaign_response():
        resp = await client.get("/api/v1/campaigns/", headers=auth_headers(admin_token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert len(body["items"]) == 3
    assert body["page"] == 1


# ---------------------------------------------------------------------------
# Get campaign by id
# ---------------------------------------------------------------------------


async def test_get_campaign_by_id(
    client: AsyncClient, db_session: AsyncSession, admin_user: User, admin_token: str
) -> None:
    """GET /campaigns/{id} returns the campaign."""
    org = await _setup_org_user(db_session, admin_user)
    campaign_id = uuid.uuid4()
    db_session.add(Campaign(
        id=campaign_id, org_id=org.id,
        nombre="Campaña Unica", tipo="whatsapp", creado_por_id=admin_user.id,
    ))
    await db_session.commit()

    with _patch_campaign_response():
        resp = await client.get(
            f"/api/v1/campaigns/{campaign_id}", headers=auth_headers(admin_token)
        )
    assert resp.status_code == 200
    assert resp.json()["nombre"] == "Campaña Unica"


async def test_get_campaign_error_cases(
    client: AsyncClient, db_session: AsyncSession, admin_user: User, admin_token: str
) -> None:
    """GET /campaigns/{id} — 404 for missing, 400 for invalid UUID."""
    await _setup_org_user(db_session, admin_user)

    with _patch_campaign_response():
        resp_404 = await client.get(
            f"/api/v1/campaigns/{uuid.uuid4()}", headers=auth_headers(admin_token)
        )
    assert resp_404.status_code == 404

    resp_400 = await client.get(
        "/api/v1/campaigns/not-a-uuid", headers=auth_headers(admin_token)
    )
    assert resp_400.status_code == 400


# ---------------------------------------------------------------------------
# Segment ciudadanos
# ---------------------------------------------------------------------------


async def test_segment_ciudadanos(
    client: AsyncClient, db_session: AsyncSession, admin_user: User, admin_token: str
) -> None:
    """POST /campaigns/segment returns ciudadanos matching criteria."""
    org = await _setup_org_user(db_session, admin_user)
    seccion = await _create_seccion(db_session)

    await _create_ciudadano(
        db_session, "Ana", seccion.id, org.id, admin_user.id,
        telefono="5511111111", intencion=IntencionVotoCiudadano.MC,
    )
    await _create_ciudadano(
        db_session, "Luis", seccion.id, org.id, admin_user.id,
        telefono="5522222222", intencion=IntencionVotoCiudadano.MORENA,
    )
    await db_session.commit()

    resp = await client.post(
        "/api/v1/campaigns/segment",
        json={"intencion_voto": ["mc"], "limit": 100},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["ciudadanos"][0]["nombre"] == "Ana"


async def test_segment_excludes_no_phone(
    client: AsyncClient, db_session: AsyncSession, admin_user: User, admin_token: str
) -> None:
    """POST /campaigns/segment never returns ciudadanos without telefono."""
    org = await _setup_org_user(db_session, admin_user)
    seccion = await _create_seccion(db_session)

    await _create_ciudadano(
        db_session, "Maria", seccion.id, org.id, admin_user.id, telefono="5533333333"
    )
    await _create_ciudadano(
        db_session, "Pedro", seccion.id, org.id, admin_user.id, telefono=None
    )
    await db_session.commit()

    resp = await client.post(
        "/api/v1/campaigns/segment",
        json={"limit": 100},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["ciudadanos"][0]["nombre"] == "Maria"
    for item in body["ciudadanos"]:
        assert item["telefono"] is not None
        assert item["telefono"] != ""
