"""Unit tests for AntiVanityValidator (Sprint S4 T-1.4).

Valida 5+ casos positivos y 5+ negativos para el validador post-generación
del Plan IA. No requiere DB ni Ollama.
"""
from __future__ import annotations

import pytest

from app.services.plan_ia.anti_vanity_validator import AntiVanityValidator


@pytest.fixture
def validator() -> AntiVanityValidator:
    return AntiVanityValidator()


def _base_valid() -> dict:
    """Plantilla válida base usada por los casos positivos."""
    return {
        "tipo": "start",
        "accion_texto": (
            "Publicar hilo de 4 tweets con cifras INE sobre transparencia "
            "en gasto estatal cada martes 9 AM durante 4 semanas consecutivas."
        ),
        "ventana_duracion_dias": 28,
        "criterio_exito": {
            "metrica": "er_pct",
            "umbral": 3.5,
            "direccion": "aumentar",
            "ventana_medicion_dias": 28,
        },
        "principio_conductual": "Cialdini Authority",
        "evidencia_respaldo": {
            "bloques_citados": ["B01", "B08"],
            "post_id_referencia": None,
            "metrica_referencia": "er_pct_slot_07_09",
            "ventana_temporal": "martes 9AM",
        },
    }


class TestValidatorPositiveCases:
    """Casos que DEBEN pasar (válidos)."""

    def test_recomendacion_start_completa(self, validator: AntiVanityValidator) -> None:
        ok, errors = validator.validate(_base_valid())
        assert ok, f"Debería pasar, errores: {errors}"
        assert errors == []

    def test_recomendacion_stop_con_post_id(self, validator: AntiVanityValidator) -> None:
        rec = _base_valid()
        rec["tipo"] = "stop"
        rec["accion_texto"] = (
            "Dejar de publicar con 3+ hashtags: B03 matriz 2x2 muestra 8/10 "
            "posts multi-hashtag cayeron en cuadrante Muerta en últimas 4 semanas."
        )
        rec["evidencia_respaldo"] = {
            "bloques_citados": ["B03"],
            "post_id_referencia": 12345,
            "metrica_referencia": None,
            "ventana_temporal": "últimas 4 semanas",
        }
        ok, errors = validator.validate(rec)
        assert ok, f"Errores: {errors}"

    def test_recomendacion_continue_varios_bloques(
        self, validator: AntiVanityValidator
    ) -> None:
        rec = _base_valid()
        rec["tipo"] = "continue"
        rec["evidencia_respaldo"]["bloques_citados"] = ["B01", "B05", "B13"]
        ok, errors = validator.validate(rec)
        assert ok, f"Errores: {errors}"

    def test_solo_ventana_temporal_como_evidencia_especifica(
        self, validator: AntiVanityValidator
    ) -> None:
        rec = _base_valid()
        rec["evidencia_respaldo"] = {
            "bloques_citados": ["B01"],
            "post_id_referencia": None,
            "metrica_referencia": None,
            "ventana_temporal": "domingo 20h",
        }
        ok, errors = validator.validate(rec)
        assert ok, f"Errores: {errors}"

    def test_principio_haidt_care(self, validator: AntiVanityValidator) -> None:
        rec = _base_valid()
        rec["principio_conductual"] = "Haidt Care"
        ok, errors = validator.validate(rec)
        assert ok, f"Errores: {errors}"

    def test_bloque_b18_limite_superior(self, validator: AntiVanityValidator) -> None:
        rec = _base_valid()
        rec["evidencia_respaldo"]["bloques_citados"] = ["B18"]
        ok, errors = validator.validate(rec)
        assert ok, f"Errores: {errors}"


class TestValidatorNegativeCases:
    """Casos que DEBEN ser rechazados."""

    def test_vacio_publica_mas_contenido(self, validator: AntiVanityValidator) -> None:
        rec = _base_valid()
        rec["accion_texto"] = "Publica más contenido."
        rec["evidencia_respaldo"]["bloques_citados"] = []
        ok, errors = validator.validate(rec)
        assert not ok
        assert any("bloques_citados" in e for e in errors)

    def test_sin_bloques_citados_es_rechazado(
        self, validator: AntiVanityValidator
    ) -> None:
        rec = _base_valid()
        rec["evidencia_respaldo"]["bloques_citados"] = []
        ok, errors = validator.validate(rec)
        assert not ok
        assert any("bloques_citados" in e for e in errors)

    def test_sin_evidencia_especifica_rechaza(
        self, validator: AntiVanityValidator
    ) -> None:
        rec = _base_valid()
        rec["evidencia_respaldo"] = {
            "bloques_citados": ["B01"],
            "post_id_referencia": None,
            "metrica_referencia": None,
            "ventana_temporal": None,
        }
        ok, errors = validator.validate(rec)
        assert not ok
        assert any("evidencia específica" in e.lower() or "post_id_referencia" in e for e in errors)

    def test_accion_texto_demasiado_corta(
        self, validator: AntiVanityValidator
    ) -> None:
        rec = _base_valid()
        rec["accion_texto"] = "Hacer más."
        ok, errors = validator.validate(rec)
        assert not ok
        assert any("accion_texto" in e for e in errors)

    def test_tipo_invalido_rechaza(self, validator: AntiVanityValidator) -> None:
        rec = _base_valid()
        rec["tipo"] = "increment"  # inválido
        ok, errors = validator.validate(rec)
        assert not ok
        assert any("tipo" in e for e in errors)

    def test_sin_principio_conductual_rechaza(
        self, validator: AntiVanityValidator
    ) -> None:
        rec = _base_valid()
        rec["principio_conductual"] = ""
        ok, errors = validator.validate(rec)
        assert not ok
        assert any("principio_conductual" in e for e in errors)

    def test_criterio_exito_incompleto_rechaza(
        self, validator: AntiVanityValidator
    ) -> None:
        rec = _base_valid()
        rec["criterio_exito"] = {"metrica": "er_pct"}  # faltan umbral + direccion
        ok, errors = validator.validate(rec)
        assert not ok
        assert any("criterio_exito" in e for e in errors)

    def test_bloque_invalido_fuera_rango(
        self, validator: AntiVanityValidator
    ) -> None:
        rec = _base_valid()
        rec["evidencia_respaldo"]["bloques_citados"] = ["B19", "B99", "X01"]
        ok, errors = validator.validate(rec)
        assert not ok
        # B19+ no pasan regex; como no hay cita inline tampoco, debe rechazar
        assert any("bloques_citados" in e for e in errors)

    def test_mejora_tu_narrativa_rechaza(
        self, validator: AntiVanityValidator
    ) -> None:
        rec = _base_valid()
        rec["accion_texto"] = "Mejora tu narrativa para conectar."
        rec["evidencia_respaldo"]["bloques_citados"] = []
        ok, errors = validator.validate(rec)
        assert not ok
        assert len(errors) >= 1


class TestValidatorBatch:
    def test_batch_mixed_valid_and_rejected(
        self, validator: AntiVanityValidator
    ) -> None:
        valid_rec = _base_valid()
        invalid_rec = _base_valid()
        invalid_rec["accion_texto"] = "Publica más contenido para ganar"
        invalid_rec["evidencia_respaldo"]["bloques_citados"] = []
        valid, rejected = validator.validate_batch([valid_rec, invalid_rec])
        assert len(valid) == 1
        assert len(rejected) == 1

    def test_feedback_for_retry_format(
        self, validator: AntiVanityValidator
    ) -> None:
        invalid_rec = _base_valid()
        invalid_rec["evidencia_respaldo"]["bloques_citados"] = []
        _, rejected = validator.validate_batch([invalid_rec])
        feedback = AntiVanityValidator.feedback_for_retry(rejected)
        assert "rechazó" in feedback.lower() or "rechaz" in feedback.lower()
        assert "B01" in feedback or "bloque" in feedback.lower()

    def test_feedback_empty_when_no_rejections(
        self, validator: AntiVanityValidator
    ) -> None:
        feedback = AntiVanityValidator.feedback_for_retry([])
        assert feedback == ""
