"""Tests de endpoints agregados — /api/v1/diagnostico/{id}."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers

pytestmark = pytest.mark.asyncio


async def test_diagnostico_completo_requires_auth(client: AsyncClient):
    r = await client.get("/api/v1/diagnostico/1")
    assert r.status_code == 401


async def test_diagnostico_completo_shape(
    client: AsyncClient, dirigente_with_data, admin_token: str
):
    r = await client.get(
        f"/api/v1/diagnostico/{dirigente_with_data.id}",
        headers=auth_headers(admin_token),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["dirigente_id"] == dirigente_with_data.id
    assert "bloques" in body
    expected_keys = {
        "B01_er_normalizado",
        "B02_breakout_scale",
        "B03_matriz_2x2",
        "B04_benchmark",
        "B05_sentiment_plutchik",
        "B06_crisis_spike",
        "B07_growth_attribution",
        "B08_sov",
        "B09_share_like_ratio",
        "B10_humanizacion",
    }
    assert set(body["bloques"].keys()) == expected_keys
    # Cada bloque tiene shape válido
    for key, bloque in body["bloques"].items():
        assert bloque["status"] in {"ok", "insufficient_data"}
        assert "bloque_version" in bloque
    assert body["resumen"]["total"] == 10
    assert body["resumen"]["ok"] + body["resumen"]["insufficient_data"] == 10


async def test_diagnostico_endpoint_individual(
    client: AsyncClient, dirigente_with_data, admin_token: str
):
    r = await client.get(
        f"/api/v1/diagnostico/{dirigente_with_data.id}/er_normalizado",
        headers=auth_headers(admin_token),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["bloque"] == "B01"
    assert body["status"] == "ok"
