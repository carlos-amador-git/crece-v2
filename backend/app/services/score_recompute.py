"""S3 · Recompute helper para score_politico (matriz v2).

Re-aplica `framework_matrix_defaults` (v1) sobre comments y posts después de
ediciones HITL · regenera agregaciones por dirigente para reportes batch.

Patrón:
- comment usa `contexto='comment_tercero'` · post usa `contexto='post_dirigente'`
- comment puede tener nlp_tono en runner-vocab antiguo (elogio/critica/...)
  o en v2-vocab directo (celebratorio/propositivo/...). El mapper v3.0.1
  maneja ambos via passthrough.
- post usa `tono_discurso` y `target_politico` que ya están en v2-vocab
  desde el clasificador LLM (no requiere mapper).

NB: las tablas `social_comments` y `social_posts` NO tienen columna
`score_politico`. La función computa y RETORNA el score · es responsabilidad
del caller (endpoint HITL S2 · job batch S7) decidir si persiste el valor
o lo usa solo para agregaciones/reportes.

Idempotencia: re-ejecutar la función no muta estado ni produce side-effects
distintos al primer call (lectura pura → score lookup).
"""
from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.nlp.matriz_v3_mapper import map_runner_to_v2

log = logging.getLogger("score_recompute")


async def _lookup_score(
    db: AsyncSession,
    *,
    rol: str,
    tono: str,
    target: str,
    contexto: str,
) -> int:
    """Lookup en framework_matrix_defaults v1. Retorna 0 si no hay match.

    NB: Retornamos 0 (no None) para mantener tipo `int` en el contrato del
    helper · permite agregaciones aritméticas sin guardas extra. El miss
    queda visible vía logging.
    """
    row = (
        await db.execute(
            text(
                """
                SELECT score_politico
                FROM framework_matrix_defaults
                WHERE version = 'v1'
                  AND rol = :rol
                  AND tono = :tono
                  AND target = :target
                  AND contexto = :contexto
                LIMIT 1
                """
            ),
            {"rol": rol, "tono": tono, "target": target, "contexto": contexto},
        )
    ).first()
    if row is None:
        log.debug(
            "score miss · rol=%s tono=%s target=%s contexto=%s",
            rol, tono, target, contexto,
        )
        return 0
    return int(row[0])


async def recompute_score_comment(db: AsyncSession, comment_id: int) -> int:
    """Re-aplica matriz v2 sobre 1 comment.

    Pasos:
    1. SELECT comment + post + profile + dirigente.rol_politico
    2. Si nlp_tono está en runner vocab → mapper v3.0.1 → tono_v2, target_v2.
       Si ya está en v2 vocab → mapper actúa como passthrough idempotente.
    3. Lookup en framework_matrix_defaults
       (rol, tono, target, contexto='comment_tercero')
    4. Retorna score (0 si miss).

    Args:
        db: sesión async SQLAlchemy
        comment_id: PK de social_comments

    Returns:
        score politico int · 0 si comment no existe, no tiene NLP, o no hay
        match en la matriz.
    """
    row = (
        await db.execute(
            text(
                """
                SELECT
                    sc.nlp_tono,
                    sc.nlp_target,
                    sc.content,
                    d.rol_politico
                FROM social_comments sc
                JOIN social_posts sp     ON sp.id = sc.parent_post_id
                JOIN social_profiles pr  ON pr.id = sp.profile_id
                JOIN dirigentes d        ON d.id = pr.dirigente_id
                WHERE sc.id = :cid
                LIMIT 1
                """
            ),
            {"cid": comment_id},
        )
    ).first()

    if row is None:
        log.warning("comment_id=%s no existe", comment_id)
        return 0

    nlp_tono, nlp_target, content, rol = row
    if not nlp_tono or not nlp_target or not rol:
        log.debug("comment_id=%s sin NLP populated o dirigente sin rol", comment_id)
        return 0

    # Mapper es idempotente para vocab v2 (passthrough v3.0.1)
    mapper = map_runner_to_v2(
        nlp_tono, nlp_target,
        comment_text=content or "",
        is_self_authored=False,  # post-level autopromo no aplica a comment
    )

    return await _lookup_score(
        db,
        rol=rol,
        tono=mapper.tono_v2,
        target=mapper.target_v2,
        contexto="comment_tercero",
    )


async def recompute_score_post(db: AsyncSession, post_id: int) -> int:
    """Re-aplica matriz v2 sobre 1 post (contexto=post_dirigente).

    A diferencia de comment, post.tono_discurso y post.target_politico ya
    están en vocab v2 directo (clasificador LLM los emite así desde D-23-G).
    No requiere mapper.

    Args:
        db: sesión async SQLAlchemy
        post_id: PK de social_posts

    Returns:
        score politico int · 0 si post no existe, no tiene clasificación, o no
        hay match en la matriz.
    """
    row = (
        await db.execute(
            text(
                """
                SELECT
                    sp.tono_discurso,
                    sp.target_politico,
                    d.rol_politico
                FROM social_posts sp
                JOIN social_profiles pr ON pr.id = sp.profile_id
                JOIN dirigentes d       ON d.id = pr.dirigente_id
                WHERE sp.id = :pid
                LIMIT 1
                """
            ),
            {"pid": post_id},
        )
    ).first()

    if row is None:
        log.warning("post_id=%s no existe", post_id)
        return 0

    tono, target, rol = row
    if not tono or not target or not rol:
        log.debug("post_id=%s sin clasificación o dirigente sin rol", post_id)
        return 0

    # Defensa: target_politico='no_determinado' (D-23-G fallback) no se evalúa
    if target in {"no_determinado", ""}:
        return 0

    return await _lookup_score(
        db,
        rol=rol,
        tono=tono,
        target=target,
        contexto="post_dirigente",
    )


async def recompute_dirigente_aggregate(
    db: AsyncSession, dirigente_id: int,
) -> dict:
    """Recalcula agregaciones de score por dirigente sobre todos sus comments.

    Cuenta comments con score>0, score<0, score=0 (incluye misses) usando
    `recompute_score_comment` por cada comment del dirigente que tenga NLP.

    NB: NO existe tabla `actividad_politica_alineada` en BD · ese KPI se
    computa on-the-fly en `app.services.actividad_alineada.compute_actividad_alineada`.
    Esta función solo retorna conteos en memoria · útil para reportes batch
    (S7 · F-NLP-3 recompute global), no para edit individual.

    Args:
        db: sesión async SQLAlchemy
        dirigente_id: PK de dirigentes

    Returns:
        dict con:
        - dirigente_id
        - total_comments_evaluados (con NLP populated)
        - score_positivo: count score > 0
        - score_negativo: count score < 0
        - score_cero: count score == 0 (incluye misses en matriz)
        - score_promedio: float · avg de todos los scores
    """
    rows = (
        await db.execute(
            text(
                """
                SELECT sc.id
                FROM social_comments sc
                JOIN social_posts sp     ON sp.id = sc.parent_post_id
                JOIN social_profiles pr  ON pr.id = sp.profile_id
                WHERE pr.dirigente_id = :did
                  AND sc.nlp_tono IS NOT NULL
                  AND sc.nlp_target IS NOT NULL
                """
            ),
            {"did": dirigente_id},
        )
    ).all()

    comment_ids = [r[0] for r in rows]
    pos = neg = zero = 0
    total_score = 0
    for cid in comment_ids:
        s = await recompute_score_comment(db, cid)
        if s > 0:
            pos += 1
        elif s < 0:
            neg += 1
        else:
            zero += 1
        total_score += s

    n = len(comment_ids)
    avg = (total_score / n) if n else 0.0

    return {
        "dirigente_id": dirigente_id,
        "total_comments_evaluados": n,
        "score_positivo": pos,
        "score_negativo": neg,
        "score_cero": zero,
        "score_promedio": round(avg, 4),
    }
