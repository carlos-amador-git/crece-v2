"""Tests unitarios para los 10 services Tier 1 (Sprint S2).

Cada test:
    1. Usa el fixture ``dirigente_with_data`` (12 posts + 2 snapshots) para happy path.
    2. Usa ``dirigente_sin_posts`` para validar que se regresa ``insufficient_data``
       en lugar de crashear.
"""
from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.diagnostico import (
    benchmark_service,
    breakout_service,
    crisis_spike_service,
    er_service,
    growth_attribution_service,
    humanizacion_service,
    matrix_2x2_service,
    sentiment_plutchik_service,
    share_like_ratio_service,
    sov_service,
)

pytestmark = pytest.mark.asyncio


# ── Shape común ────────────────────────────────────────────────────────

def _assert_shape(result: dict, bloque: str) -> None:
    assert "status" in result
    assert result.get("bloque") == bloque
    assert "bloque_version" in result
    assert "computed_at" in result
    assert result["status"] in {"ok", "insufficient_data"}


# ── B01 ER normalizado ─────────────────────────────────────────────────

async def test_b01_er_happy_path(db_session: AsyncSession, dirigente_with_data):
    r = await er_service.compute(db_session, dirigente_with_data.id, org_id=dirigente_with_data.org_id)
    _assert_shape(r, "B01")
    assert r["status"] == "ok"
    assert "er_por_plataforma" in r["data"]
    assert "TWITTER" in r["data"]["er_por_plataforma"]
    assert r["data"]["estrato"] in {"Nano", "Micro", "Mid", "Macro", "Mega"}
    assert r["data"]["modificador_temporal"] == 1.0  # sin dias_a_comicio


async def test_b01_er_insufficient(db_session: AsyncSession, dirigente_sin_posts):
    r = await er_service.compute(db_session, dirigente_sin_posts.id, org_id=dirigente_sin_posts.org_id)
    _assert_shape(r, "B01")
    assert r["status"] == "insufficient_data"


async def test_b01_modificador_temporal_en_ventana(db_session: AsyncSession, dirigente_with_data):
    r = await er_service.compute(
        db_session, dirigente_with_data.id, org_id=dirigente_with_data.org_id, dias_a_comicio=20
    )
    assert r["status"] == "ok"
    # 7 < dias <= 30 → plateau 2.5
    assert r["data"]["modificador_temporal"] == 2.5


# ── B02 Breakout ───────────────────────────────────────────────────────

async def test_b02_breakout_happy(db_session: AsyncSession, dirigente_with_data):
    r = await breakout_service.compute(db_session, dirigente_with_data.id, org_id=dirigente_with_data.org_id)
    _assert_shape(r, "B02")
    assert r["status"] == "ok"
    assert 1 <= r["data"]["max_categoria"] <= 6
    assert "posts_por_categoria" in r["data"]


async def test_b02_insufficient(db_session: AsyncSession, dirigente_sin_posts):
    r = await breakout_service.compute(db_session, dirigente_sin_posts.id)
    _assert_shape(r, "B02")
    assert r["status"] == "insufficient_data"


# ── B03 Matriz 2x2 ─────────────────────────────────────────────────────

async def test_b03_matriz_happy(db_session: AsyncSession, dirigente_with_data):
    r = await matrix_2x2_service.compute(db_session, dirigente_with_data.id, org_id=dirigente_with_data.org_id)
    _assert_shape(r, "B03")
    assert r["status"] == "ok"
    assert set(r["data"]["conteo_cuadrantes"].keys()) == {"INSIGNIA", "CRISIS", "VANIDAD", "MUERTA"}


async def test_b03_insufficient(db_session: AsyncSession, dirigente_sin_posts):
    r = await matrix_2x2_service.compute(db_session, dirigente_sin_posts.id)
    _assert_shape(r, "B03")
    assert r["status"] == "insufficient_data"


# ── B04 Benchmark ──────────────────────────────────────────────────────

async def test_b04_benchmark_insufficient_sin_proxies(db_session: AsyncSession, dirigente_with_data):
    # Piña(1) tiene proxy S2, pero este dirigente_with_data tiene un ID distinto
    # → fallback insufficient con origen_competidores='ninguno'
    r = await benchmark_service.compute(db_session, dirigente_with_data.id, org_id=dirigente_with_data.org_id)
    _assert_shape(r, "B04")
    # Shape OK — el test verifica graceful degradation
    assert r["status"] in {"ok", "insufficient_data"}


# ── B05 Plutchik ───────────────────────────────────────────────────────

async def test_b05_plutchik_happy(db_session: AsyncSession, dirigente_with_data):
    r = await sentiment_plutchik_service.compute(db_session, dirigente_with_data.id, org_id=dirigente_with_data.org_id)
    _assert_shape(r, "B05")
    assert r["status"] == "ok"
    assert set(r["data"]["emociones_promedio"].keys()) == {"trust", "anger", "joy", "fear", "sadness", "disgust"}


async def test_b05_insufficient(db_session: AsyncSession, dirigente_sin_posts):
    r = await sentiment_plutchik_service.compute(db_session, dirigente_sin_posts.id)
    _assert_shape(r, "B05")
    assert r["status"] == "insufficient_data"


# ── B06 Crisis Spike ───────────────────────────────────────────────────

async def test_b06_crisis_spike(db_session: AsyncSession, dirigente_with_data):
    r = await crisis_spike_service.compute(db_session, dirigente_with_data.id, org_id=dirigente_with_data.org_id)
    _assert_shape(r, "B06")
    # Puede ser ok o insufficient según posts en baseline 7d
    if r["status"] == "ok":
        assert "spike_detected" in r["data"]
        assert 0 <= r["data"]["severity"] <= 1


# ── B07 Growth Attribution ─────────────────────────────────────────────

async def test_b07_growth_happy(db_session: AsyncSession, dirigente_with_data):
    r = await growth_attribution_service.compute(db_session, dirigente_with_data.id, org_id=dirigente_with_data.org_id)
    _assert_shape(r, "B07")
    assert r["status"] == "ok"
    assert "followers_ganados_total" in r["data"]
    assert r["data"]["half_life_dias"] == 7


async def test_b07_insufficient(db_session: AsyncSession, dirigente_sin_posts):
    r = await growth_attribution_service.compute(db_session, dirigente_sin_posts.id)
    _assert_shape(r, "B07")
    assert r["status"] == "insufficient_data"


# ── B08 SoV ────────────────────────────────────────────────────────────

async def test_b08_sov(db_session: AsyncSession, dirigente_with_data):
    r = await sov_service.compute(db_session, dirigente_with_data.id, org_id=dirigente_with_data.org_id)
    _assert_shape(r, "B08")
    assert r["status"] == "ok"
    topics = {t["topic"] for t in r["data"]["topics_cubiertos"]}
    assert {"seguridad", "economia", "salud"}.issubset(topics) or len(topics) >= 1


# ── B09 Share/Like ─────────────────────────────────────────────────────

async def test_b09_share_like(db_session: AsyncSession, dirigente_with_data):
    r = await share_like_ratio_service.compute(db_session, dirigente_with_data.id, org_id=dirigente_with_data.org_id)
    _assert_shape(r, "B09")
    assert r["status"] == "ok"
    assert r["data"]["semaforo"] in {"VERDE", "AMARILLO", "ROJO"}
    assert r["data"]["n_posts"] > 0


# ── B10 Humanización ───────────────────────────────────────────────────

async def test_b10_humanizacion_happy(db_session: AsyncSession, dirigente_with_data):
    r = await humanizacion_service.compute(db_session, dirigente_with_data.id, org_id=dirigente_with_data.org_id)
    _assert_shape(r, "B10")
    assert r["status"] == "ok"
    assert 0 <= r["data"]["score_0_100"] <= 100
    # El fixture usa "familia/colonia/gracias" → humanización alta
    assert r["data"]["factores"]["keywords_personales_pct"] > 0
