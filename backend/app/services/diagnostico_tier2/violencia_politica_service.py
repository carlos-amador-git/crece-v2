"""B18 — Escaneo Violencia Política (MASTER §3.2 #18).

Clasifica comments usando diccionarios seed de:

    - hate speech generalista MX (insultos, descalificaciones)
    - violencia política de género (VPG): insultos específicos a mujeres
      políticas (Unidad Técnica de Igualdad de Género INE 2020+)
    - amenazas directas

Severity scale:
    LOW     — hate speech (insulto genérico)
    MEDIUM  — VPG sin amenaza explícita
    HIGH    — amenaza directa

El servicio NO reemplaza auditoría humana ni Perspective API; es un
prefiltro para alertar al cliente.

Returns:
    {
        "comments_violencia": [{
            "comment_id", "post_id", "severity", "categorias", "snippet"
        }],
        "severity_dist": {"LOW": 34, "MEDIUM": 8, "HIGH": 2},
        "total_analizados": 347,
        "pct_violento": 12.6,
        "dirigentes_objetivo": [...],  # siempre [dirigente_id] en este scope
    }

Insufficient:
    - 0 comments en ventana
"""
from __future__ import annotations

import re
from collections import Counter

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.diagnostico_tier2._common import (
    AMENAZAS_KEYWORDS,
    HATE_SPEECH_KEYWORDS,
    VIOLENCIA_GENERO_KEYWORDS,
    build_dirigente_not_found,
    build_insufficient,
    build_ok,
    load_comments_for_dirigente,
    load_dirigente_scoped,
)

BLOQUE = "B18"
# Ampliada de 90 a 180 días el 2026-09-22. El scraping estuvo caído entre
# junio y septiembre (colas de Celery desconectadas, ver b21543f), así que con
# 90 días los bloques Tier 2 no alcanzaban ningún comentario y devolvían
# `insufficient_data` para todos los dirigentes. Los datos son reales; lo que
# cambia es el período que cubren.
# La ventana viaja en el payload (`ventana_dias`) y la pantalla la declara
# explícitamente: no puede quedar implícito que el análisis es "reciente".
# Revertir a 90 cuando el scraping lleve un trimestre estable.
VENTANA_DIAS = 180


def _kw_hits(keywords: list[str], text: str) -> list[str]:
    """Match con límite de palabra inicial para evitar falsos positivos por
    substring. Sin esto ``"puta"`` matchea dentro de ``"diputado"``. El ``\\b``
    inicial sin boundary final preserva stems (``"pendej"`` → ``"pendejo"``)."""
    return [k for k in keywords if re.search(rf"\b{re.escape(k)}", text)]


def _clasificar(content: str) -> tuple[str | None, list[str]]:
    """Return (severity, categorias)."""
    if not content:
        return None, []
    t = content.lower()
    categorias: list[str] = []

    amenaza = _kw_hits(AMENAZAS_KEYWORDS, t)
    vpg = _kw_hits(VIOLENCIA_GENERO_KEYWORDS, t)
    hate = _kw_hits(HATE_SPEECH_KEYWORDS, t)

    if amenaza:
        categorias.append("amenaza")
    if vpg:
        categorias.append("violencia_genero")
    if hate:
        categorias.append("hate_speech")

    if not categorias:
        return None, []

    if amenaza:
        severity = "HIGH"
    elif vpg:
        severity = "MEDIUM"
    else:
        severity = "LOW"

    return severity, categorias


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
        return build_insufficient(BLOQUE, missing=["0 comments en ventana"])

    violentos: list[dict] = []
    for c in comments:
        severity, cats = _clasificar(c.get("content") or "")
        if severity is None:
            continue
        violentos.append(
            {
                "comment_id": c["id"],
                "post_id": c["post_id"],
                "severity": severity,
                "categorias": cats,
                "author_hash": c["author_hash"],
                "snippet": (c.get("content") or "")[:180],
                "nlp_tono": c.get("nlp_tono"),
                "published_at": (
                    c["published_at"].isoformat() if c.get("published_at") else None
                ),
            }
        )

    dist = Counter(v["severity"] for v in violentos)
    pct_violento = round((len(violentos) / len(comments)) * 100.0, 2)

    return build_ok(
        BLOQUE,
        {
            "comments_violencia": violentos[:100],
            "severity_dist": dict(dist),
            "total_analizados": len(comments),
            "n_violentos": len(violentos),
            "pct_violento": pct_violento,
            "dirigentes_objetivo": [dirigente_id],
            "ventana_dias": VENTANA_DIAS,
            "diccionarios_version": "seed_mx_v1",
            "nota": (
                "Diccionarios seed conservadores. Para audit externo usar "
                "Perspective API o clasificador supervisado en Sprint S5+."
            ),
        },
    )
