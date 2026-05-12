"""Plan IA · T8 — Servicio de seguimiento 14d ventana.

Recorre recomendaciones `estado='ejecutada'` con `ventana_fin > NOW()` y actualiza
`metricas_observadas` JSONB con snapshot diario del post ejecutor. Marca un flag
`alerta_desviacion` cuando la diferencia entre observadas y predichas supera el
umbral definido en `criterio_exito`.

Ejecutado diariamente por el Celery task `plan_ia_seguimiento_diario` a las 03:00 UTC.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.recomendacion_plan_ia import RecomendacionPlanIA
from app.models.social import SocialPost

logger = logging.getLogger(__name__)


def _snapshot_post(post: SocialPost) -> dict[str, Any]:
    """Return a dict snapshot of the current post metrics."""
    return {
        "fecha": datetime.now(UTC).date().isoformat(),
        "timestamp": datetime.now(UTC).isoformat(),
        "likes": int(post.likes or 0),
        "comments": int(post.comments or 0),
        "shares": int(post.shares or 0),
        "views": int(post.views or 0),
        "engagement_rate": float(post.engagement_rate or 0.0),
    }


def _detect_desviacion(
    metricas_predichas: dict[str, Any] | None,
    ultimo_snapshot: dict[str, Any],
    criterio_exito: dict[str, Any] | None,
) -> dict[str, Any]:
    """Compute whether the last snapshot deviates from predictions beyond criterio_exito threshold.

    Returns a dict `{flag: bool, reason: str, pct: float}` suitable for UI bloque #10.5.
    """
    if not metricas_predichas or not ultimo_snapshot:
        return {"flag": False, "reason": "sin_predicciones", "pct": 0.0}

    # Threshold default: 20% desviation, overridable via criterio_exito.umbral_desviacion_pct
    umbral_pct = 0.20
    if criterio_exito and isinstance(criterio_exito, dict):
        try:
            umbral_pct = float(criterio_exito.get("umbral_desviacion_pct", umbral_pct))
        except (TypeError, ValueError):
            umbral_pct = 0.20

    # Use the first predicted metric present in both dicts as the reference
    for metrica, predicho in metricas_predichas.items():
        observado = ultimo_snapshot.get(metrica)
        if observado is None or predicho in (None, 0):
            continue
        try:
            predicho_f = float(predicho)
            observado_f = float(observado)
        except (TypeError, ValueError):
            continue
        if predicho_f == 0:
            continue
        delta_pct = abs(observado_f - predicho_f) / predicho_f
        if delta_pct >= umbral_pct:
            return {
                "flag": True,
                "reason": f"{metrica}:{observado_f:.2f}_vs_{predicho_f:.2f}",
                "pct": round(delta_pct, 4),
            }

    return {"flag": False, "reason": "dentro_umbral", "pct": 0.0}


def actualizar_seguimiento(session: Session) -> dict[str, Any]:
    """Actualiza `metricas_observadas` de todas las recomendaciones en ventana activa.

    Returns dict con {procesadas, actualizadas, alertas, errores}.
    """
    now = datetime.now(UTC)
    rows = (
        session.query(RecomendacionPlanIA)
        .filter(
            RecomendacionPlanIA.estado == "ejecutada",
            RecomendacionPlanIA.ventana_fin.isnot(None),
            RecomendacionPlanIA.ventana_fin > now,
            RecomendacionPlanIA.post_ejecutor_id.isnot(None),
        )
        .all()
    )

    procesadas = 0
    actualizadas = 0
    alertas = 0
    errores = 0

    for rec in rows:
        procesadas += 1
        try:
            post = session.get(SocialPost, rec.post_ejecutor_id)
            if post is None:
                logger.warning(
                    "seguimiento: recomendacion %d tiene post_ejecutor_id %d inexistente",
                    rec.id,
                    rec.post_ejecutor_id,
                )
                errores += 1
                continue

            snapshot = _snapshot_post(post)
            existing = rec.metricas_observadas or {}
            snapshots = list(existing.get("snapshots_diarios", []))
            snapshots.append(snapshot)

            desviacion = _detect_desviacion(rec.metricas_predichas, snapshot, rec.criterio_exito)

            nuevo = {
                **existing,
                "snapshots_diarios": snapshots,
                "ultimo_snapshot": snapshot,
                "alerta_desviacion": desviacion,
                "actualizado_en": now.isoformat(),
            }
            rec.metricas_observadas = nuevo
            rec.updated_at = now
            actualizadas += 1
            if desviacion.get("flag"):
                alertas += 1
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("seguimiento: error en recomendacion %d: %s", rec.id, exc)
            errores += 1

    session.commit()
    return {
        "procesadas": procesadas,
        "actualizadas": actualizadas,
        "alertas": alertas,
        "errores": errores,
        "timestamp": now.isoformat(),
    }


def evolucion_diaria(session: Session, recomendacion_id: int) -> dict[str, Any]:
    """Devuelve la evolución diaria de una recomendación para UI bloque #10.5."""
    rec = session.get(RecomendacionPlanIA, recomendacion_id)
    if rec is None:
        return {"error": "recomendacion_not_found", "id": recomendacion_id}

    observadas = rec.metricas_observadas or {}
    return {
        "recomendacion_id": rec.id,
        "dirigente_id": rec.dirigente_id,
        "estado": rec.estado,
        "ventana_inicio": rec.ventana_inicio.isoformat() if rec.ventana_inicio else None,
        "ventana_fin": rec.ventana_fin.isoformat() if rec.ventana_fin else None,
        "metricas_predichas": rec.metricas_predichas,
        "criterio_exito": rec.criterio_exito,
        "post_ejecutor_id": rec.post_ejecutor_id,
        "snapshots_diarios": observadas.get("snapshots_diarios", []),
        "ultimo_snapshot": observadas.get("ultimo_snapshot"),
        "alerta_desviacion": observadas.get("alerta_desviacion"),
    }
