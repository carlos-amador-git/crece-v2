"""Índice de Aceptación (IA) por publicación.

Tres capas viables free-tier:
 - Expansión: engagers_externos / engagers_totales (inferido de authors nuevos vs previos)
 - Aprobación: (pos_comments + celebratorio + solidario) / total
 - Rechazo: (neg_comments + ataque + critico) / total

LFPDPPP: solo usamos author_hash, nunca PII crudo.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter()


class IAScores(BaseModel):
    post_id: int
    platform_post_id: str
    total_comments: int
    aprobacion_pct: float
    rechazo_pct: float
    neutral_pct: float
    expansion_pct: float  # % authors que no habían comentado antes
    total_likes_on_comments: int
    unique_authors: int
    tono_breakdown: dict[str, int]
    confidence: str  # low/medium/high según volumen


@router.get("/posts/{post_id}/ia", response_model=IAScores)
async def get_ia_por_post(
    post_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
) -> IAScores:
    post_row = (await db.execute(
        text("SELECT id, platform_post_id, profile_id FROM social_posts WHERE id = :id"),
        {"id": post_id},
    )).first()
    if not post_row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Post no existe")

    scores_sql = text("""
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE nlp_polaridad = 1) AS pos,
            COUNT(*) FILTER (WHERE nlp_polaridad = -1) AS neg,
            COUNT(*) FILTER (WHERE nlp_polaridad = 0) AS neu,
            COUNT(DISTINCT author_hash) AS unique_authors,
            COALESCE(SUM(likes), 0) AS likes_total
        FROM social_comments
        WHERE parent_post_id = :pid
          AND nlp_model_version IS NOT NULL
    """)
    s = (await db.execute(scores_sql, {"pid": post_id})).first()
    total = s[0] or 0

    if total == 0:
        return IAScores(
            post_id=post_id,
            platform_post_id=post_row[1],
            total_comments=0,
            aprobacion_pct=0.0,
            rechazo_pct=0.0,
            neutral_pct=0.0,
            expansion_pct=0.0,
            total_likes_on_comments=0,
            unique_authors=0,
            tono_breakdown={},
            confidence="none",
        )

    aprobacion_pct = round(100.0 * s[1] / total, 1)
    rechazo_pct = round(100.0 * s[2] / total, 1)
    neutral_pct = round(100.0 * s[3] / total, 1)

    expansion_sql = text("""
        WITH current_authors AS (
            SELECT DISTINCT author_hash FROM social_comments WHERE parent_post_id = :pid
        ),
        historical_authors AS (
            SELECT DISTINCT c.author_hash
            FROM social_comments c
            JOIN social_posts p ON p.id = c.parent_post_id
            WHERE p.profile_id = :profile_id
              AND c.parent_post_id != :pid
              AND c.published_at < (SELECT MIN(published_at) FROM social_comments WHERE parent_post_id = :pid)
        )
        SELECT
            (SELECT COUNT(*) FROM current_authors) AS n_current,
            (SELECT COUNT(*) FROM current_authors WHERE author_hash NOT IN (SELECT author_hash FROM historical_authors)) AS n_new
    """)
    ex_row = (await db.execute(expansion_sql, {"pid": post_id, "profile_id": post_row[2]})).first()
    expansion_pct = round(100.0 * (ex_row[1] or 0) / (ex_row[0] or 1), 1)

    tono_sql = text("""
        SELECT nlp_tono, COUNT(*)
        FROM social_comments
        WHERE parent_post_id = :pid AND nlp_tono IS NOT NULL
        GROUP BY nlp_tono
    """)
    tono_rows = (await db.execute(tono_sql, {"pid": post_id})).fetchall()
    tono_breakdown = {r[0]: r[1] for r in tono_rows}

    confidence = "low" if total < 20 else ("medium" if total < 100 else "high")

    return IAScores(
        post_id=post_id,
        platform_post_id=post_row[1],
        total_comments=total,
        aprobacion_pct=aprobacion_pct,
        rechazo_pct=rechazo_pct,
        neutral_pct=neutral_pct,
        expansion_pct=expansion_pct,
        total_likes_on_comments=s[5] or 0,
        unique_authors=s[4] or 0,
        tono_breakdown=tono_breakdown,
        confidence=confidence,
    )


class IADirigenteSummary(BaseModel):
    dirigente_id: int
    posts_con_ia: int
    aprobacion_promedio: float
    rechazo_promedio: float
    expansion_promedio: float
    top_aprobacion: list[dict]
    top_rechazo: list[dict]


@router.get("/dirigentes/{dirigente_id}/ia-summary", response_model=IADirigenteSummary)
async def get_ia_summary_dirigente(
    dirigente_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
) -> IADirigenteSummary:
    sql = text("""
        WITH post_scores AS (
            SELECT
                p.id AS post_id,
                p.platform_post_id,
                substring(p.content, 1, 80) AS snippet,
                COUNT(c.id) AS total,
                100.0 * COUNT(c.id) FILTER (WHERE c.nlp_polaridad = 1) / NULLIF(COUNT(c.id), 0) AS aprobacion,
                100.0 * COUNT(c.id) FILTER (WHERE c.nlp_polaridad = -1) / NULLIF(COUNT(c.id), 0) AS rechazo
            FROM social_posts p
            JOIN social_profiles sp ON sp.id = p.profile_id
            JOIN social_comments c ON c.parent_post_id = p.id AND c.nlp_model_version IS NOT NULL
            WHERE sp.dirigente_id = :did
            GROUP BY p.id, p.platform_post_id, p.content
            HAVING COUNT(c.id) >= 5
        )
        SELECT
            COUNT(*) AS posts_con_ia,
            COALESCE(AVG(aprobacion), 0) AS apr_avg,
            COALESCE(AVG(rechazo), 0) AS rej_avg
        FROM post_scores
    """)
    summary = (await db.execute(sql, {"did": dirigente_id})).first()

    top_apr_sql = text("""
        SELECT p.id, p.platform_post_id, substring(p.content, 1, 100) AS snippet,
            COUNT(c.id) AS n,
            100.0 * COUNT(c.id) FILTER (WHERE c.nlp_polaridad = 1) / NULLIF(COUNT(c.id), 0) AS apr
        FROM social_posts p
        JOIN social_profiles sp ON sp.id = p.profile_id
        JOIN social_comments c ON c.parent_post_id = p.id AND c.nlp_model_version IS NOT NULL
        WHERE sp.dirigente_id = :did
        GROUP BY p.id
        HAVING COUNT(c.id) >= 5
        ORDER BY apr DESC NULLS LAST
        LIMIT 3
    """)
    top_apr = [
        {"post_id": r[0], "platform_post_id": r[1], "snippet": r[2], "n_comments": r[3], "aprobacion_pct": round(r[4] or 0, 1)}
        for r in (await db.execute(top_apr_sql, {"did": dirigente_id})).fetchall()
    ]

    top_rej_sql = text("""
        SELECT p.id, p.platform_post_id, substring(p.content, 1, 100) AS snippet,
            COUNT(c.id) AS n,
            100.0 * COUNT(c.id) FILTER (WHERE c.nlp_polaridad = -1) / NULLIF(COUNT(c.id), 0) AS rej
        FROM social_posts p
        JOIN social_profiles sp ON sp.id = p.profile_id
        JOIN social_comments c ON c.parent_post_id = p.id AND c.nlp_model_version IS NOT NULL
        WHERE sp.dirigente_id = :did
        GROUP BY p.id
        HAVING COUNT(c.id) >= 5
        ORDER BY rej DESC NULLS LAST
        LIMIT 3
    """)
    top_rej = [
        {"post_id": r[0], "platform_post_id": r[1], "snippet": r[2], "n_comments": r[3], "rechazo_pct": round(r[4] or 0, 1)}
        for r in (await db.execute(top_rej_sql, {"did": dirigente_id})).fetchall()
    ]

    return IADirigenteSummary(
        dirigente_id=dirigente_id,
        posts_con_ia=summary[0] or 0,
        aprobacion_promedio=round(summary[1] or 0, 1),
        rechazo_promedio=round(summary[2] or 0, 1),
        expansion_promedio=0.0,  # Calcular cuando haya más data histórica
        top_aprobacion=top_apr,
        top_rechazo=top_rej,
    )
