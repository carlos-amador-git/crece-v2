"""B11 — Cross-Partisan Validation Score (MASTER §3.2 #11).

Infiere afiliación partidista del autor de cada comment usando diccionarios
keyword (MC, MORENA, PAN, PRI, PVEM, PT). El score 0-100 mide qué porcentaje
del engagement (comments) proviene de partidos distintos al del dirigente.

Valor analítico:
    - score_cross_partisan_0_100 alto = mensaje cruza líneas partidistas
      (bueno para outreach, malo para base leal consolidada).
    - Útil para distinguir "choir preaching" vs "cross-cutting influence"
      (Habermas + Sunstein, Echo Chambers 2001).

Returns:
    {
        "score_cross_partisan_0_100": 34.2,
        "comments_por_partido": {"MC": 120, "MORENA": 45, "PAN": 10, "PRI": 4, ...},
        "pct_out_of_base": 34.2,
        "partido_dirigente": "MC",
        "posts_cross_partisan_top": [{post_id, pct_out_of_base, n_comments}],
        "n_comments_clasificados": 180,
        "n_comments_sin_clasificacion": 167,
    }

Insufficient:
    - 0 comments en ventana
    - 0 comments con afiliación inferible (todos "UNKNOWN")
"""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.diagnostico_tier2._common import (
    AFILIACION_KEYWORDS,
    build_dirigente_not_found,
    build_insufficient,
    build_ok,
    load_comments_for_dirigente,
    load_dirigente_scoped,
)

BLOQUE = "B11"
VENTANA_DIAS = 90


def inferir_afiliacion(content: str | None) -> str:
    """Return partido inferred or 'UNKNOWN' if no keyword matched."""
    if not content:
        return "UNKNOWN"
    t = content.lower()
    for partido, kws in AFILIACION_KEYWORDS.items():
        for k in kws:
            if k in t:
                return partido
    return "UNKNOWN"


async def compute(
    db: AsyncSession,
    dirigente_id: int,
    org_id: int | None = None,
) -> dict:
    dirigente = await load_dirigente_scoped(db, dirigente_id, org_id)
    if dirigente is None:
        return build_dirigente_not_found(BLOQUE, dirigente_id)

    comments = await load_comments_for_dirigente(db, dirigente_id, VENTANA_DIAS)
    if not comments:
        return build_insufficient(
            BLOQUE,
            missing=[f"0 comments en últimos {VENTANA_DIAS} días para dirigente={dirigente_id}"],
        )

    partido_dirigente = (dirigente.partido or "MC").upper()

    conteo: dict[str, int] = defaultdict(int)
    por_post: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for c in comments:
        partido = inferir_afiliacion(c.get("content"))
        conteo[partido] += 1
        por_post[c["post_id"]][partido] += 1

    total = len(comments)
    clasificados = total - conteo.get("UNKNOWN", 0)
    if clasificados == 0:
        return build_insufficient(
            BLOQUE,
            missing=[
                f"De {total} comentarios analizados, cero mencionan partidos tradicionales (MORENA, MC, PAN, PRI, PVEM, PT).",
                "La audiencia no se identifica con el sistema bipartidista — el bloque no aplica al perfil.",
            ],
            extra={
                "comments_por_partido": dict(conteo),
                "n_comments_total": total,
            },
        )

    in_base = conteo.get(partido_dirigente, 0)
    out_of_base = clasificados - in_base
    pct_out = round((out_of_base / clasificados) * 100.0, 2) if clasificados else 0.0

    # Top posts cross-partisan (más % out-of-base, mínimo 3 comments clasificados)
    posts_ranking = []
    for post_id, partidos in por_post.items():
        total_post = sum(partidos.values())
        clasif_post = total_post - partidos.get("UNKNOWN", 0)
        if clasif_post < 3:
            continue
        in_base_post = partidos.get(partido_dirigente, 0)
        pct_post = round(((clasif_post - in_base_post) / clasif_post) * 100.0, 2)
        posts_ranking.append(
            {
                "post_id": post_id,
                "pct_out_of_base": pct_post,
                "n_comments_clasificados": clasif_post,
                "distribucion": dict(partidos),
            }
        )
    posts_ranking.sort(key=lambda x: x["pct_out_of_base"], reverse=True)

    return build_ok(
        BLOQUE,
        {
            "score_cross_partisan_0_100": pct_out,
            "comments_por_partido": dict(conteo),
            "pct_out_of_base": pct_out,
            "partido_dirigente": partido_dirigente,
            "posts_cross_partisan_top": posts_ranking[:10],
            "n_comments_clasificados": clasificados,
            "n_comments_sin_clasificacion": conteo.get("UNKNOWN", 0),
            "n_comments_total": total,
            "ventana_dias": VENTANA_DIAS,
            "metodologia": "keyword_dictionary_v1",
        },
    )
