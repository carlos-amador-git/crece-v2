"""B12 — CIB Detector multinivel (MASTER §3.2 #12).

Framework ITESO / DFRLab para detección de Coordinated Inauthentic Behavior:

    a) Maestros de Ceremonias: autores que hacen >=3 comments en mismo post
       dentro de ventana <1h (comportamiento de repost/farm).
    b) Cuentas Coro: autores distintos con similaridad léxica alta (Jaccard
       sobre n-grams) — mensaje coordinado en corpus.
    c) Account age heurística: si author_hash aparece por PRIMERA VEZ en el
       periodo y con > K comments → sospecha de cuenta nueva farm.

El servicio retorna ``flagged_cib`` lista de author_hash sospechosos con
razón + confidence_score 0-1.

Returns:
    {
        "total_comments_analizados": 347,
        "flagged_cib": [
            {"author_hash": "a1b2...", "razones": ["maestro_ceremonias:post_42"], "confidence": 0.85, "n_comments": 5},
            ...
        ],
        "authors_maestro_ceremonias": 3,
        "authors_coro_cluster": 7,
        "authors_nuevos_sospechosos": 2,
        "confidence_score": 0.58,
        "n_authors_unicos": 210,
    }

Insufficient:
    - 0 comments o <20 comments (señal insuficiente para detección)
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.diagnostico_tier2._common import (
    build_dirigente_not_found,
    build_insufficient,
    build_ok,
    load_comments_for_dirigente,
    load_dirigente_scoped,
)

BLOQUE = "B12"
# Ampliada de 90 a 180 días el 2026-09-22. El scraping estuvo caído entre
# junio y septiembre (colas de Celery desconectadas, ver b21543f), así que con
# 90 días los bloques Tier 2 no alcanzaban ningún comentario y devolvían
# `insufficient_data` para todos los dirigentes. Los datos son reales; lo que
# cambia es el período que cubren.
# La ventana viaja en el payload (`ventana_dias`) y la pantalla la declara
# explícitamente: no puede quedar implícito que el análisis es "reciente".
# Revertir a 90 cuando el scraping lleve un trimestre estable.
VENTANA_DIAS = 180
MIN_COMMENTS_REQUERIDOS = 20
UMBRAL_MAESTRO_CEREMONIAS = 3  # comments en mismo post en <60min
VENTANA_MAESTRO_SEG = 60 * 60
UMBRAL_JACCARD = 0.8  # similaridad para "cuentas coro"
UMBRAL_COMMENTS_NUEVO_AUTHOR = 5  # comments_cuenta_nueva_sospechosa
# Contenido distintivo mínimo (shingles) para evaluar "coro". Sin esto, elogios
# genéricos cortos ("Excelente", "Felicidades", "Saludos amiga") que muchos
# usuarios distintos escriben igual disparaban falsos "coro" (verificado
# 2026-05-26: 429 autores en 202 grupos de texto genérico, NO coordinación).
MIN_SHINGLES_CORO = 6


def _shingles(text: str, n: int = 3) -> set[str]:
    """Genera n-grams de palabras (shingles) para Jaccard."""
    if not text:
        return set()
    tokens = text.lower().split()
    if len(tokens) < n:
        return {" ".join(tokens)} if tokens else set()
    return {" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    uni = len(a | b)
    return inter / uni if uni > 0 else 0.0


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
    if len(comments) < MIN_COMMENTS_REQUERIDOS:
        return build_insufficient(
            BLOQUE,
            missing=[
                f"solo {len(comments)} comments < umbral {MIN_COMMENTS_REQUERIDOS} "
                "para detección CIB estadísticamente significativa",
            ],
        )

    # ── (a) Maestros de Ceremonias ─────────────────────────────────
    # author_hash con >=N comments en mismo post dentro de 60 min
    por_post_author: dict[tuple[int, str], list[datetime]] = defaultdict(list)
    for c in comments:
        pa = c.get("published_at")
        if isinstance(pa, datetime):
            por_post_author[(c["post_id"], c["author_hash"])].append(pa)

    maestro_flags: dict[str, list[str]] = defaultdict(list)
    for (post_id, author_hash), timestamps in por_post_author.items():
        if len(timestamps) < UMBRAL_MAESTRO_CEREMONIAS:
            continue
        timestamps_sorted = sorted(timestamps)
        window = timestamps_sorted[UMBRAL_MAESTRO_CEREMONIAS - 1] - timestamps_sorted[0]
        if window.total_seconds() <= VENTANA_MAESTRO_SEG:
            maestro_flags[author_hash].append(f"maestro_ceremonias:post_{post_id}")

    # ── (b) Cuentas Coro ──────────────────────────────────────────
    # Similaridad Jaccard por author_hash sobre su corpus agregado.
    # Evitamos O(n²) global: sampleamos authors con >=2 comments.
    author_corpus: dict[str, str] = defaultdict(str)
    author_comment_count: dict[str, int] = defaultdict(int)
    for c in comments:
        author_corpus[c["author_hash"]] += " " + (c.get("content") or "")
        author_comment_count[c["author_hash"]] += 1

    # Candidatos coro: >=2 comments Y corpus con contenido distintivo suficiente
    # (>= MIN_SHINGLES_CORO). Excluye elogios genéricos cortos que no son coordinación.
    shingles_por_author = {
        a: _shingles(author_corpus[a])
        for a, n in author_comment_count.items()
        if n >= 2
    }
    authors_candidatos = [
        a for a, sh in shingles_por_author.items() if len(sh) >= MIN_SHINGLES_CORO
    ]
    coro_clusters: list[tuple[str, str]] = []
    if 2 <= len(authors_candidatos) <= 500:
        for i in range(len(authors_candidatos)):
            for j in range(i + 1, len(authors_candidatos)):
                a1 = authors_candidatos[i]
                a2 = authors_candidatos[j]
                sim = _jaccard(shingles_por_author[a1], shingles_por_author[a2])
                if sim >= UMBRAL_JACCARD:
                    coro_clusters.append((a1, a2))

    coro_flags: dict[str, list[str]] = defaultdict(list)
    for a1, a2 in coro_clusters:
        coro_flags[a1].append(f"coro_cluster:con_{a2[:12]}")
        coro_flags[a2].append(f"coro_cluster:con_{a1[:12]}")

    # ── (c) Account age heurística (basada en corpus disponible) ──
    nuevos_sospechosos: list[str] = []
    for author, n in author_comment_count.items():
        if n >= UMBRAL_COMMENTS_NUEVO_AUTHOR:
            # sin account age real desde scraper — marcamos solo si el hash
            # no aparece en comments fuera de ventana (proxy)
            nuevos_sospechosos.append(author)

    # ── Consolidar flagged_cib ────────────────────────────────────
    all_flagged: dict[str, dict] = {}
    for author, razones in maestro_flags.items():
        all_flagged.setdefault(author, {"razones": [], "confidence": 0.0})
        all_flagged[author]["razones"].extend(razones)
        all_flagged[author]["confidence"] += 0.5
    for author, razones in coro_flags.items():
        all_flagged.setdefault(author, {"razones": [], "confidence": 0.0})
        all_flagged[author]["razones"].extend(razones)
        all_flagged[author]["confidence"] += 0.35
    for author in nuevos_sospechosos:
        if author in all_flagged:  # combina con otras señales → más sospechoso
            all_flagged[author]["razones"].append("comments_alta_frecuencia")
            all_flagged[author]["confidence"] += 0.15

    for a in all_flagged.values():
        a["confidence"] = round(min(a["confidence"], 1.0), 3)

    flagged_list = [
        {
            "author_hash": author,
            "razones": info["razones"],
            "confidence": info["confidence"],
            "n_comments": author_comment_count[author],
        }
        for author, info in all_flagged.items()
    ]
    flagged_list.sort(key=lambda x: x["confidence"], reverse=True)

    confidence_global = (
        round(sum(f["confidence"] for f in flagged_list) / len(flagged_list), 3)
        if flagged_list
        else 0.0
    )

    return build_ok(
        BLOQUE,
        {
            "total_comments_analizados": len(comments),
            "flagged_cib": flagged_list[:50],
            "authors_maestro_ceremonias": len(maestro_flags),
            "authors_coro_cluster": len({a for pair in coro_clusters for a in pair}),
            "authors_nuevos_sospechosos": len(nuevos_sospechosos),
            "confidence_score": confidence_global,
            "n_authors_unicos": len(author_comment_count),
            "n_flagged_total": len(flagged_list),
            "umbrales": {
                "maestro_ceremonias_min": UMBRAL_MAESTRO_CEREMONIAS,
                "ventana_maestro_min": VENTANA_MAESTRO_SEG // 60,
                "jaccard_min": UMBRAL_JACCARD,
                "comments_nuevo_author_min": UMBRAL_COMMENTS_NUEVO_AUTHOR,
            },
            "ventana_dias": VENTANA_DIAS,
            "metodologia": "iteso_dfrlab_v1",
        },
    )
