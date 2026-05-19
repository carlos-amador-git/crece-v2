"""Tests path-scoped onboarding endpoints (B-ONBOARDING-FE-BE-MISMATCH-1, 2026-05-16).

5 endpoints nuevos con ``{dirigente_id}`` en path. Cada uno aplica
``assert_dirigente_access`` con el path param (scope multi-tenant).

NOTA: ``test_onboarding_flow.py`` usa ``authed_client`` y ``admin_session`` que
no existen como fixtures (suite legacy rota). Este archivo usa ``client`` +
``admin_token`` directamente.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dirigente import Dirigente
from app.models.organizacion import Organizacion, TipoOrganizacion

pytestmark = pytest.mark.anyio


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def dirigente_pina_scoped(db_session: AsyncSession):
    org = Organizacion(
        nombre="MC CDMX Test Scoped Q4",
        slug="mc-cdmx-scoped-q4",
        tipo=TipoOrganizacion.PARTIDO,
    )
    db_session.add(org)
    await db_session.flush()
    d = Dirigente(
        full_name="Piña Scoped Test",
        cargo="Coordinador",
        partido="MC",
        estado="CDMX",
        org_id=org.id,
    )
    db_session.add(d)
    await db_session.commit()
    await db_session.refresh(d)
    return d


async def test_profile_scoped_dirigente_inexistente(
    client: AsyncClient, admin_token: str
):
    resp = await client.post(
        "/api/v1/onboarding/999999/profile",
        json={"perfil": "politico_activo"},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 404


async def test_profile_scoped_perfil_invalido(
    client: AsyncClient, admin_token: str, dirigente_pina_scoped: Dirigente
):
    resp = await client.post(
        f"/api/v1/onboarding/{dirigente_pina_scoped.id}/profile",
        json={"perfil": "dictador"},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 422


async def test_profile_scoped_persiste(
    client: AsyncClient, admin_token: str, dirigente_pina_scoped: Dirigente
):
    resp = await client.post(
        f"/api/v1/onboarding/{dirigente_pina_scoped.id}/profile",
        json={"perfil": "politico_activo"},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["perfil_1_5"] == "politico_activo"


async def test_accounts_manual_scoped_persiste(
    client: AsyncClient, admin_token: str, dirigente_pina_scoped: Dirigente
):
    resp = await client.post(
        f"/api/v1/onboarding/{dirigente_pina_scoped.id}/accounts-manual",
        json={
            "accounts": [
                {"plataforma": "INSTAGRAM", "url": "https://instagram.com/test.scoped"},
            ],
        },
        headers=_auth(admin_token),
    )
    assert resp.status_code == 200, resp.text


async def test_promesas_scoped_persiste(
    client: AsyncClient, admin_token: str, dirigente_pina_scoped: Dirigente
):
    resp = await client.post(
        f"/api/v1/onboarding/{dirigente_pina_scoped.id}/promesas",
        json={
            "promesas": [
                {"texto_promesa": "Mejorar transporte público"},
            ],
        },
        headers=_auth(admin_token),
    )
    assert resp.status_code in (200, 201), resp.text


async def test_confirm_accounts_scoped_acepta(
    client: AsyncClient, admin_token: str, dirigente_pina_scoped: Dirigente
):
    await client.post(
        f"/api/v1/onboarding/{dirigente_pina_scoped.id}/accounts-manual",
        json={
            "accounts": [
                {"plataforma": "INSTAGRAM", "url": "https://instagram.com/test.scoped"},
            ],
        },
        headers=_auth(admin_token),
    )
    resp = await client.post(
        f"/api/v1/onboarding/{dirigente_pina_scoped.id}/confirm-accounts",
        json={
            "confirmed": [
                {"platform": "INSTAGRAM", "handle": "test.scoped", "confirmed": True},
            ],
        },
        headers=_auth(admin_token),
    )
    assert resp.status_code == 200, resp.text
