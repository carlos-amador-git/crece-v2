"""Plan IA · T10 — Servicio de memoria / Bloque #10.7.

Agrega recomendaciones `completada` + `fallida` del dirigente, calcula tasa de éxito
por tipo (start/stop/continue) y por `principio_conductual`, y devuelve histórico
drill-down últimas 20 recomendaciones. Este resultado es consumible por el RAG de
Agent A (T3) como signal positivo/negativo.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.recomendacion_plan_ia import RecomendacionPlanIA

TERMINAL_ESTADOS = ("completada", "fallida")
HISTORICAL_LIMIT = 20


def _tasa_exito(counts: dict[str, int]) -> float:
    total = counts.get("total", 0)
    if total == 0:
        return 0.0
    exitosas = counts.get("exitosa", 0)
    # parcial cuenta como 0.5
    parciales = counts.get("parcial", 0)
    return round((exitosas + 0.5 * parciales) / total, 4)


def compute(
    session: Session,
    dirigente_id: int,
    org_id: int | None = None,
) -> dict[str, Any]:
    """Calcula el bloque #10.7 Memoria Plan IA para un dirigente.

    Returns:
        {
          total_completadas, tasa_exito_global,
          por_tipo: {start: {total, exitosa, parcial, fallida, tasa_exito}, ...},
          por_principio_conductual: {...},
          historico: [{id, tipo, accion_texto, veredicto, ...}]  # últimas 20
        }
    """
    q = session.query(RecomendacionPlanIA).filter(
        RecomendacionPlanIA.dirigente_id == dirigente_id,
        RecomendacionPlanIA.estado.in_(TERMINAL_ESTADOS),
    )
    if org_id is not None:
        q = q.filter(RecomendacionPlanIA.org_id == org_id)

    rows = q.order_by(desc(RecomendacionPlanIA.updated_at)).all()

    total_completadas = len(rows)

    # Global counts
    global_counts: dict[str, int] = defaultdict(int)
    por_tipo: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    por_principio: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for rec in rows:
        v = rec.veredicto or "fallida"
        global_counts["total"] += 1
        global_counts[v] += 1

        tipo = rec.tipo or "unknown"
        por_tipo[tipo]["total"] += 1
        por_tipo[tipo][v] += 1

        principio = rec.principio_conductual or "sin_principio"
        por_principio[principio]["total"] += 1
        por_principio[principio][v] += 1

    # Flatten and enrich with tasa_exito
    def _enrich(d: dict[str, dict[str, int]]) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        for k, counts in d.items():
            out[k] = {
                "total": counts.get("total", 0),
                "exitosa": counts.get("exitosa", 0),
                "parcial": counts.get("parcial", 0),
                "fallida": counts.get("fallida", 0),
                "tasa_exito": _tasa_exito(counts),
            }
        return out

    # Historical drill-down (ultimas 20)
    historico = []
    for rec in rows[:HISTORICAL_LIMIT]:
        historico.append(
            {
                "id": rec.id,
                "tipo": rec.tipo,
                "accion_texto": (rec.accion_texto or "")[:200],
                "principio_conductual": rec.principio_conductual,
                "estado": rec.estado,
                "veredicto": rec.veredicto,
                "veredicto_original": rec.veredicto_original,
                "veredicto_editado_por_cliente": rec.veredicto_editado_por_cliente,
                "ventana_inicio": rec.ventana_inicio.isoformat()
                if rec.ventana_inicio
                else None,
                "ventana_fin": rec.ventana_fin.isoformat() if rec.ventana_fin else None,
                "post_ejecutor_id": rec.post_ejecutor_id,
                "updated_at": rec.updated_at.isoformat() if rec.updated_at else None,
            }
        )

    return {
        "dirigente_id": dirigente_id,
        "org_id": org_id,
        "total_completadas": total_completadas,
        "tasa_exito_global": _tasa_exito(global_counts),
        "por_tipo": _enrich(por_tipo),
        "por_principio_conductual": _enrich(por_principio),
        "historico": historico,
    }


def rag_signal(
    session: Session,
    dirigente_id: int,
    limit: int = 10,
) -> dict[str, Any]:
    """Signal para el RAG de Agent A: qué tipos/principios tienen alta tasa de éxito.

    Útil para inyectar en el prompt del LLM como preferencia histórica del dirigente.
    """
    memoria = compute(session, dirigente_id)
    # Top-3 principios conductuales exitosos
    principios_exitosos = sorted(
        [
            (k, v)
            for k, v in memoria["por_principio_conductual"].items()
            if v["total"] >= 2 and v["tasa_exito"] >= 0.6
        ],
        key=lambda x: x[1]["tasa_exito"],
        reverse=True,
    )[:3]

    return {
        "dirigente_id": dirigente_id,
        "total_completadas": memoria["total_completadas"],
        "tasa_exito_global": memoria["tasa_exito_global"],
        "principios_preferidos": [
            {
                "principio": k,
                "tasa_exito": v["tasa_exito"],
                "total_muestras": v["total"],
            }
            for k, v in principios_exitosos
        ],
        "ejemplos_exitosos": [
            h
            for h in memoria["historico"]
            if h.get("veredicto") == "exitosa"
        ][:limit],
    }
