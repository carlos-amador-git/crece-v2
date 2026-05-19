"""Tests for /api/v1/alerts/ integration endpoints."""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alerta_crisis import AlertaCrisis
from app.models.organizacion import Organizacion, TipoOrganizacion
from app.models.user import User
from tests.conftest import auth_headers

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_org(db: AsyncSession) -> Organizacion:
    org = Organizacion(
        nombre="MC Alerts Test",
        slug="mc-alerts-test",
        tipo=TipoOrganizacion.PARTIDO,
        estado="Ciudad de Mexico",
        is_active=True,
    )
    db.add(org)
    await db.flush()
    await db.refresh(org)
    return org


async def _create_alerta(
    db: AsyncSession,
    org_id: int,
    severidad: str = "media",
    estado: str = "nueva",
    tipo: str = "negative_trend",
) -> AlertaCrisis:
    alerta = AlertaCrisis(
        org_id=org_id,
        tipo=tipo,
        severidad=severidad,
        descripcion="Incremento de menciones negativas en las ultimas 6 horas",
        estado=estado,
        post_ids=[],
    )
    db.add(alerta)
    await db.flush()
    await db.refresh(alerta)
    return alerta


# ---------------------------------------------------------------------------
# Auth guard
# ---------------------------------------------------------------------------


async def test_list_alerts_requires_auth(client: AsyncClient) -> None:
    """GET /alerts/ without token returns 401."""
    resp = await client.get("/api/v1/alerts/")
    assert resp.status_code == 401


async def test_patch_alert_status_requires_auth(client: AsyncClient) -> None:
    """PATCH /alerts/{id}/status without token returns 401."""
    resp = await client.patch("/api/v1/alerts/1/status", json={"estado": "vista"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# List alerts
# ---------------------------------------------------------------------------


async def test_list_alerts_empty(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user: User,
    admin_token: str,
) -> None:
    """GET /alerts/ returns empty list when no alerts exist."""
    org = await _create_org(db_session)
    admin_user.org_id = org.id
    await db_session.commit()
    await db_session.refresh(admin_user)

    resp = await client.get("/api/v1/alerts/", headers=auth_headers(admin_token))
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_alerts_with_data(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user: User,
    admin_token: str,
) -> None:
    """GET /alerts/ returns all seeded alerts for the org."""
    org = await _create_org(db_session)
    admin_user.org_id = org.id
    await db_session.flush()

    await _create_alerta(db_session, org.id, severidad="baja")
    await _create_alerta(db_session, org.id, severidad="alta")
    await db_session.commit()
    await db_session.refresh(admin_user)

    resp = await client.get("/api/v1/alerts/", headers=auth_headers(admin_token))
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2


async def test_list_alerts_scoped_to_org(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user: User,
    admin_token: str,
) -> None:
    """GET /alerts/ only returns alerts belonging to the current user's org."""
    org_own = await _create_org(db_session)

    # Second org — alerts from here must not appear
    org_other = Organizacion(
        nombre="Otra Org",
        slug="otra-org",
        tipo=TipoOrganizacion.CANDIDATURA,
        is_active=True,
    )
    db_session.add(org_other)
    await db_session.flush()
    await db_session.refresh(org_other)

    admin_user.org_id = org_own.id
    await db_session.flush()

    await _create_alerta(db_session, org_own.id, severidad="alta")
    await _create_alerta(db_session, org_other.id, severidad="critica")
    await db_session.commit()
    await db_session.refresh(admin_user)

    resp = await client.get("/api/v1/alerts/", headers=auth_headers(admin_token))
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["severidad"] == "alta"


# ---------------------------------------------------------------------------
# Filter by severity
# ---------------------------------------------------------------------------


async def test_filter_alerts_by_severity(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user: User,
    admin_token: str,
) -> None:
    """GET /alerts/?severity=alta returns only high severity alerts."""
    org = await _create_org(db_session)
    admin_user.org_id = org.id
    await db_session.flush()

    await _create_alerta(db_session, org.id, severidad="baja")
    await _create_alerta(db_session, org.id, severidad="media")
    await _create_alerta(db_session, org.id, severidad="alta")
    await _create_alerta(db_session, org.id, severidad="alta")
    await db_session.commit()
    await db_session.refresh(admin_user)

    resp = await client.get(
        "/api/v1/alerts/?severity=alta",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    for item in body:
        assert item["severidad"] == "alta"


async def test_filter_alerts_by_status(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user: User,
    admin_token: str,
) -> None:
    """GET /alerts/?status=atendida returns only atendida alerts."""
    org = await _create_org(db_session)
    admin_user.org_id = org.id
    await db_session.flush()

    await _create_alerta(db_session, org.id, estado="nueva")
    await _create_alerta(db_session, org.id, estado="atendida")
    await db_session.commit()
    await db_session.refresh(admin_user)

    resp = await client.get(
        "/api/v1/alerts/?status=atendida",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["estado"] == "atendida"


# ---------------------------------------------------------------------------
# Update alert status
# ---------------------------------------------------------------------------


async def test_update_alert_status(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user: User,
    admin_token: str,
) -> None:
    """PATCH /alerts/{id}/status transitions estado correctly."""
    org = await _create_org(db_session)
    admin_user.org_id = org.id
    await db_session.flush()
    alerta = await _create_alerta(db_session, org.id, estado="nueva")
    await db_session.commit()
    await db_session.refresh(admin_user)
    await db_session.refresh(alerta)

    resp = await client.patch(
        f"/api/v1/alerts/{alerta.id}/status",
        json={"estado": "atendida"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["estado"] == "atendida"
    assert body["alert_id"] == alerta.id


async def test_update_alert_status_invalid_value(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user: User,
    admin_token: str,
) -> None:
    """PATCH /alerts/{id}/status with invalid estado returns 400."""
    org = await _create_org(db_session)
    admin_user.org_id = org.id
    await db_session.flush()
    alerta = await _create_alerta(db_session, org.id)
    await db_session.commit()
    await db_session.refresh(admin_user)
    await db_session.refresh(alerta)

    resp = await client.patch(
        f"/api/v1/alerts/{alerta.id}/status",
        json={"estado": "invalido"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 400
    assert "Invalid status" in resp.json()["detail"]


async def test_update_alert_status_not_found(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user: User,
    admin_token: str,
) -> None:
    """PATCH /alerts/{id}/status for non-existent alert returns 404."""
    org = await _create_org(db_session)
    admin_user.org_id = org.id
    await db_session.commit()
    await db_session.refresh(admin_user)

    resp = await client.patch(
        "/api/v1/alerts/99999/status",
        json={"estado": "vista"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 404


async def test_update_alert_status_all_valid_transitions(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user: User,
    admin_token: str,
) -> None:
    """PATCH /alerts/{id}/status accepts vista, atendida, and descartada."""
    org = await _create_org(db_session)
    admin_user.org_id = org.id
    await db_session.commit()
    await db_session.refresh(admin_user)

    for estado in ("vista", "atendida", "descartada"):
        alerta = await _create_alerta(db_session, org.id, estado="nueva")
        await db_session.commit()
        await db_session.refresh(alerta)

        resp = await client.patch(
            f"/api/v1/alerts/{alerta.id}/status",
            json={"estado": estado},
            headers=auth_headers(admin_token),
        )
        assert resp.status_code == 200, f"Expected 200 for estado={estado}"
        assert resp.json()["estado"] == estado
