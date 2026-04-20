"""Tests unitarios para los 8 services Tier 2 (Sprint S3 · MASTER §3.2)."""
from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.diagnostico_tier2 import (
    cib_detector_service,
    cross_partisan_service,
    filtro_realidad_service,
    promesas_service,
    rage_click_service,
    topic_drift_service,
    veda_compliance_service,
    violencia_politica_service,
)

pytestmark = pytest.mark.asyncio


def _assert_shape(result: dict, bloque: str) -> None:
    assert "status" in result
    assert result.get("bloque") == bloque
    assert result.get("bloque_version") == "tier2-v1"
    assert result["status"] in {"ok", "insufficient_data"}


# ── B11 Cross-Partisan ────────────────────────────────────────────────

async def test_b11_cross_partisan(db_session: AsyncSession, dirigente_tier2):
    r = await cross_partisan_service.compute(
        db_session, dirigente_tier2.id, org_id=dirigente_tier2.org_id
    )
    _assert_shape(r, "B11")
    assert r["status"] == "ok"
    assert r["data"]["partido_dirigente"] == "MC"
    assert r["data"]["n_comments_total"] > 0
    assert "comments_por_partido" in r["data"]


async def test_b11_insufficient(db_session, dirigente_tier2_sin_data):
    r = await cross_partisan_service.compute(
        db_session, dirigente_tier2_sin_data.id, org_id=dirigente_tier2_sin_data.org_id
    )
    _assert_shape(r, "B11")
    assert r["status"] == "insufficient_data"


# ── B12 CIB Detector ──────────────────────────────────────────────────

async def test_b12_cib_detector(db_session, dirigente_tier2):
    r = await cib_detector_service.compute(
        db_session, dirigente_tier2.id, org_id=dirigente_tier2.org_id
    )
    _assert_shape(r, "B12")
    assert r["status"] == "ok"
    assert r["data"]["total_comments_analizados"] >= 20
    # fixture seedea hash_MC01 con 3 comments en mismo post < 1h → maestro
    assert r["data"]["authors_maestro_ceremonias"] >= 1
    # hash_AA01 y hash_AA02 tienen texto idéntico → coro
    assert r["data"]["authors_coro_cluster"] >= 2


# ── B13 Filtro Realidad ───────────────────────────────────────────────

async def test_b13_filtro_realidad(db_session, dirigente_tier2):
    r = await filtro_realidad_service.compute(
        db_session, dirigente_tier2.id, org_id=dirigente_tier2.org_id
    )
    _assert_shape(r, "B13")
    assert r["status"] == "ok"
    assert r["data"]["er_total_comments"] > 0
    assert r["data"]["impact_hint"] in {"alto", "medio", "bajo"}


# ── B14 Topic Drift ───────────────────────────────────────────────────

async def test_b14_topic_drift(db_session, dirigente_tier2):
    r = await topic_drift_service.compute(
        db_session, dirigente_tier2.id, org_id=dirigente_tier2.org_id
    )
    _assert_shape(r, "B14")
    assert r["status"] == "ok"
    assert r["data"]["n_posts_analizados"] >= 1
    assert 0 <= r["data"]["drift_score_promedio"] <= 1


# ── B15 Rage Click ────────────────────────────────────────────────────

async def test_b15_rage_click(db_session, dirigente_tier2):
    r = await rage_click_service.compute(
        db_session, dirigente_tier2.id, org_id=dirigente_tier2.org_id
    )
    _assert_shape(r, "B15")
    assert r["status"] == "ok"
    assert r["data"]["rage_clicks_detectados"] >= 1  # post 4 con 3/5 hostiles


# ── B16 Promesas ──────────────────────────────────────────────────────

async def test_b16_promesas(db_session, dirigente_tier2):
    r = await promesas_service.compute(
        db_session, dirigente_tier2.id, org_id=dirigente_tier2.org_id
    )
    _assert_shape(r, "B16")
    assert r["status"] == "ok"
    assert r["data"]["n_promesas_total"] == 2


async def test_b16_promesas_insufficient(db_session, dirigente_tier2_sin_data):
    r = await promesas_service.compute(
        db_session, dirigente_tier2_sin_data.id,
        org_id=dirigente_tier2_sin_data.org_id,
    )
    _assert_shape(r, "B16")
    assert r["status"] == "insufficient_data"


# ── B17 Veda Compliance ───────────────────────────────────────────────

async def test_b17_veda_sin_veda_activa(db_session, dirigente_tier2):
    r = await veda_compliance_service.compute(
        db_session, dirigente_tier2.id,
        org_id=dirigente_tier2.org_id, en_veda=False,
    )
    _assert_shape(r, "B17")
    assert r["status"] == "ok"
    assert r["data"]["puede_publicar"] is True
    # post 5 contiene "voto" y "candidato" — debe estar en riesgo
    assert r["data"]["n_posts_riesgo"] >= 1


async def test_b17_veda_con_veda_activa_bloquea(db_session, dirigente_tier2):
    r = await veda_compliance_service.compute(
        db_session, dirigente_tier2.id,
        org_id=dirigente_tier2.org_id, en_veda=True,
    )
    assert r["status"] == "ok"
    assert r["data"]["ventana_veda_activa"] is True
    # hay posts_riesgo → puede_publicar False
    assert r["data"]["puede_publicar"] is False


# ── B18 Violencia Política ────────────────────────────────────────────

async def test_b18_violencia_politica(db_session, dirigente_tier2):
    r = await violencia_politica_service.compute(
        db_session, dirigente_tier2.id, org_id=dirigente_tier2.org_id
    )
    _assert_shape(r, "B18")
    assert r["status"] == "ok"
    # fixture tiene: VPG ("putita", "mujerzuela"), amenazas ("te voy a matar"),
    # hate ("pendejo", "corrupto"). esperar >0 detectados.
    assert r["data"]["n_violentos"] >= 3
    dist = r["data"]["severity_dist"]
    assert "HIGH" in dist  # amenaza directa


async def test_b18_insufficient(db_session, dirigente_tier2_sin_data):
    r = await violencia_politica_service.compute(
        db_session, dirigente_tier2_sin_data.id,
        org_id=dirigente_tier2_sin_data.org_id,
    )
    _assert_shape(r, "B18")
    assert r["status"] == "insufficient_data"
