"""Tests endpoint agregado Tier 2 (Sprint S3 · MASTER §3.2)."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers

pytestmark = pytest.mark.asyncio


async def test_diagnostico_tier2_requires_auth(client: AsyncClient):
    r = await client.get("/api/v1/diagnostico_tier2/1")
    assert r.status_code == 401


async def test_diagnostico_tier2_completo_shape(
    client: AsyncClient, dirigente_tier2, admin_token: str
):
    r = await client.get(
        f"/api/v1/diagnostico_tier2/{dirigente_tier2.id}",
        headers=auth_headers(admin_token),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["dirigente_id"] == dirigente_tier2.id
    expected = {
        "B11_cross_partisan",
        "B12_cib_detector",
        "B13_filtro_realidad",
        "B14_topic_drift",
        "B15_rage_click",
        "B16_promesas",
        "B17_veda_compliance",
        "B18_violencia_politica",
    }
    assert set(body["bloques"].keys()) == expected
    for key, bloque in body["bloques"].items():
        assert bloque["status"] in {"ok", "insufficient_data"}
        assert bloque["bloque_version"] == "tier2-v1"
    assert body["resumen"]["total"] == 8


async def test_diagnostico_tier2_recompute_tier1(
    client: AsyncClient, dirigente_tier2, admin_token: str
):
    r = await client.get(
        f"/api/v1/diagnostico_tier2/{dirigente_tier2.id}?recompute_tier1=true",
        headers=auth_headers(admin_token),
    )
    assert r.status_code == 200
    body = r.json()
    # Debe incluir sección tier1_recomputed cuando recompute_tier1=true y B13 ok
    if body["bloques"]["B13_filtro_realidad"]["status"] == "ok":
        assert body["tier1_recomputed"] is not None
        assert "er_tier1_baseline" in body["tier1_recomputed"]


async def test_diagnostico_tier2_endpoint_individual(
    client: AsyncClient, dirigente_tier2, admin_token: str
):
    r = await client.get(
        f"/api/v1/diagnostico_tier2/{dirigente_tier2.id}/cib_detector",
        headers=auth_headers(admin_token),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["bloque"] == "B12"
