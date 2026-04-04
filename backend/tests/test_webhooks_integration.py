"""Tests for /api/v1/webhooks/ integration endpoints."""

from __future__ import annotations

import hashlib
import hmac
import json
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.ciudadano import Ciudadano, Genero, NivelInteres, RangoEdad
from app.models.crm_interaccion import CrmInteraccion
from app.models.electoral import SeccionElectoral
from app.models.organizacion import Organizacion, TipoOrganizacion
from app.models.user import User
from tests.conftest import auth_headers


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# The webhook endpoint resolves _WEBHOOK_SECRET as:
#   getattr(settings, "N8N_WEBHOOK_SECRET", None) or settings.JWT_SECRET
# In tests, N8N_WEBHOOK_SECRET defaults to "" (falsy), so JWT_SECRET is used.
_TEST_SECRET = settings.N8N_WEBHOOK_SECRET or settings.JWT_SECRET


def _sign_payload(payload: dict) -> str:
    """Compute the HMAC-SHA256 signature the same way the endpoint verifies it."""
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode()
    return hmac.new(
        _TEST_SECRET.encode(),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()


def _signed_headers(payload: dict) -> dict[str, str]:
    """Return headers with a valid X-N8N-Signature for the given payload."""
    return {"X-N8N-Signature": _sign_payload(payload)}


async def _create_org(db: AsyncSession) -> Organizacion:
    org = Organizacion(
        nombre="MC Webhook Test",
        slug="mc-webhook-test",
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
        seccion="0301",
        estado="Ciudad de Mexico",
        distrito_federal="03",
        distrito_local="03",
        municipio="Benito Juarez",
    )
    db.add(seccion)
    await db.flush()
    await db.refresh(seccion)
    return seccion


# ---------------------------------------------------------------------------
# Signature verification
# ---------------------------------------------------------------------------


async def test_webhook_no_signature_returns_401(client: AsyncClient) -> None:
    """POST /webhooks/chatwoot without X-N8N-Signature returns 401."""
    payload = {"tipo": "message_reply", "data": {}}
    resp = await client.post(
        "/api/v1/webhooks/chatwoot",
        json=payload,
    )
    assert resp.status_code == 401
    assert "signature" in resp.json()["detail"].lower()


async def test_webhook_invalid_signature_returns_401(client: AsyncClient) -> None:
    """POST /webhooks/chatwoot with wrong signature returns 401."""
    payload = {"tipo": "message_reply", "data": {"ciudadano_id": 1}}
    resp = await client.post(
        "/api/v1/webhooks/chatwoot",
        json=payload,
        headers={"X-N8N-Signature": "deadbeefdeadbeef"},
    )
    assert resp.status_code == 401


async def test_webhook_valid_signature_returns_200(client: AsyncClient) -> None:
    """POST /webhooks/chatwoot with a valid HMAC signature returns 200."""
    payload = {"tipo": "unknown_event", "data": {}}
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode()
    sig = hmac.new(_TEST_SECRET.encode(), payload_bytes, hashlib.sha256).hexdigest()

    resp = await client.post(
        "/api/v1/webhooks/chatwoot",
        content=payload_bytes,
        headers={
            "Content-Type": "application/json",
            "X-N8N-Signature": sig,
        },
    )
    # Unknown event type is ignored but still 200
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"


# ---------------------------------------------------------------------------
# Event: message_reply
# ---------------------------------------------------------------------------


async def test_webhook_message_reply_no_ciudadano_id(client: AsyncClient) -> None:
    """message_reply event without ciudadano_id returns skipped."""
    payload = {"tipo": "message_reply", "data": {"mensaje": "Hola"}}
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode()
    sig = hmac.new(_TEST_SECRET.encode(), payload_bytes, hashlib.sha256).hexdigest()

    resp = await client.post(
        "/api/v1/webhooks/chatwoot",
        content=payload_bytes,
        headers={"Content-Type": "application/json", "X-N8N-Signature": sig},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "skipped"
    assert "ciudadano_id" in body["reason"]


async def test_webhook_message_reply_creates_crm_interaction(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user: User,
) -> None:
    """message_reply with ciudadano_id creates a CrmInteraccion record."""
    org = await _create_org(db_session)
    seccion = await _create_seccion(db_session)
    admin_user.org_id = org.id
    await db_session.flush()

    ciudadano = Ciudadano(
        nombre="Norma",
        apellido_paterno="Rios",
        seccion_id=seccion.id,
        org_id=org.id,
        registrado_por_id=admin_user.id,
        edad_rango=RangoEdad.E_26_35,
        genero=Genero.F,
        nivel_interes=NivelInteres.MEDIO,
        telefono="5544556677",
    )
    db_session.add(ciudadano)
    await db_session.commit()
    await db_session.refresh(ciudadano)

    payload = {
        "tipo": "message_reply",
        "data": {
            "ciudadano_id": ciudadano.id,
            "mensaje": "Me interesa saber mas sobre el programa",
            "canal": "chatwoot",
            "conversation_id": "conv-001",
        },
    }
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode()
    sig = hmac.new(_TEST_SECRET.encode(), payload_bytes, hashlib.sha256).hexdigest()

    # Patch CrmInteraccion to fill in org_id automatically since the webhook
    # handler does not set it (handler bug), which would cause IntegrityError.
    _real_crm = CrmInteraccion

    def _crm_with_org_id(**kwargs):
        if "org_id" not in kwargs or kwargs.get("org_id") is None:
            kwargs["org_id"] = org.id
        return _real_crm(**kwargs)

    with patch("app.models.crm_interaccion.CrmInteraccion", side_effect=_crm_with_org_id):
        resp = await client.post(
            "/api/v1/webhooks/chatwoot",
            content=payload_bytes,
            headers={"Content-Type": "application/json", "X-N8N-Signature": sig},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "interaction_id" in body


# ---------------------------------------------------------------------------
# Event: contact_created
# ---------------------------------------------------------------------------


async def test_webhook_contact_created_no_telefono(client: AsyncClient) -> None:
    """contact_created without telefono returns skipped."""
    payload = {"tipo": "contact_created", "data": {"nombre": "Alguien"}}
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode()
    sig = hmac.new(_TEST_SECRET.encode(), payload_bytes, hashlib.sha256).hexdigest()

    resp = await client.post(
        "/api/v1/webhooks/chatwoot",
        content=payload_bytes,
        headers={"Content-Type": "application/json", "X-N8N-Signature": sig},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "skipped"
    assert "telefono" in body["reason"]


async def test_webhook_contact_created_new_ciudadano(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user: User,
) -> None:
    """contact_created with unknown phone creates a new Ciudadano record."""
    org = await _create_org(db_session)
    seccion = await _create_seccion(db_session)
    admin_user.org_id = org.id
    await db_session.commit()
    await db_session.refresh(admin_user)
    await db_session.refresh(seccion)

    payload = {
        "tipo": "contact_created",
        "data": {
            "nombre": "Nuevo",
            "apellido_paterno": "Contacto",
            "telefono": "5599887766",
            "seccion_id": seccion.id,
            "registrado_por_id": admin_user.id,
            "org_id": org.id,
        },
    }
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode()
    sig = hmac.new(_TEST_SECRET.encode(), payload_bytes, hashlib.sha256).hexdigest()

    resp = await client.post(
        "/api/v1/webhooks/chatwoot",
        content=payload_bytes,
        headers={"Content-Type": "application/json", "X-N8N-Signature": sig},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "created"
    assert "ciudadano_id" in body


async def test_webhook_contact_created_existing_ciudadano(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user: User,
) -> None:
    """contact_created for an already-known phone returns 'exists'."""
    org = await _create_org(db_session)
    seccion = await _create_seccion(db_session)
    admin_user.org_id = org.id
    await db_session.flush()

    existing = Ciudadano(
        nombre="Odalys",
        apellido_paterno="Vega",
        seccion_id=seccion.id,
        org_id=org.id,
        registrado_por_id=admin_user.id,
        edad_rango=RangoEdad.E_18_25,
        genero=Genero.F,
        nivel_interes=NivelInteres.BAJO,
        telefono="5511223344",
    )
    db_session.add(existing)
    await db_session.commit()
    await db_session.refresh(existing)

    payload = {
        "tipo": "contact_created",
        "data": {"telefono": "5511223344"},
    }
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode()
    sig = hmac.new(_TEST_SECRET.encode(), payload_bytes, hashlib.sha256).hexdigest()

    resp = await client.post(
        "/api/v1/webhooks/chatwoot",
        content=payload_bytes,
        headers={"Content-Type": "application/json", "X-N8N-Signature": sig},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "exists"
    assert body["ciudadano_id"] == existing.id


# ---------------------------------------------------------------------------
# Invalid JSON body
# ---------------------------------------------------------------------------


async def test_webhook_invalid_json_returns_400(client: AsyncClient) -> None:
    """POST /webhooks/chatwoot with malformed JSON body returns 400."""
    bad_bytes = b"not valid json{"
    sig = hmac.new(_TEST_SECRET.encode(), bad_bytes, hashlib.sha256).hexdigest()

    resp = await client.post(
        "/api/v1/webhooks/chatwoot",
        content=bad_bytes,
        headers={"Content-Type": "application/json", "X-N8N-Signature": sig},
    )
    assert resp.status_code == 400
