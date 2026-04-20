"""B13 — Filtro de Realidad (MASTER §3.2 #13).

Wrapper sobre B01 ER que recalcula el engagement excluyendo los comments de
author_hash flagged por B12 (CIB Detector). Devuelve el delta entre ER crudo
y ER orgánico — killer feature del producto porque demuestra el valor.

El recálculo real de los servicios Tier 1 con los excluidos se hace en el
endpoint agregado. Este service solo reporta el delta de engagement sobre
el corpus de comments.

Returns:
    {
        "er_total_comments": 347,
        "er_organico_comments": 312,
        "delta_comments_cib": 35,
        "pct_comments_flagged": 10.1,
        "flagged_author_count": 5,
        "ejemplos_flagged": [author_hash_masked...],
        "impact_hint": "alto" | "medio" | "bajo",
    }

Insufficient:
    - B12 regresó insufficient_data
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.diagnostico_tier2 import cib_detector_service
from app.services.diagnostico_tier2._common import (
    build_dirigente_not_found,
    build_insufficient,
    build_ok,
    load_comments_for_dirigente,
    load_dirigente_scoped,
)

BLOQUE = "B13"
VENTANA_DIAS = 90


def _clasificar_impacto(pct: float) -> str:
    if pct >= 20:
        return "alto"
    if pct >= 5:
        return "medio"
    return "bajo"


async def compute(
    db: AsyncSession,
    dirigente_id: int,
    org_id: int | None = None,
    cib_result: dict | None = None,
) -> dict:
    """Compute delta CIB/organico.

    Args:
        cib_result: resultado precomputado de B12 (evita re-ejecutar NLP).
                    Si None, se ejecuta B12 internamente.
    """
    dirigente = await load_dirigente_scoped(db, dirigente_id, org_id)
    if dirigente is None:
        return build_dirigente_not_found(BLOQUE, dirigente_id)

    if cib_result is None:
        cib_result = await cib_detector_service.compute(db, dirigente_id, org_id)

    if cib_result.get("status") != "ok":
        return build_insufficient(
            BLOQUE,
            missing=[
                f"B12 CIB Detector regresó status={cib_result.get('status')}",
                *cib_result.get("missing", []),
            ],
        )

    all_comments = await load_comments_for_dirigente(db, dirigente_id, VENTANA_DIAS)
    if not all_comments:
        return build_insufficient(BLOQUE, missing=["0 comments en ventana"])

    flagged_hashes = {
        f["author_hash"] for f in cib_result["data"].get("flagged_cib", [])
    }

    if not flagged_hashes:
        return build_ok(
            BLOQUE,
            {
                "er_total_comments": len(all_comments),
                "er_organico_comments": len(all_comments),
                "delta_comments_cib": 0,
                "pct_comments_flagged": 0.0,
                "flagged_author_count": 0,
                "ejemplos_flagged": [],
                "impact_hint": "bajo",
                "note": "Sin authors CIB detectados — ER orgánico == ER total",
                "ventana_dias": VENTANA_DIAS,
            },
        )

    comments_cib = sum(1 for c in all_comments if c["author_hash"] in flagged_hashes)
    comments_organicos = len(all_comments) - comments_cib
    pct_flagged = round((comments_cib / len(all_comments)) * 100.0, 2)

    ejemplos = [f"{h[:12]}…" for h in list(flagged_hashes)[:5]]

    return build_ok(
        BLOQUE,
        {
            "er_total_comments": len(all_comments),
            "er_organico_comments": comments_organicos,
            "delta_comments_cib": comments_cib,
            "pct_comments_flagged": pct_flagged,
            "flagged_author_count": len(flagged_hashes),
            "ejemplos_flagged": ejemplos,
            "impact_hint": _clasificar_impacto(pct_flagged),
            "flagged_hashes_para_exclusion": list(flagged_hashes),
            "ventana_dias": VENTANA_DIAS,
            "note": (
                "Para ver ER Tier 1 recalculado sin CIB, use el endpoint "
                f"/api/v1/diagnostico_tier2/{dirigente_id}?recompute_tier1=true"
            ),
        },
    )
