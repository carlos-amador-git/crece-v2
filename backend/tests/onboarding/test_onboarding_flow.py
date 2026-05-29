"""Tests unitarios del Onboarding Wizard Sprint S5.

Cubre 1 test por endpoint principal + verificación D-23 regla dura
(confirmación humana obligatoria pre-scraping).
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.models.dirigente import Dirigente
from app.models.organizacion import Organizacion

pytestmark = pytest.mark.anyio


@pytest.fixture
async def dirigente_pina(admin_session, admin_user):
    """Crea un dirigente Piña para los tests (id autogenerado)."""
    org = Organizacion(
        id=1,
        name="MC CDMX Test",
        slug=f"mc-cdmx-test-{id(admin_user)}",
    )
    admin_session.add(org)
    await admin_session.flush()

    d = Dirigente(
        full_name="Alejandro Piña Test",
        cargo="Coordinador Test",
        partido="MC",
        estado="CDMX",
        org_id=org.id,
    )
    admin_session.add(d)
    await admin_session.commit()
    await admin_session.refresh(d)
    return d


async def test_post_profile_valida_y_persiste(
    authed_client: AsyncClient, dirigente_pina
):
    resp = await authed_client.post(
        "/api/v1/onboarding/profile",
        json={"dirigente_id": dirigente_pina.id, "perfil": "politico_activo"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["perfil_1_5"] == "politico_activo"


async def test_post_profile_rechaza_perfil_invalido(
    authed_client: AsyncClient, dirigente_pina
):
    resp = await authed_client.post(
        "/api/v1/onboarding/profile",
        json={"dirigente_id": dirigente_pina.id, "perfil": "dictador"},
    )
    assert resp.status_code == 422


async def test_post_accounts_manual_extrae_handle_normalizado(
    authed_client: AsyncClient, dirigente_pina
):
    resp = await authed_client.post(
        "/api/v1/onboarding/accounts/manual",
        json={
            "dirigente_id": dirigente_pina.id,
            "accounts": [
                {"plataforma": "INSTAGRAM", "url": "https://instagram.com/Alejandro.PINHA"},
                {"plataforma": "TWITTER", "url": "https://x.com/Alejandro_Pinha"},
                {"plataforma": "FACEBOOK", "url": "https://no-valid.example.com/foo"},
            ],
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    handles = {p["platform"]: p["handle"] for p in body["persisted"]}
    assert handles["INSTAGRAM"] == "alejandro.pinha"
    assert handles["TWITTER"] == "alejandro_pinha"
    assert body["coverage"]["INSTAGRAM"] is True
    assert len(body["invalid_urls"]) >= 1


async def test_confirm_accounts_requiere_flag_explicito_D23(
    authed_client: AsyncClient, dirigente_pina
):
    # Sección 2: persistir
    await authed_client.post(
        "/api/v1/onboarding/accounts/manual",
        json={
            "dirigente_id": dirigente_pina.id,
            "accounts": [
                {"plataforma": "INSTAGRAM", "url": "https://instagram.com/pina_test"},
            ],
        },
    )
    # Sección 5: confirmed=False NO activa
    resp = await authed_client.post(
        "/api/v1/onboarding/confirm-accounts",
        json={
            "dirigente_id": dirigente_pina.id,
            "confirmed": [
                {"platform": "INSTAGRAM", "handle": "pina_test", "confirmed": False},
            ],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_activated"] == 0
    assert body["pending"][0]["reason"] == "confirmed_flag_missing_or_false"


async def test_confirm_accounts_activa_con_flag_true(
    authed_client: AsyncClient, dirigente_pina
):
    await authed_client.post(
        "/api/v1/onboarding/accounts/manual",
        json={
            "dirigente_id": dirigente_pina.id,
            "accounts": [
                {"plataforma": "INSTAGRAM", "url": "https://instagram.com/pina_test"},
            ],
        },
    )
    resp = await authed_client.post(
        "/api/v1/onboarding/confirm-accounts",
        json={
            "dirigente_id": dirigente_pina.id,
            "confirmed": [
                {"platform": "INSTAGRAM", "handle": "pina_test", "confirmed": True},
            ],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_activated"] == 1


async def test_oauth_init_excluye_x_D19(authed_client: AsyncClient, dirigente_pina):
    resp = await authed_client.get(
        f"/api/v1/oauth/init/x?dirigente_id={dirigente_pina.id}"
    )
    assert resp.status_code == 422  # X rechazado por ck platform


async def test_oauth_callback_stub_marca_is_stub_true(
    authed_client: AsyncClient, dirigente_pina
):
    resp = await authed_client.post(
        "/api/v1/oauth/callback/instagram",
        json={
            "dirigente_id": dirigente_pina.id,
            "platform_user_id": "1234",
            "platform_username": "pina_test",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_stub"] is True
    assert body["platform"] == "instagram"


async def test_oauth_status_incluye_x_nota_D19(
    authed_client: AsyncClient, dirigente_pina
):
    resp = await authed_client.get(f"/api/v1/oauth/status/{dirigente_pina.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert "x" in body["platforms"]
    assert "D-19" in body["platforms"]["x"]["note"]


async def test_competidores_popula_array_dirigente(
    authed_client: AsyncClient, dirigente_pina
):
    resp = await authed_client.post(
        "/api/v1/onboarding/competidores",
        json={
            "dirigente_id": dirigente_pina.id,
            "competidores": [
                {"full_name": "Comp 1 Test", "cargo": "Cargo Test", "partido": "MORENA"},
                {"full_name": "Comp 2 Test", "cargo": "Cargo Test 2", "partido": "PAN"},
            ],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert len(body["competidor_ids"]) == 2


async def test_promesas_bulk_insert(authed_client: AsyncClient, dirigente_pina):
    resp = await authed_client.post(
        "/api/v1/onboarding/promesas",
        json={
            "dirigente_id": dirigente_pina.id,
            "promesas": [
                {"texto_promesa": "Promesa de prueba unitaria con suficiente longitud"},
            ],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


async def test_activate_falla_con_requisitos_faltantes(
    authed_client: AsyncClient, dirigente_pina
):
    # Sin perfil ni cuentas ni competidores ni promesas → 409
    resp = await authed_client.post(
        f"/api/v1/onboarding/activate/{dirigente_pina.id}"
    )
    assert resp.status_code == 409
    detail = resp.json()["detail"]
    assert "missing" in detail
    assert len(detail["missing"]) >= 3
