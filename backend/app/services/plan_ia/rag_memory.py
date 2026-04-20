"""RAG histórico Plan IA — Sprint S4 T3.

Recupera las top-N recomendaciones previas del mismo dirigente y las formatea
como JSON inyectable en el bloque 5 del prompt. Futuros sprints añadirán
embedding semántico sobre `accion_texto + evidencia_respaldo` para ranking
por similitud; en S4 se usa orden temporal descendente (recencia) como proxy.

Sprint S5+ task: vector embedding + top-K por similitud a diagnóstico actual.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recomendacion_plan_ia import RecomendacionPlanIA

logger = logging.getLogger(__name__)


async def fetch_historico(
    db: AsyncSession,
    dirigente_id: int,
    org_id: int,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Devuelve las últimas `limit` recomendaciones del dirigente (cualquier estado)
    ordenadas por created_at DESC.

    Args:
        db: sesión async.
        dirigente_id: FK.
        org_id: scope de org para evitar cross-tenant leak.
        limit: default 10. Sprint S4 baseline.

    Returns:
        Lista de dicts con campos resumidos aptos para inyectar en el prompt.
        Lista vacía si no hay historial.
    """
    stmt = (
        select(RecomendacionPlanIA)
        .where(RecomendacionPlanIA.dirigente_id == dirigente_id)
        .where(RecomendacionPlanIA.org_id == org_id)
        .order_by(RecomendacionPlanIA.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()

    out: list[dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "id": r.id,
                "tipo": r.tipo,
                "accion_texto": (r.accion_texto or "")[:240],
                "estado": r.estado,
                "veredicto": r.veredicto,
                "principio_conductual": r.principio_conductual,
                "bloques_citados": (r.evidencia_respaldo or {}).get("bloques_citados", []),
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
        )
    return out


def format_historico_for_prompt(historico: list[dict[str, Any]]) -> str:
    """Serializa el histórico como JSON compacto apto para el prompt.

    Si vacío, retorna marcador explícito — el LLM sabe que no hay memoria
    previa (primera generación).
    """
    if not historico:
        return '{"nota": "Sin historial previo — primera generación Plan IA para este dirigente."}'
    return json.dumps(
        {
            "total_previas": len(historico),
            "top_recomendaciones": historico,
            "nota": (
                "Usa este historial para evitar repetir recomendaciones. "
                "Si una recomendación previa fue 'completada' con veredicto "
                "'exitosa', considera 'continue' para extender; si fue 'fallida', "
                "propón 'stop' o reformulación."
            ),
        },
        ensure_ascii=False,
    )
