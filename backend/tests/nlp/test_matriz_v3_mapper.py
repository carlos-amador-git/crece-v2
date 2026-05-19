"""Tests matriz v3 mapper."""
from __future__ import annotations

import pytest

from app.nlp.matriz_v3_mapper import (
    MAPPER_VERSION,
    MapperStats,
    TARGET_MAPPING,
    TONO_MAPPING_BASE,
    get_v2_label,
    map_runner_to_v2,
)


@pytest.fixture(autouse=True)
def reset_stats():
    MapperStats.reset()
    yield


# Mapping básico --------------------------------------------------------------

def test_tono_mapping_base_completo():
    """Tonos runner clásicos (excepto pregunta + autopromocion) deben mapear."""
    runner_tonos = {"elogio", "critica", "ataque", "informativo", "personal"}
    assert runner_tonos.issubset(set(TONO_MAPPING_BASE.keys()))


def test_target_mapping_completo():
    """Los 6 targets del runner clásico deben mapear (v3.0.1 añade passthroughs)."""
    expected = {"dirigente_post", "gobierno", "oposicion", "ciudadania",
                "institucion", "otros"}
    assert expected.issubset(set(TARGET_MAPPING.keys()))


# v3.0.1 — passthrough vocab v2 directo del runner ----------------------------

@pytest.mark.parametrize("v2_tono", [
    "celebratorio",
    "propositivo",
    "critico",
    "solidario",
])
def test_passthrough_v2_tono(v2_tono):
    """Runner Gemma a veces ya devuelve vocab v2 — debe pasar tal cual sin fallback."""
    res = map_runner_to_v2(v2_tono, "gobierno")
    assert res.tono_v2 == v2_tono
    assert not res.fallback
    assert "tono_fallback_from" not in res.flags


def test_passthrough_v2_target_autopromocion():
    """target=autopromocion del runner ya en vocab v2 — passthrough sin fallback."""
    res = map_runner_to_v2("celebratorio", "autopromocion")
    assert res.target_v2 == "autopromocion"
    assert res.tono_v2 == "celebratorio"
    assert not res.fallback


@pytest.mark.parametrize("runner,v2", [
    ("elogio", "celebratorio"),
    ("critica", "critico"),
    ("ataque", "ataque"),
    ("informativo", "informativo"),
    ("personal", "personal"),
])
def test_tono_basic(runner, v2):
    res = map_runner_to_v2(runner, "gobierno")
    assert res.tono_v2 == v2
    assert not res.fallback


@pytest.mark.parametrize("runner,v2", [
    ("dirigente_post", "dirigente"),
    ("gobierno", "gobierno"),
    ("oposicion", "oposicion"),
    ("ciudadania", "ciudadania"),
    ("institucion", "tema_especifico"),
    ("otros", "tema_especifico"),
])
def test_target_basic(runner, v2):
    res = map_runner_to_v2("informativo", runner)
    assert res.target_v2 == v2


def test_mapping_version_in_output():
    res = map_runner_to_v2("elogio", "dirigente_post")
    assert res.mapping_version == MAPPER_VERSION


# R3 — autopromoción runtime (G2) ---------------------------------------------

def test_autopromo_runtime_overrides():
    """is_self_authored=True debe disparar autopromocion antes de mapping."""
    res = map_runner_to_v2(
        "ataque", "gobierno",
        is_self_authored=True,
    )
    assert res.tono_v2 == "celebratorio"
    assert res.target_v2 == "autopromocion"
    assert res.flags.get("autopromo_runtime") is True


def test_autopromo_runner_tono():
    """tono=autopromocion (sin self-authored) → celebratorio + autopromocion target."""
    res = map_runner_to_v2("autopromocion", "dirigente_post")
    assert res.tono_v2 == "celebratorio"
    assert res.target_v2 == "autopromocion"
    assert res.flags.get("from_runner_autopromocion") is True


# R5 — pregunta con/sin hostility (G1) ----------------------------------------

def test_pregunta_default_informativo():
    res = map_runner_to_v2("pregunta", "gobierno", comment_text="¿En qué fecha?")
    assert res.tono_v2 == "informativo"
    assert res.flags.get("pregunta_default") is True


def test_pregunta_hostility_critico():
    res = map_runner_to_v2(
        "pregunta", "gobierno",
        comment_text="¿Hasta cuándo seguirán mintiendo?"
    )
    assert res.tono_v2 == "critico"
    assert res.flags.get("pregunta_hostility_detected") is True


@pytest.mark.parametrize("texto", [
    "¿Por qué tanta corrupción?",
    "¡Qué vergüenza!",
    "Renuncia ya"
])
def test_pregunta_varios_hostiles(texto):
    res = map_runner_to_v2("pregunta", "gobierno", comment_text=texto)
    assert res.tono_v2 == "critico"


# R2 — emoji breve (G4) -------------------------------------------------------

def test_emoji_breve_promote_only_dirigente():
    """Comment <30 chars con ≥2 emojis + target=dirigente → celebratorio."""
    res = map_runner_to_v2(
        "personal", "dirigente_post",
        comment_text="💪🧡 Maynez",
    )
    assert res.tono_v2 == "celebratorio"
    assert res.flags.get("emoji_breve_promotion") is True


def test_emoji_breve_no_promote_otros_target():
    """Mismo emoji-breve PERO target=gobierno → no promote (G4 condicional)."""
    res = map_runner_to_v2(
        "personal", "gobierno",
        comment_text="💪🧡 contra todos",
    )
    assert res.tono_v2 == "personal"
    assert "emoji_breve_promotion" not in res.flags


def test_emoji_breve_no_promote_long_text():
    """≥30 chars no aplica promotion."""
    res = map_runner_to_v2(
        "personal", "dirigente_post",
        comment_text="💪🧡 Maynez es lo mejor que ha pasado al pais entero",
    )
    assert res.tono_v2 == "personal"


def test_emoji_breve_no_promote_one_emoji():
    """1 emoji no es suficiente."""
    res = map_runner_to_v2(
        "personal", "dirigente_post",
        comment_text="❤️ Linda",
    )
    assert res.tono_v2 == "personal"


# Fallbacks (G5) --------------------------------------------------------------

def test_tono_unknown_fallback():
    res = map_runner_to_v2("emocion_random", "gobierno")
    assert res.tono_v2 == "personal"
    assert res.fallback
    assert res.flags.get("tono_fallback_from") == "emocion_random"


def test_target_unknown_fallback():
    res = map_runner_to_v2("informativo", "extranjero")
    assert res.target_v2 == "tema_especifico"
    assert res.fallback


# Stats (G5) ------------------------------------------------------------------

def test_mapper_stats_counters():
    map_runner_to_v2("elogio", "gobierno")
    map_runner_to_v2("emocion_x", "gobierno")  # fallback
    map_runner_to_v2("pregunta", "gobierno", comment_text="¿Cuándo?")  # default informativo
    map_runner_to_v2("pregunta", "gobierno", comment_text="renuncia ya!")  # critico
    map_runner_to_v2("personal", "dirigente_post", comment_text="💪🧡 X")  # emoji_breve
    map_runner_to_v2("ataque", "gobierno", is_self_authored=True)  # autopromo runtime

    snap = MapperStats.snapshot()
    assert snap["total"] == 6
    assert snap["fallbacks"] == 1
    assert snap["pregunta_to_informativo"] == 1
    assert snap["pregunta_to_critico"] == 1
    assert snap["emoji_breve"] == 1
    assert snap["autopromo_runtime"] == 1


# Public helper ---------------------------------------------------------------

def test_get_v2_label_helper():
    tono, target = get_v2_label("elogio", "dirigente_post")
    assert tono == "celebratorio"
    assert target == "dirigente"
