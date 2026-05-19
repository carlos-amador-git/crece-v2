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


def _require_tenant_access(user: User, post_org_id: int | None) -> None:
    """Admin puede ver cualquier org; viewer solo su propia org."""
    if user.role == "admin":
        return
    if post_org_id is None or user.org_id != post_org_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Sin acceso a data de otra organización",
        )


@router.get("/posts/{post_id}/ia", response_model=IAScores)
async def get_ia_por_post(
    post_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> IAScores:
    post_row = (await db.execute(
        text("""
            SELECT p.id, p.platform_post_id, p.profile_id, d.org_id
            FROM social_posts p
            JOIN social_profiles sp ON sp.id = p.profile_id
            JOIN dirigentes d ON d.id = sp.dirigente_id
            WHERE p.id = :id
        """),
        {"id": post_id},
    )).first()
    if not post_row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Post no existe")
    _require_tenant_access(current_user, post_row[3])

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
    current_user: Annotated[User, Depends(get_current_user)],
) -> IADirigenteSummary:
    d_row = (await db.execute(
        text("SELECT org_id FROM dirigentes WHERE id = :id"),
        {"id": dirigente_id},
    )).first()
    if not d_row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dirigente no existe")
    _require_tenant_access(current_user, d_row[0])

    # KPI agregados: porcentaje sobre TODOS los comments analizados — paridad
    # con /aceptacion/overview (que también calcula así). El filtro HAVING >= 5
    # se aplica SOLO a los rankings (top_aprobacion / top_rechazo) para evitar
    # posts con poca señal en el ranking.
    # Antes (D-OVERVIEW-IA-SUMMARY-MISMATCH-1, 2026-05-15): se usaba un AVG de
    # promedios sobre posts con >=5 comments → totales no cuadraban con overview.
    sql = text("""
        SELECT
            COUNT(DISTINCT p.id) AS posts_con_ia,
            COALESCE(100.0 * COUNT(c.id) FILTER (WHERE c.nlp_polaridad = 1)
                     / NULLIF(COUNT(c.id), 0), 0) AS apr_avg,
            COALESCE(100.0 * COUNT(c.id) FILTER (WHERE c.nlp_polaridad = -1)
                     / NULLIF(COUNT(c.id), 0), 0) AS rej_avg
        FROM social_posts p
        JOIN social_profiles sp ON sp.id = p.profile_id
        JOIN social_comments c ON c.parent_post_id = p.id AND c.nlp_model_version IS NOT NULL
        WHERE sp.dirigente_id = :did
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


class AceptacionOverviewRow(BaseModel):
    dirigente_id: int
    full_name: str
    rol_politico: str | None
    total_followers: int
    unique_commenters: int
    total_comments: int
    pct_activados: float
    pct_fantasma: float
    pct_aprobacion: float
    pct_rechazo: float
    pct_neutral: float


class AceptacionOverview(BaseModel):
    dirigentes: list[AceptacionOverviewRow]
    total_corpus_comments: int
    metodologia: str


@router.get("/aceptacion/overview", response_model=AceptacionOverview)
async def get_aceptacion_overview(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AceptacionOverview:
    """Overview agregado por dirigente: activación, fantasmas y polaridad.

    Scope (Option A — paridad con /fantasmas-por-plataforma · 043a4eb):
      - admin → sin filtro
      - viewer con dirigente_id → solo SU dirigente
      - resto (analyst, viewer sin dirigente) → todos los de su org
    """
    org_filter = ""
    params: dict = {}
    if current_user.role == "admin":
        pass
    elif current_user.role == "viewer" and current_user.dirigente_id:
        org_filter = "WHERE d.id = :dirigente_id"
        params["dirigente_id"] = current_user.dirigente_id
    else:
        if not current_user.org_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Sin org asignada")
        org_filter = "WHERE d.org_id = :org_id"
        params["org_id"] = current_user.org_id

    sql = text(f"""
        WITH eng AS (
            SELECT d.id, d.full_name, d.rol_politico,
                   COUNT(DISTINCT sc.author_hash) AS unique_commenters,
                   COUNT(sc.id) AS total_comments,
                   100.0 * COUNT(sc.id) FILTER (WHERE sc.nlp_polaridad = 1) / NULLIF(COUNT(sc.id), 0) AS pct_aprobacion,
                   100.0 * COUNT(sc.id) FILTER (WHERE sc.nlp_polaridad = -1) / NULLIF(COUNT(sc.id), 0) AS pct_rechazo,
                   100.0 * COUNT(sc.id) FILTER (WHERE sc.nlp_polaridad = 0) / NULLIF(COUNT(sc.id), 0) AS pct_neutral
            FROM dirigentes d
            LEFT JOIN social_profiles p ON p.dirigente_id = d.id
            LEFT JOIN social_posts sp ON sp.profile_id = p.id
            LEFT JOIN social_comments sc ON sc.parent_post_id = sp.id
                AND sc.nlp_model_version IS NOT NULL
            {org_filter}
            GROUP BY d.id, d.full_name, d.rol_politico
        ),
        fol AS (
            SELECT dirigente_id, SUM(followers_count) AS total_followers
            FROM social_profiles
            GROUP BY dirigente_id
        )
        SELECT eng.id, eng.full_name, eng.rol_politico,
               COALESCE(fol.total_followers, 0) AS total_followers,
               eng.unique_commenters,
               eng.total_comments,
               CASE WHEN COALESCE(fol.total_followers, 0) > 0
                    THEN ROUND(100.0 * eng.unique_commenters / fol.total_followers, 2)
                    ELSE 0 END AS pct_activados,
               CASE WHEN COALESCE(fol.total_followers, 0) > 0
                    THEN ROUND(100.0 * (1 - eng.unique_commenters::decimal / fol.total_followers), 2)
                    ELSE 0 END AS pct_fantasma,
               ROUND(COALESCE(eng.pct_aprobacion, 0), 1),
               ROUND(COALESCE(eng.pct_rechazo, 0), 1),
               ROUND(COALESCE(eng.pct_neutral, 0), 1)
        FROM eng
        LEFT JOIN fol ON fol.dirigente_id = eng.id
        ORDER BY eng.id
    """)
    rows = (await db.execute(sql, params)).fetchall()
    dirigentes = [
        AceptacionOverviewRow(
            dirigente_id=r[0], full_name=r[1], rol_politico=r[2],
            total_followers=int(r[3]), unique_commenters=int(r[4] or 0),
            total_comments=int(r[5] or 0),
            pct_activados=float(r[6] or 0), pct_fantasma=float(r[7] or 0),
            pct_aprobacion=float(r[8] or 0), pct_rechazo=float(r[9] or 0),
            pct_neutral=float(r[10] or 0),
        )
        for r in rows
    ]
    total_corpus = sum(d.total_comments for d in dirigentes)

    return AceptacionOverview(
        dirigentes=dirigentes,
        total_corpus_comments=total_corpus,
        metodologia=(
            "Activación = unique_commenters / total_followers. Fantasma = 1 - activación. "
            "Polaridad calculada con matriz v2 (53 reglas) sobre comments con nlp_model_version='comment-framework-v2'. "
            "Baseline industria: 1-3% activación saludable. Limitación: solo comments como señal, no likes."
        ),
    )


# ──────────────────────────────────────────────────────────────────────────
# Fantasmas-por-plataforma
# Sister endpoint del overview: misma fórmula activados/fantasmas pero
# desglosado por (dirigente, plataforma) en vez de agregado por dirigente.
# Frontend: useFantasmasPorPlataforma()
# ──────────────────────────────────────────────────────────────────────────
class _PlatformFantasmaRow(BaseModel):
    platform: str
    followers: int
    unique_commenters: int
    pct_activados: float
    pct_fantasma: float


class _DirigentePlatformFantasmas(BaseModel):
    dirigente_id: int
    full_name: str
    platforms: list[_PlatformFantasmaRow]


@router.get("/aceptacion/fantasmas-por-plataforma", response_model=list[_DirigentePlatformFantasmas])
async def get_fantasmas_por_plataforma(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[_DirigentePlatformFantasmas]:
    """Activación/fantasmas por (dirigente, plataforma).

    Mismo cálculo que /aceptacion/overview pero desagregado por plataforma.
    Permite al UI mostrar dónde el dirigente tiene mejor/peor engagement.
    """
    extra_filter = ""
    params: dict = {}
    if current_user.role == "admin":
        pass
    elif current_user.role == "viewer" and current_user.dirigente_id:
        extra_filter = "AND d.id = :dirigente_id"
        params["dirigente_id"] = current_user.dirigente_id
    else:
        if not current_user.org_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Sin org asignada")
        extra_filter = "AND d.org_id = :org_id"
        params["org_id"] = current_user.org_id

    sql = text(f"""
        SELECT d.id, d.full_name, p.platform::text AS platform,
               p.followers_count AS followers,
               COUNT(DISTINCT sc.author_hash) AS unique_commenters
        FROM dirigentes d
        JOIN social_profiles p ON p.dirigente_id = d.id
        LEFT JOIN social_posts sp ON sp.profile_id = p.id
        LEFT JOIN social_comments sc ON sc.parent_post_id = sp.id
            AND sc.nlp_model_version IS NOT NULL
        WHERE p.followers_count > 0 {extra_filter}
        GROUP BY d.id, d.full_name, p.platform, p.followers_count
        ORDER BY d.id, p.platform
    """)
    rows = (await db.execute(sql, params)).fetchall()

    grouped: dict[int, _DirigentePlatformFantasmas] = {}
    for r in rows:
        d_id, full_name, platform, followers, unique_commenters = r
        followers = int(followers or 0)
        unique_commenters = int(unique_commenters or 0)
        pct_act = round(100.0 * unique_commenters / followers, 2) if followers > 0 else 0.0
        pct_fan = round(100.0 - pct_act, 2) if followers > 0 else 0.0
        if d_id not in grouped:
            grouped[d_id] = _DirigentePlatformFantasmas(
                dirigente_id=d_id, full_name=full_name, platforms=[]
            )
        grouped[d_id].platforms.append(_PlatformFantasmaRow(
            platform=platform.lower(),
            followers=followers,
            unique_commenters=unique_commenters,
            pct_activados=pct_act,
            pct_fantasma=pct_fan,
        ))

    return list(grouped.values())
