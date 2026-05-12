"""Plan IA · T9 — Servicio de cierre automático.

Al vencer la ventana de 14 días, calcula un veredicto automático (exitosa/parcial/fallida)
según el cumplimiento del `criterio_exito` vs `metricas_observadas`. El cliente puede
editar el veredicto; el servicio preserva `veredicto_original` y marca la edición.

Ejecutado diariamente por el Celery task `plan_ia_cierre_diario` a las 04:00 UTC.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.recomendacion_plan_ia import RecomendacionPlanIA

logger = logging.getLogger(__name__)

# Thresholds
EXITOSA_THRESHOLD = 0.80
PARCIAL_THRESHOLD = 0.40


def _calcular_cumplimiento(
    criterio_exito: dict[str, Any] | None,
    metricas_observadas: dict[str, Any] | None,
) -> dict[str, Any]:
    """Calcula el porcentaje de cumplimiento del criterio de éxito.

    `criterio_exito` espera la forma:
        {"metrica": "engagement_rate", "objetivo": 0.05, "tipo": "min"}
        o
        {"metrica": "likes", "objetivo": 100, "tipo": "min"}

    Retorna: {pct_cumplimiento, observado, objetivo, metrica, tipo}
    """
    if not criterio_exito or not isinstance(criterio_exito, dict):
        return {"pct_cumplimiento": 0.0, "motivo": "sin_criterio"}
    if not metricas_observadas or not isinstance(metricas_observadas, dict):
        return {"pct_cumplimiento": 0.0, "motivo": "sin_metricas_observadas"}

    metrica = criterio_exito.get("metrica")
    objetivo = criterio_exito.get("objetivo")
    tipo = criterio_exito.get("tipo", "min")  # 'min' o 'max'
    if metrica is None or objetivo in (None, 0):
        return {"pct_cumplimiento": 0.0, "motivo": "criterio_incompleto"}

    ultimo = metricas_observadas.get("ultimo_snapshot") or {}
    observado = ultimo.get(metrica)
    if observado is None:
        return {"pct_cumplimiento": 0.0, "motivo": f"sin_dato_{metrica}"}

    try:
        obj_f = float(objetivo)
        obs_f = float(observado)
    except (TypeError, ValueError):
        return {"pct_cumplimiento": 0.0, "motivo": "valor_no_numerico"}

    if obj_f == 0:
        return {"pct_cumplimiento": 0.0, "motivo": "objetivo_cero"}

    if tipo == "min":
        pct = obs_f / obj_f
    elif tipo == "max":
        # tipo 'max' = reducir; éxito cuando observado <= objetivo
        if obs_f <= obj_f:
            pct = 1.0
        else:
            pct = max(0.0, 1.0 - ((obs_f - obj_f) / obj_f))
    else:
        pct = obs_f / obj_f

    return {
        "pct_cumplimiento": round(pct, 4),
        "observado": obs_f,
        "objetivo": obj_f,
        "metrica": metrica,
        "tipo": tipo,
    }


def _veredicto_por_pct(pct: float) -> str:
    if pct >= EXITOSA_THRESHOLD:
        return "exitosa"
    if pct >= PARCIAL_THRESHOLD:
        return "parcial"
    return "fallida"


def cerrar_ventanas_vencidas(session: Session) -> dict[str, Any]:
    """Cierra recomendaciones cuya `ventana_fin <= NOW()` y estaban `estado='ejecutada'`.

    Returns dict con {procesadas, completadas, exitosas, parciales, fallidas, errores}.
    """
    now = datetime.now(UTC)
    rows = (
        session.query(RecomendacionPlanIA)
        .filter(
            RecomendacionPlanIA.estado == "ejecutada",
            RecomendacionPlanIA.ventana_fin.isnot(None),
            RecomendacionPlanIA.ventana_fin <= now,
        )
        .all()
    )

    counts = {
        "procesadas": 0,
        "completadas": 0,
        "exitosas": 0,
        "parciales": 0,
        "fallidas": 0,
        "errores": 0,
    }
    veredicto_key = {"exitosa": "exitosas", "parcial": "parciales", "fallida": "fallidas"}

    for rec in rows:
        counts["procesadas"] += 1
        try:
            cumplimiento = _calcular_cumplimiento(rec.criterio_exito, rec.metricas_observadas)
            pct = float(cumplimiento.get("pct_cumplimiento", 0.0))
            veredicto = _veredicto_por_pct(pct)

            rec.veredicto = veredicto
            # Preserve the original LLM veredicto the first time we set it
            if rec.veredicto_original is None:
                rec.veredicto_original = veredicto

            # Estado final
            rec.estado = "completada" if veredicto != "fallida" else "fallida"

            # Persistimos el cumplimiento dentro de metricas_observadas
            observadas = rec.metricas_observadas or {}
            observadas["cumplimiento_final"] = cumplimiento
            rec.metricas_observadas = observadas

            rec.updated_at = now

            counts["completadas"] += 1
            counts[veredicto_key[veredicto]] += 1
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("cierre: error en recomendacion %d: %s", rec.id, exc)
            counts["errores"] += 1

    session.commit()
    counts["timestamp"] = now.isoformat()
    return counts


def editar_veredicto_cliente(
    session: Session,
    recomendacion_id: int,
    nuevo_veredicto: str,
    notas: str | None = None,
) -> dict[str, Any]:
    """Edita el veredicto por el cliente, preservando `veredicto_original`.

    Validación: `nuevo_veredicto` debe ser uno de {exitosa, parcial, fallida}.
    """
    if nuevo_veredicto not in ("exitosa", "parcial", "fallida"):
        return {"error": "veredicto_invalido", "valor": nuevo_veredicto}

    rec = session.get(RecomendacionPlanIA, recomendacion_id)
    if rec is None:
        return {"error": "recomendacion_not_found", "id": recomendacion_id}

    # Preservar original si no estaba preservado
    if rec.veredicto_original is None:
        rec.veredicto_original = rec.veredicto

    rec.veredicto = nuevo_veredicto
    rec.veredicto_editado_por_cliente = True
    if notas is not None:
        rec.notas_cliente = notas

    # Re-sincronizar estado con veredicto editado
    rec.estado = "completada" if nuevo_veredicto != "fallida" else "fallida"
    rec.updated_at = datetime.now(UTC)

    session.commit()
    return {
        "id": rec.id,
        "veredicto": rec.veredicto,
        "veredicto_original": rec.veredicto_original,
        "veredicto_editado_por_cliente": rec.veredicto_editado_por_cliente,
        "estado": rec.estado,
        "notas_cliente": rec.notas_cliente,
    }
