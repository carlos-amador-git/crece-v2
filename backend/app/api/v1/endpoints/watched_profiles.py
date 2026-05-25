"""Watched profiles — perfiles bajo observación nominada del cliente.

Origen: PLAN-2026-05-14-watchlist-saymi.md · Fase 2.

Endpoints expuestos en /api/v1/aceptacion/watched-profiles:
- GET    /                              — listar (filtros: platform, source, dirigente_id, has_engagement)
- POST   /                              — crear watched (precomputa author_hash)
- PATCH  /{id}                          — actualizar tags/notes/is_active
- DELETE /{id}                          — soft delete (is_active=false) o hard delete con ?hard=true
- GET    /{id}/engagement               — comments + likes detectados de este watched
- GET    /summary?dirigente_id=X        — métricas agregadas para el tab UI
- GET    /suggestions?dirigente_id=X    — comentaristas frecuentes no watchlisted
"""
from __future__ import annotations

import hashlib
import os
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter()

SALT = os.environ.get("COMMENT_AUTHOR_SALT", "crece-v2-lfpdppp-salt-2026")

PLATFORMS = ("TWITTER", "INSTAGRAM", "FACEBOOK", "TIKTOK", "YOUTUBE", "BLUESKY", "THREADS", "TELEGRAM")
SOURCES = ("cliente_seed", "manual", "auto_suggested", "competidor")


def _hash(platform: str, external_id: str) -> str:
    return hashlib.sha256(f"{platform}:{external_id}:{SALT}".encode()).hexdigest()


# ── Schemas ──────────────────────────────────────────────────────────

class WatchedProfileCreate(BaseModel):
    dirigente_observador_id: int
    platform: Literal["TWITTER", "INSTAGRAM", "FACEBOOK", "TIKTOK", "YOUTUBE", "BLUESKY", "THREADS", "TELEGRAM"]
    profile_external_id: str = Field(min_length=1, max_length=100)
    profile_handle: str | None = Field(default=None, max_length=255)
    profile_url: str | None = Field(default=None, max_length=500)
    display_name: str | None = Field(default=None, max_length=255)
    avatar_url: str | None = None
    source: Literal["cliente_seed", "manual", "auto_suggested", "competidor"] = "manual"
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None


class WatchedProfileUpdate(BaseModel):
    profile_handle: str | None = Field(default=None, max_length=255)
    display_name: str | None = Field(default=None, max_length=255)
    tags: list[str] | None = None
    notes: str | None = None
    is_active: bool | None = None


class WatchedProfileOut(BaseModel):
    id: int
    dirigente_observador_id: int
    platform: str
    profile_external_id: str
    profile_handle: str | None
    profile_url: str | None
    display_name: str | None
    avatar_url: str | None
    source: str
    tags: list[str]
    notes: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    n_comments: int = 0
    n_likes: int = 0
    last_engagement: datetime | None = None


class WatchedSummary(BaseModel):
    dirigente_id: int
    total_watched: int
    by_source: dict[str, int]
    by_platform: dict[str, int]
    activos_engagement: int  # con ≥1 comment o ≥1 like
    inactivos: int
    comments_total: int
    likes_total: int
    auto_suggested_pending: int  # contemplado para futuro


class EngagementEntry(BaseModel):
    type: Literal["comment", "like"]
    post_id: int
    platform_post_id: str
    post_url: str | None
    post_published_at: datetime | None
    content: str | None  # solo en comments
    reaction_type: str | None  # solo en likes
    detected_at: datetime
    source: str  # 'scraper'/'visual_evidence'/'oauth'


# ── Helpers ──────────────────────────────────────────────────────────

def _check_org(user: User, dirigente_org_id: int | None) -> None:
    if user.role == "admin":
        return
    if dirigente_org_id is None or user.org_id != dirigente_org_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Sin acceso a esta organización")


async def _assert_dirigente_access(
    db: AsyncSession, user: User, dirigente_id: int
) -> int:
    """Resuelve dirigente.org_id y aplica _check_org. Retorna org_id si OK.

    Raises 404 si el dirigente no existe, 403 si el user no pertenece al org.
    """
    row = (
        await db.execute(
            text("SELECT org_id FROM dirigentes WHERE id = :did"),
            {"did": dirigente_id},
        )
    ).first()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dirigente no existe")
    _check_org(user, row[0])
    return row[0]


async def _assert_watched_access(
    db: AsyncSession, user: User, watched_id: int
) -> tuple[str, int]:
    """Resuelve watched_profile → (author_hash, dirigente_observador_id) con check de org.

    Raises 404 si el watched no existe, 403 si el user no pertenece al org.
    """
    row = (
        await db.execute(
            text(
                """
                SELECT wp.author_hash, wp.dirigente_observador_id, d.org_id
                FROM watched_profiles wp
                JOIN dirigentes d ON d.id = wp.dirigente_observador_id
                WHERE wp.id = :wid
                """
            ),
            {"wid": watched_id},
        )
    ).first()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Watched profile no existe")
    _check_org(user, row[2])
    return row[0], row[1]


# ── Endpoints ────────────────────────────────────────────────────────

@router.get("/", response_model=list[WatchedProfileOut])
async def list_watched(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    dirigente_id: int | None = None,
    platform: str | None = None,
    source: str | None = None,
    tag: str | None = None,
    active_only: bool = True,
    has_engagement: bool | None = None,
    limit: int = Query(default=200, le=500),
):
    """Lista watched profiles con métricas agregadas inline (n_comments, n_likes, last_engagement).

    Scope multi-tenant:
    - Si `dirigente_id` se especifica → validar que pertenece al org del user (o admin).
    - Si NO se especifica → admin ve todo, resto solo su `user.org_id`.
    """
    where = ["1=1"]
    params: dict = {"limit": limit}
    if dirigente_id is not None:
        await _assert_dirigente_access(db, user, dirigente_id)
        where.append("wp.dirigente_observador_id = :did")
        params["did"] = dirigente_id
    elif user.role != "admin":
        where.append("wp.org_id = :user_org")
        params["user_org"] = user.org_id
    if platform:
        where.append("wp.platform = :plat")
        params["plat"] = platform.upper()
    if source:
        where.append("wp.source = :src")
        params["src"] = source
    if tag:
        where.append("wp.tags ? :tag")
        params["tag"] = tag
    if active_only:
        where.append("wp.is_active = true")

    sql = f"""
        SELECT
          wp.id, wp.dirigente_observador_id, wp.platform, wp.profile_external_id,
          wp.profile_handle, wp.profile_url, wp.display_name, wp.avatar_url,
          wp.source, wp.tags, wp.notes, wp.is_active,
          wp.created_at, wp.updated_at,
          COALESCE(c.n_comments, 0) AS n_comments,
          COALESCE(l.n_likes, 0) AS n_likes,
          GREATEST(c.last_comment, l.last_like) AS last_engagement
        FROM watched_profiles wp
        LEFT JOIN LATERAL (
          SELECT COUNT(*) AS n_comments, MAX(sc.published_at) AS last_comment
          FROM social_comments sc
          JOIN social_posts sp ON sp.id = sc.parent_post_id
          JOIN social_profiles spr ON spr.id = sp.profile_id
          WHERE sc.author_hash = wp.author_hash
            AND spr.dirigente_id = wp.dirigente_observador_id
        ) c ON true
        LEFT JOIN LATERAL (
          SELECT COUNT(*) AS n_likes, MAX(wle.detected_at) AS last_like
          FROM watched_like_events wle
          WHERE wle.watched_profile_id = wp.id
        ) l ON true
        WHERE {" AND ".join(where)}
        ORDER BY GREATEST(c.last_comment, l.last_like) DESC NULLS LAST, wp.id
        LIMIT :limit
    """
    rows = (await db.execute(text(sql), params)).mappings().all()

    if has_engagement is True:
        rows = [r for r in rows if (r["n_comments"] or 0) + (r["n_likes"] or 0) > 0]
    elif has_engagement is False:
        rows = [r for r in rows if (r["n_comments"] or 0) + (r["n_likes"] or 0) == 0]

    return [WatchedProfileOut(**dict(r)) for r in rows]


@router.post("/", response_model=WatchedProfileOut, status_code=status.HTTP_201_CREATED)
async def create_watched(
    payload: WatchedProfileCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    # validar dirigente exists + org access
    drow = (await db.execute(
        text("SELECT org_id FROM dirigentes WHERE id = :did"),
        {"did": payload.dirigente_observador_id},
    )).first()
    if not drow:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dirigente no existe")
    _check_org(user, drow[0])

    ah = _hash(payload.platform, payload.profile_external_id)
    try:
        result = await db.execute(text("""
            INSERT INTO watched_profiles
              (dirigente_observador_id, org_id, platform, profile_external_id,
               profile_handle, profile_url, display_name, avatar_url,
               source, tags, notes, author_hash, created_by)
            VALUES (:did, :org, :plat, :eid, :handle, :url, :name, :avatar,
                    :src, CAST(:tags AS jsonb), :notes, :ah, :uid)
            RETURNING id, dirigente_observador_id, platform, profile_external_id,
                      profile_handle, profile_url, display_name, avatar_url,
                      source, tags, notes, is_active, created_at, updated_at
        """), {
            "did": payload.dirigente_observador_id,
            "org": drow[0],
            "plat": payload.platform,
            "eid": payload.profile_external_id,
            "handle": payload.profile_handle,
            "url": payload.profile_url,
            "name": payload.display_name,
            "avatar": payload.avatar_url,
            "src": payload.source,
            "tags": __import__("json").dumps(payload.tags),
            "notes": payload.notes,
            "ah": ah,
            "uid": user.id,
        })
        row = result.mappings().first()
        await db.commit()
        return WatchedProfileOut(n_comments=0, n_likes=0, last_engagement=None, **dict(row))
    except Exception as e:
        await db.rollback()
        if "uq_watched_dirigente_platform_external" in str(e):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Ya existe un watched profile con esa combinación dirigente+platform+external_id",
            )
        raise


@router.patch("/{watched_id}", response_model=WatchedProfileOut)
async def update_watched(
    watched_id: int,
    payload: WatchedProfileUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    await _assert_watched_access(db, user, watched_id)
    sets, params = [], {"id": watched_id}
    if payload.profile_handle is not None:
        sets.append("profile_handle = :handle")
        params["handle"] = payload.profile_handle
    if payload.display_name is not None:
        sets.append("display_name = :name")
        params["name"] = payload.display_name
    if payload.tags is not None:
        sets.append("tags = CAST(:tags AS jsonb)")
        params["tags"] = __import__("json").dumps(payload.tags)
    if payload.notes is not None:
        sets.append("notes = :notes")
        params["notes"] = payload.notes
    if payload.is_active is not None:
        sets.append("is_active = :active")
        params["active"] = payload.is_active
    if not sets:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Sin campos para actualizar")

    sets.append("updated_at = now()")
    sql = f"UPDATE watched_profiles SET {', '.join(sets)} WHERE id = :id RETURNING id"
    res = await db.execute(text(sql), params)
    if not res.first():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Watched profile no existe")
    # S8 audit log · endpoint usa SQL raw, ORM listeners no aplican
    from app.core.audit_listeners import log_destructive_op
    changed_cols = [k for k in payload.model_dump(exclude_unset=True).keys()]
    await log_destructive_op(
        db,
        action="UPDATE",
        model="watched_profiles",
        record_id=watched_id,
        changes_summary={"changed_columns": changed_cols},
    )
    await db.commit()
    # return updated
    rows = await list_watched(db, user, dirigente_id=None, active_only=False, limit=500)
    found = next((r for r in rows if r.id == watched_id), None)
    if not found:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No se pudo recuperar el watched actualizado")
    return found


@router.delete("/{watched_id}")
async def delete_watched(
    watched_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    hard: bool = False,
):
    await _assert_watched_access(db, user, watched_id)
    if hard:
        await db.execute(text("DELETE FROM watched_profiles WHERE id = :id"), {"id": watched_id})
    else:
        await db.execute(
            text("UPDATE watched_profiles SET is_active = false, updated_at = now() WHERE id = :id"),
            {"id": watched_id},
        )
    # S8 audit log · ambos paths (hard / soft) son destructivos
    from app.core.audit_listeners import log_destructive_op
    await log_destructive_op(
        db,
        action="DELETE" if hard else "UPDATE",
        model="watched_profiles",
        record_id=watched_id,
        changes_summary=({"soft_delete": True} if not hard else None),
    )
    await db.commit()
    return {"ok": True, "hard": hard}


@router.get("/summary", response_model=WatchedSummary)
async def watched_summary(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    dirigente_id: int,
):
    """Métricas agregadas para el header del tab UI."""
    await _assert_dirigente_access(db, user, dirigente_id)
    base = await db.execute(text("""
        SELECT
          COUNT(*) AS total,
          COUNT(*) FILTER (WHERE source='cliente_seed') AS cs,
          COUNT(*) FILTER (WHERE source='manual') AS man,
          COUNT(*) FILTER (WHERE source='auto_suggested') AS asu,
          COUNT(*) FILTER (WHERE source='competidor') AS cmp,
          COUNT(*) FILTER (WHERE platform='FACEBOOK')  AS p_fb,
          COUNT(*) FILTER (WHERE platform='INSTAGRAM') AS p_ig,
          COUNT(*) FILTER (WHERE platform='TWITTER')   AS p_tw,
          COUNT(*) FILTER (WHERE platform='TIKTOK')    AS p_tt,
          COUNT(*) FILTER (WHERE platform='YOUTUBE')   AS p_yt
        FROM watched_profiles
        WHERE dirigente_observador_id = :did AND is_active = true
    """), {"did": dirigente_id})
    b = base.mappings().first()

    eng = await db.execute(text("""
        WITH cmt AS (
            SELECT wp.id, COUNT(sc.id) AS n
            FROM watched_profiles wp
            LEFT JOIN social_comments sc ON sc.author_hash = wp.author_hash
            LEFT JOIN social_posts sp ON sp.id = sc.parent_post_id
            LEFT JOIN social_profiles spr ON spr.id = sp.profile_id
              AND spr.dirigente_id = wp.dirigente_observador_id
            WHERE wp.dirigente_observador_id = :did AND wp.is_active = true
            GROUP BY wp.id
        ),
        lik AS (
            SELECT wp.id, COUNT(wle.id) AS n
            FROM watched_profiles wp
            LEFT JOIN watched_like_events wle ON wle.watched_profile_id = wp.id
            WHERE wp.dirigente_observador_id = :did AND wp.is_active = true
            GROUP BY wp.id
        )
        SELECT
          (SELECT SUM(n) FROM cmt) AS comments_total,
          (SELECT SUM(n) FROM lik) AS likes_total,
          COUNT(*) FILTER (WHERE COALESCE(c.n,0)+COALESCE(l.n,0) > 0) AS activos,
          COUNT(*) FILTER (WHERE COALESCE(c.n,0)+COALESCE(l.n,0) = 0) AS inactivos
        FROM cmt c
        FULL OUTER JOIN lik l ON l.id = c.id
    """), {"did": dirigente_id})
    e = eng.mappings().first()

    return WatchedSummary(
        dirigente_id=dirigente_id,
        total_watched=b["total"] or 0,
        by_source={"cliente_seed": b["cs"], "manual": b["man"], "auto_suggested": b["asu"], "competidor": b["cmp"]},
        by_platform={
            "FACEBOOK": b["p_fb"], "INSTAGRAM": b["p_ig"], "TWITTER": b["p_tw"],
            "TIKTOK": b["p_tt"], "YOUTUBE": b["p_yt"],
        },
        activos_engagement=e["activos"] or 0,
        inactivos=e["inactivos"] or 0,
        comments_total=e["comments_total"] or 0,
        likes_total=e["likes_total"] or 0,
        auto_suggested_pending=0,
    )


@router.get("/{watched_id}/engagement", response_model=list[EngagementEntry])
async def watched_engagement(
    watched_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(default=100, le=500),
):
    """Comments + likes detectados de este watched, ordenados por fecha."""
    ah, did = await _assert_watched_access(db, user, watched_id)

    rows_c = (await db.execute(text("""
        SELECT 'comment' AS type, sp.id AS post_id, sp.platform_post_id,
               COALESCE(sp.raw_data->>'url', sp.raw_data->>'topLevelUrl') AS post_url,
               sp.published_at AS post_published_at,
               substring(sc.content, 1, 500) AS content,
               NULL::text AS reaction_type,
               sc.published_at AS detected_at,
               sc.data_source AS source
        FROM social_comments sc
        JOIN social_posts sp ON sp.id = sc.parent_post_id
        JOIN social_profiles spr ON spr.id = sp.profile_id
        WHERE sc.author_hash = :ah AND spr.dirigente_id = :did
        ORDER BY sc.published_at DESC NULLS LAST
        LIMIT :limit
    """), {"ah": ah, "did": did, "limit": limit})).mappings().all()

    rows_l = (await db.execute(text("""
        SELECT 'like' AS type, sp.id AS post_id, sp.platform_post_id,
               COALESCE(sp.raw_data->>'url', sp.raw_data->>'topLevelUrl') AS post_url,
               sp.published_at AS post_published_at,
               NULL::text AS content,
               wle.reaction_type,
               wle.detected_at,
               wle.source
        FROM watched_like_events wle
        JOIN social_posts sp ON sp.id = wle.post_id
        WHERE wle.watched_profile_id = :wid
        ORDER BY wle.detected_at DESC
        LIMIT :limit
    """), {"wid": watched_id, "limit": limit})).mappings().all()

    combined = sorted(
        [EngagementEntry(**dict(r)) for r in list(rows_c) + list(rows_l)],
        key=lambda x: x.detected_at, reverse=True,
    )
    return combined[:limit]


@router.get("/suggestions", response_model=list[dict])
async def watched_suggestions(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    dirigente_id: int,
    min_comments: int = Query(default=2, ge=1),
    limit: int = Query(default=20, le=100),
):
    """Comentaristas frecuentes (≥min_comments) que NO están watchlisted aún.

    Sprint C: devuelve `commenter_handle` cuando esté cacheado en cualquier
    comment con ese author_hash (scrapers nuevos lo pueblan desde sc1).
    UI muestra handle si existe, hash truncado si no.
    """
    await _assert_dirigente_access(db, user, dirigente_id)
    rows = (await db.execute(text("""
        WITH watched AS (
            SELECT author_hash FROM watched_profiles
            WHERE dirigente_observador_id = :did AND is_active = true
        ),
        candidates AS (
            SELECT sc.author_hash, COUNT(*) AS n_comments,
                   MAX(sc.published_at) AS last_comment,
                   MAX(spr.platform::text) AS platform,
                   MAX(sc.commenter_handle) AS commenter_handle
            FROM social_comments sc
            JOIN social_posts sp ON sp.id = sc.parent_post_id
            JOIN social_profiles spr ON spr.id = sp.profile_id
            WHERE spr.dirigente_id = :did
              AND sc.author_hash NOT IN (SELECT author_hash FROM watched)
            GROUP BY sc.author_hash
            HAVING COUNT(*) >= :minc
        )
        SELECT author_hash, n_comments, last_comment, platform, commenter_handle
        FROM candidates
        ORDER BY n_comments DESC, last_comment DESC NULLS LAST
        LIMIT :limit
    """), {"did": dirigente_id, "minc": min_comments, "limit": limit})).mappings().all()
    return [dict(r) for r in rows]


# ── Top Fans ranking ──────────────────────────────────────────────────
# Endpoint dedicado que computa score = n_likes*1 + n_comments*2.5 en SQL
# y devuelve los top N perfiles ordenados por score DESC.
# Razón: el endpoint genérico list_watched ordena por last_engagement, lo que
# causa que batches de auto_suggested con timestamp idéntico desplacen perfiles
# de alto score fuera del LIMIT 200 antes de llegar al frontend.

class TopFanEntry(BaseModel):
    id: int
    platform: str
    profile_external_id: str
    profile_handle: str | None
    display_name: str | None
    source: str
    n_likes: int
    n_comments: int
    score: float


@router.get("/top-fans", response_model=list[TopFanEntry])
async def top_fans(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    dirigente_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    source: str | None = Query(
        default=None,
        description="cliente_seed · auto_suggested · manual · None=todos"
    ),
    platform: str | None = Query(
        default=None,
        description="FACEBOOK · INSTAGRAM · TWITTER · TIKTOK · YOUTUBE · None=todas"
    ),
):
    """Top fans ordenados por score = n_likes*1 + n_comments*2.5.

    A diferencia de list_watched (que ordena por last_engagement), este endpoint
    ordena directamente por score DESC en SQL, garantizando que los perfiles con
    más engagement siempre aparezcan sin importar cuándo fueron ingresados.
    """
    await _assert_dirigente_access(db, user, dirigente_id)

    where = ["wp.dirigente_observador_id = :did", "wp.is_active = true"]
    params: dict = {"did": dirigente_id, "limit": limit}

    if source:
        where.append("wp.source = :src")
        params["src"] = source
    if platform:
        where.append("wp.platform = :plat")
        params["plat"] = platform.upper()

    sql = f"""
        SELECT
          wp.id,
          wp.platform,
          wp.profile_external_id,
          wp.profile_handle,
          wp.display_name,
          wp.source,
          COALESCE(l.n_likes, 0)    AS n_likes,
          COALESCE(c.n_comments, 0) AS n_comments,
          COALESCE(l.n_likes, 0) * 1.0 + COALESCE(c.n_comments, 0) * 2.5 AS score
        FROM watched_profiles wp
        LEFT JOIN LATERAL (
          SELECT COUNT(*) AS n_likes
          FROM watched_like_events wle
          WHERE wle.watched_profile_id = wp.id
        ) l ON true
        LEFT JOIN LATERAL (
          SELECT COUNT(*) AS n_comments
          FROM social_comments sc
          JOIN social_posts sp ON sp.id = sc.parent_post_id
          JOIN social_profiles spr ON spr.id = sp.profile_id
          WHERE sc.author_hash = wp.author_hash
            AND spr.dirigente_id = wp.dirigente_observador_id
        ) c ON true
        WHERE {" AND ".join(where)}
        ORDER BY score DESC, wp.id
        LIMIT :limit
    """
    rows = (await db.execute(text(sql), params)).mappings().all()
    return [TopFanEntry(**dict(r)) for r in rows]


# ── Dashboard Stats: timeline, top-posts, interactions-summary ────────
# PLAN-2026-05-17-fans-dashboard.md · Sprint A
# Convención: timeline agrupado por sp.published_at (NO detected_at, sería pico falso).

class TimelinePoint(BaseModel):
    date: str  # YYYY-MM-DD
    n_posts: int
    n_reactions: int
    n_comments: int
    window_quality: Literal["complete", "partial"]  # partial = últimos 3d acumulando


class TopPostSampleQuote(BaseModel):
    text: str
    polaridad: int  # -2..+2


class TopPostItem(BaseModel):
    post_id: int
    published_at: str
    content_snippet: str
    likes: int
    n_comments: int
    n_classified_comments: int
    avg_polaridad: float | None
    sample_quotes: list[TopPostSampleQuote]
    post_url: str | None


class InteractionsSummary(BaseModel):
    dirigente_id: int
    window_days: int | None
    """None cuando all_time=True · UI debe mostrar 'histórico' en vez de 'Nd'."""
    total_reactions: int
    total_comments: int
    comments_classified: int
    comments_classified_pct: float
    posts_in_window: int
    by_reaction_type: dict[str, int]
    reaction_type_quality: Literal["placeholder_like_only", "fully_classified"]


@router.get("/timeline", response_model=list[TimelinePoint])
async def watched_timeline(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    dirigente_id: int,
    days: int = Query(default=44, ge=7, le=120),
    platform: str | None = Query(default=None, description="FACEBOOK · INSTAGRAM · TWITTER · TIKTOK · YOUTUBE · None=todas"),
):
    """Series temporales agrupadas por DÍA DE PUBLICACIÓN del post (no detected_at).

    Cada bucket = posts publicados ese día + reactions+comments acumulados
    detectados sobre esos posts.

    `window_quality`:
      - complete: bucket en ventana [now-days, now-3d]
      - partial:  bucket en últimos 3d (posts siguen acumulando reactions)

    `platform`: None (default) = cross-platform agregado. Filter explícito
    si quiere comparar plataformas individuales.
    """
    await _assert_dirigente_access(db, user, dirigente_id)
    platform_clause = "AND sps.platform = :platform" if platform else ""
    params: dict = {"did": dirigente_id, "days": str(days)}
    if platform:
        params["platform"] = platform

    rows = (await db.execute(text(f"""
        WITH posts_in_range AS (
          SELECT sp.id, sp.published_at::date AS bucket
          FROM social_posts sp
          JOIN social_profiles sps ON sp.profile_id=sps.id
          WHERE sps.dirigente_id=:did
            {platform_clause}
            AND sp.published_at::date >= (NOW()::date - (:days || ' days')::interval)
        ),
        per_bucket_reactions AS (
          SELECT pir.bucket, COUNT(wle.id) AS n_reactions, COUNT(DISTINCT pir.id) AS n_posts
          FROM posts_in_range pir
          LEFT JOIN watched_like_events wle ON wle.post_id=pir.id
          GROUP BY pir.bucket
        ),
        per_bucket_comments AS (
          SELECT pir.bucket, COUNT(sc.id) AS n_comments
          FROM posts_in_range pir
          LEFT JOIN social_comments sc ON sc.parent_post_id=pir.id
          GROUP BY pir.bucket
        )
        SELECT r.bucket, r.n_posts, r.n_reactions, COALESCE(c.n_comments, 0) AS n_comments
        FROM per_bucket_reactions r
        LEFT JOIN per_bucket_comments c ON c.bucket=r.bucket
        ORDER BY r.bucket
    """), params)).all()

    out: list[TimelinePoint] = []
    cutoff_partial = datetime.now(UTC).date() - timedelta(days=3)
    for r in rows:
        bucket_date = r[0]
        quality = "partial" if bucket_date >= cutoff_partial else "complete"
        out.append(TimelinePoint(
            date=bucket_date.isoformat(),
            n_posts=r[1] or 0,
            n_reactions=r[2] or 0,
            n_comments=r[3] or 0,
            window_quality=quality,
        ))
    return out


@router.get("/top-posts", response_model=list[TopPostItem])
async def watched_top_posts(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    dirigente_id: int,
    kind: Literal["winners", "losers"] = "winners",
    limit: int = Query(default=3, ge=1, le=10),
    days: int = Query(default=30, ge=7, le=120),
    platform: str | None = Query(default=None, description="None=cross-platform · FACEBOOK · INSTAGRAM · etc"),
):
    """Top posts ranqueados por polaridad neta de comments + engagement.

    - kind=winners: alto engagement AND AVG(nlp_polaridad) > 0 (comments positivos)
    - kind=losers:  alto engagement AND AVG(nlp_polaridad) < 0 (críticas concentradas)

    Requiere comments con `nlp_polaridad` poblado (Sprint D backfill).
    Si <3 posts con clasificación, devuelve los que haya (lista corta).
    """
    await _assert_dirigente_access(db, user, dirigente_id)
    order = "DESC" if kind == "winners" else "ASC"
    polarity_filter = "AVG(sc.nlp_polaridad) > 0" if kind == "winners" else "AVG(sc.nlp_polaridad) < 0"

    # Salvaguarda 2026-05-20 (CEO Issue #3): excluir posts sin ninguna reacción
    # pública (sp.likes >= 1). Defensa contra "posts huérfanos rankeados solo
    # por polaridad NLP". En Saymi BD actual no afecta el ranking (mínimo
    # observado 20 likes), pero protege otros dirigentes con corpus menor.
    platform_clause = "AND sps.platform = :platform" if platform else ""
    params: dict = {"did": dirigente_id, "days": str(days), "limit": limit}
    if platform:
        params["platform"] = platform
    rows = (await db.execute(text(f"""
        SELECT
          sp.id AS post_id,
          sp.published_at,
          LEFT(sp.content, 200) AS snippet,
          sp.likes,
          COUNT(sc.id) AS n_comments,
          COUNT(sc.id) FILTER (WHERE sc.nlp_polaridad IS NOT NULL) AS n_classified,
          AVG(sc.nlp_polaridad)::float AS avg_pol,
          sp.raw_data->>'url' AS url
        FROM social_posts sp
        JOIN social_profiles sps ON sp.profile_id=sps.id
        LEFT JOIN social_comments sc ON sc.parent_post_id=sp.id
        WHERE sps.dirigente_id=:did
          {platform_clause}
          AND sp.published_at >= NOW() - (:days || ' days')::interval
          AND sp.likes >= 1
        GROUP BY sp.id
        HAVING COUNT(sc.id) FILTER (WHERE sc.nlp_polaridad IS NOT NULL) >= 3
          AND {polarity_filter}
        ORDER BY AVG(sc.nlp_polaridad) {order}, sp.likes DESC
        LIMIT :limit
    """), params)).all()

    out: list[TopPostItem] = []
    for r in rows:
        # Sample 3 quotes alineadas con polaridad del kind
        sample_polarity_filter = ">= 1" if kind == "winners" else "<= -1"
        quotes = (await db.execute(text(f"""
            SELECT LEFT(sc.content, 140), sc.nlp_polaridad
            FROM social_comments sc
            WHERE sc.parent_post_id=:pid
              AND sc.nlp_polaridad IS NOT NULL
              AND sc.nlp_polaridad {sample_polarity_filter}
            ORDER BY ABS(sc.nlp_polaridad) DESC, sc.likes DESC
            LIMIT 3
        """), {"pid": r[0]})).all()
        out.append(TopPostItem(
            post_id=r[0],
            published_at=r[1].isoformat() if r[1] else "",
            content_snippet=(r[2] or "").strip(),
            likes=r[3] or 0,
            n_comments=r[4] or 0,
            n_classified_comments=r[5] or 0,
            avg_polaridad=round(r[6], 3) if r[6] is not None else None,
            sample_quotes=[
                TopPostSampleQuote(text=q[0].strip(), polaridad=q[1]) for q in quotes
            ],
            post_url=r[7],
        ))
    return out


@router.get("/interactions-summary", response_model=InteractionsSummary)
async def watched_interactions_summary(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    dirigente_id: int,
    days: int = Query(default=44, ge=7, le=3650),
    all_time: bool = Query(default=False),
    platform: str | None = Query(default=None, description="None=cross-platform · FACEBOOK · INSTAGRAM · etc"),
):
    """KPIs agregados para header del dashboard.

    `all_time=true` ignora el filtro de fecha y reporta total histórico
    (decisión CEO 2026-05-20: el badge con ventana 44d ocultaba ~30% de
    las reactions reales · per Hugo RADAR delta ~100K vs UI 56K).

    `platform`: None default = cross-platform agregado (CEO 2026-05-21
    D-PLATFORM-SELECTOR). Explícito para vista por red.
    """
    await _assert_dirigente_access(db, user, dirigente_id)
    platform_clause = "AND sps.platform = :platform" if platform else ""
    base_params: dict = {"did": dirigente_id}
    if platform:
        base_params["platform"] = platform

    if all_time:
        base = (await db.execute(text(f"""
            SELECT
              COUNT(DISTINCT wle.id) AS reactions,
              COUNT(DISTINCT sc.id) AS comments,
              COUNT(DISTINCT sc.id) FILTER (WHERE sc.nlp_tono IS NOT NULL) AS classified,
              COUNT(DISTINCT sp.id) AS posts_window
            FROM social_profiles sps
            LEFT JOIN social_posts sp ON sp.profile_id=sps.id
            LEFT JOIN watched_like_events wle ON wle.post_id=sp.id
            LEFT JOIN social_comments sc ON sc.parent_post_id=sp.id
            WHERE sps.dirigente_id=:did {platform_clause}
        """), base_params)).first()
    else:
        window_params = {**base_params, "days": str(days)}
        base = (await db.execute(text(f"""
            SELECT
              COUNT(DISTINCT wle.id) AS reactions,
              COUNT(DISTINCT sc.id) AS comments,
              COUNT(DISTINCT sc.id) FILTER (WHERE sc.nlp_tono IS NOT NULL) AS classified,
              COUNT(DISTINCT sp.id) AS posts_window
            FROM social_profiles sps
            LEFT JOIN social_posts sp ON sp.profile_id=sps.id
              AND sp.published_at >= NOW() - (:days || ' days')::interval
            LEFT JOIN watched_like_events wle ON wle.post_id=sp.id
            LEFT JOIN social_comments sc ON sc.parent_post_id=sp.id
            WHERE sps.dirigente_id=:did {platform_clause}
        """), window_params)).first()

    mix_rows = (await db.execute(text("""
        SELECT wle.reaction_type, COUNT(*) AS n
        FROM watched_like_events wle
        JOIN watched_profiles wp ON wle.watched_profile_id=wp.id
        WHERE wp.dirigente_observador_id=:did
        GROUP BY wle.reaction_type
    """), {"did": dirigente_id})).all()
    mix = {r[0]: r[1] for r in mix_rows}
    non_like = sum(v for k, v in mix.items() if k != "like")
    quality = "placeholder_like_only" if non_like == 0 else "fully_classified"

    total_comments = base[1] or 0
    classified = base[2] or 0
    pct = round(classified / total_comments * 100, 1) if total_comments else 0.0

    return InteractionsSummary(
        dirigente_id=dirigente_id,
        window_days=None if all_time else days,
        total_reactions=base[0] or 0,
        total_comments=total_comments,
        comments_classified=classified,
        comments_classified_pct=pct,
        posts_in_window=base[3] or 0,
        by_reaction_type=mix,
        reaction_type_quality=quality,
    )


# ── Bulk ingest de reacciones externas (S-8.1) ────────────────────────

class ReactorIn(BaseModel):
    platform: Literal["FACEBOOK", "INSTAGRAM", "TWITTER", "TIKTOK", "YOUTUBE"]
    profile_external_id: str = Field(min_length=1, max_length=100)
    profile_handle: str | None = Field(default=None, max_length=255)
    display_name: str | None = Field(default=None, max_length=255)
    profile_url: str | None = Field(default=None, max_length=500)
    avatar_url: str | None = None
    reaction_type: Literal["like", "love", "wow", "haha", "sad", "angry", "support", "care"] = "like"


class PostEnvelopeIn(BaseModel):
    post_url: str = Field(min_length=1)
    badge_count: int | None = None
    reactor_count: int | None = None
    low_engagement: bool = False
    post_date: str | None = None  # "YYYY-MM-DD"
    captured_at_iso: str | None = None
    timestamp_text: str | None = None
    story_fbid: str | None = None  # OPCIONAL: si viene, match directo platform_post_id
    reactors: list[ReactorIn] = Field(default_factory=list)


class IngestReactionsPayload(BaseModel):
    dirigente_observador_id: int
    source: Literal["other_scraper", "apify_reactions", "visual_evidence", "oauth_api"] = "other_scraper"
    fuzzy_likes_tolerance: int = Field(default=30, ge=0, le=200)
    results: list[PostEnvelopeIn]


class PostMatchReport(BaseModel):
    post_url: str
    matched_post_id: int | None
    match_strategy: Literal["story_fbid", "story_fbid_url", "fuzzy_date_likes", "ambiguous", "no_match"]
    candidates_count: int = 0


class ClienteSeedHit(BaseModel):
    watched_profile_id: int
    display_name: str | None
    profile_handle: str | None
    n_reactions: int


class IngestReactionsResult(BaseModel):
    posts_received: int
    posts_resolved: int
    posts_skipped_no_match: int
    posts_skipped_ambiguous: int
    reactions_inserted: int
    reactions_duplicates: int
    profiles_created_auto: int
    cliente_seed_matches: list[ClienteSeedHit]
    posts_detail: list[PostMatchReport]


@router.post(
    "/ingest-reactions-bulk",
    response_model=IngestReactionsResult,
    status_code=status.HTTP_200_OK,
)
async def ingest_reactions_bulk(
    payload: IngestReactionsPayload,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    """Bulk ingest de reacciones desde scrapers externos (Juan FB browser-harness, etc.).

    Plan: S-8.1 · 2026-05-17. Sin rotura schema · LFPDPPP-safe (hash server-side con
    COMMENT_AUTHOR_SALT local, NUNCA viaja en payload).

    Match estrategia post:
      1. Si reactor.envelope trae `story_fbid` → match directo platform_post_id (cero deuda).
      2. Fallback: fuzzy `(published_at::date = post_date AND profile=dirigente.fb_profile
         AND |likes - badge_count| <= tolerance)`. Si >1 candidato → skip ambiguous.
      3. Si 0 candidatos → skip no_match (post no en BD, requiere backfill previo).

    Match estrategia reactor:
      - Lookup en watched_profiles del dirigente_observador por (case-insensitive):
        profile_handle == raw_id OR profile_external_id == raw_id.
      - Si match → usa wp_id existente (cliente_seed gana).
      - Si no match → INSERT auto_suggested con datos del reactor + author_hash del raw_id.

    Inserta en watched_like_events con ON CONFLICT DO NOTHING (idempotente).
    """
    await _assert_dirigente_access(db, user, payload.dirigente_observador_id)

    # 1. Resolver social_profile del dirigente (asumimos 1 FB profile activo).
    # Para soportar otras plataformas en payload mixto, agrupamos por platform.
    profiles_by_plat: dict[str, int] = {}
    prow = (await db.execute(text("""
        SELECT id, platform::text FROM social_profiles
        WHERE dirigente_id = :did
    """), {"did": payload.dirigente_observador_id})).all()
    for pid, plat in prow:
        profiles_by_plat[plat] = pid

    if not profiles_by_plat:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"Dirigente {payload.dirigente_observador_id} no tiene social_profiles activos",
        )

    # 2. Org_id para nuevos auto_suggested
    org_row = (await db.execute(
        text("SELECT org_id FROM dirigentes WHERE id = :did"),
        {"did": payload.dirigente_observador_id},
    )).first()
    org_id = org_row[0] if org_row else None

    posts_resolved = 0
    posts_skipped_no_match = 0
    posts_skipped_ambiguous = 0
    reactions_inserted = 0
    reactions_duplicates = 0
    profiles_created_auto = 0
    posts_detail: list[PostMatchReport] = []
    seed_counter: dict[int, int] = {}  # wp_id → n_reactions de cliente_seed

    for env in payload.results:
        # Skip envelopes sin reactores
        if not env.reactors:
            posts_detail.append(PostMatchReport(
                post_url=env.post_url, matched_post_id=None,
                match_strategy="no_match", candidates_count=0,
            ))
            posts_skipped_no_match += 1
            continue

        # Determinar platform del envelope (asumir todos los reactors mismo platform)
        env_platform = env.reactors[0].platform
        sp_profile_id = profiles_by_plat.get(env_platform)
        if not sp_profile_id:
            posts_detail.append(PostMatchReport(
                post_url=env.post_url, matched_post_id=None,
                match_strategy="no_match", candidates_count=0,
            ))
            posts_skipped_no_match += 1
            continue

        # 3. Match post
        matched_post_id: int | None = None
        match_strategy: str = "no_match"
        candidates_count = 0

        if env.story_fbid:
            res = (await db.execute(text("""
                SELECT id FROM social_posts
                WHERE profile_id = :pid AND platform_post_id = :sfid
                LIMIT 2
            """), {"pid": sp_profile_id, "sfid": env.story_fbid})).all()
            candidates_count = len(res)
            if candidates_count == 1:
                matched_post_id = res[0][0]
                match_strategy = "story_fbid"
            elif candidates_count > 1:
                match_strategy = "ambiguous"

        # 3b. Fallback URL-based: story_fbid extraído del path FB ≠ platform_post_id
        # interno de Apify. El URL en raw_data sí contiene el story_fbid.
        if not matched_post_id and match_strategy != "ambiguous" and env.story_fbid:
            res = (await db.execute(text("""
                SELECT id FROM social_posts
                WHERE profile_id = :pid
                  AND raw_data->>'url' LIKE :pattern
                LIMIT 2
            """), {"pid": sp_profile_id, "pattern": f"%{env.story_fbid}%"})).all()
            candidates_count = len(res)
            if candidates_count == 1:
                matched_post_id = res[0][0]
                match_strategy = "story_fbid_url"
            elif candidates_count > 1:
                match_strategy = "ambiguous"

        if not matched_post_id and match_strategy != "ambiguous" and env.post_date and env.badge_count is not None:
            try:
                pdate = datetime.strptime(env.post_date, "%Y-%m-%d").date()
            except ValueError:
                pdate = None
            if pdate is not None:
                res = (await db.execute(text("""
                    SELECT id FROM social_posts
                    WHERE profile_id = :pid
                      AND published_at::date = :pdate
                      AND ABS(likes - :bc) <= :tol
                    ORDER BY ABS(likes - :bc) ASC
                    LIMIT 5
                """), {
                    "pid": sp_profile_id,
                    "pdate": pdate,
                    "bc": env.badge_count,
                    "tol": payload.fuzzy_likes_tolerance,
                })).all()
            else:
                res = []
            candidates_count = len(res)
            if candidates_count == 1:
                matched_post_id = res[0][0]
                match_strategy = "fuzzy_date_likes"
            elif candidates_count > 1:
                # Aceptamos el más cercano (ORDER BY ABS asc, [0] gana)
                matched_post_id = res[0][0]
                match_strategy = "fuzzy_date_likes"
            # candidates_count == 0 → no_match

        posts_detail.append(PostMatchReport(
            post_url=env.post_url, matched_post_id=matched_post_id,
            match_strategy=match_strategy,  # type: ignore[arg-type]
            candidates_count=candidates_count,
        ))

        if not matched_post_id:
            if match_strategy == "ambiguous":
                posts_skipped_ambiguous += 1
            else:
                posts_skipped_no_match += 1
            continue

        posts_resolved += 1

        # 4. Procesar reactors del envelope
        for reactor in env.reactors:
            raw_id = reactor.profile_external_id
            # Lookup case-insensitive sobre handle OR external_id
            wp_row = (await db.execute(text("""
                SELECT id, source FROM watched_profiles
                WHERE dirigente_observador_id = :did
                  AND platform = :plat
                  AND (
                    LOWER(profile_handle) = LOWER(:raw)
                    OR LOWER(profile_external_id) = LOWER(:raw)
                  )
                LIMIT 1
            """), {
                "did": payload.dirigente_observador_id,
                "plat": reactor.platform,
                "raw": raw_id,
            })).first()

            if wp_row:
                wp_id, wp_source = wp_row[0], wp_row[1]
                is_seed = (wp_source == "cliente_seed")
            else:
                # Crear auto_suggested
                ah = _hash(reactor.platform, raw_id)
                try:
                    ins = await db.execute(text("""
                        INSERT INTO watched_profiles
                          (dirigente_observador_id, org_id, platform, profile_external_id,
                           profile_handle, profile_url, display_name, avatar_url,
                           source, tags, notes, author_hash, created_by)
                        VALUES (:did, :org, :plat, :eid, :handle, :url, :name, :avatar,
                                'auto_suggested', CAST('[]' AS jsonb), NULL, :ah, :uid)
                        ON CONFLICT (dirigente_observador_id, platform, profile_external_id)
                        DO UPDATE SET updated_at = now()
                        RETURNING id
                    """), {
                        "did": payload.dirigente_observador_id,
                        "org": org_id,
                        "plat": reactor.platform,
                        "eid": raw_id,
                        "handle": reactor.profile_handle,
                        "url": reactor.profile_url,
                        "name": reactor.display_name,
                        "avatar": reactor.avatar_url,
                        "ah": ah,
                        "uid": user.id,
                    })
                    wp_id = ins.first()[0]
                    profiles_created_auto += 1
                    is_seed = False
                except Exception:
                    await db.rollback()
                    continue

            # 5. Insertar watched_like_event idempotente
            try:
                ev = await db.execute(text("""
                    INSERT INTO watched_like_events
                      (watched_profile_id, post_id, reaction_type, detected_at, source)
                    VALUES (:wp, :pid, :rt, now(), :src)
                    ON CONFLICT (watched_profile_id, post_id, reaction_type) DO NOTHING
                    RETURNING id
                """), {
                    "wp": wp_id, "pid": matched_post_id,
                    "rt": reactor.reaction_type, "src": payload.source,
                })
                if ev.first():
                    reactions_inserted += 1
                    if is_seed:
                        seed_counter[wp_id] = seed_counter.get(wp_id, 0) + 1
                else:
                    reactions_duplicates += 1
            except Exception:
                await db.rollback()
                continue

    # 6. Resolver detalles cliente_seed para el reporte
    cliente_seed_matches: list[ClienteSeedHit] = []
    if seed_counter:
        rows = (await db.execute(text("""
            SELECT id, display_name, profile_handle
            FROM watched_profiles
            WHERE id = ANY(:ids)
        """), {"ids": list(seed_counter.keys())})).all()
        for wp_id, name, handle in rows:
            cliente_seed_matches.append(ClienteSeedHit(
                watched_profile_id=wp_id,
                display_name=name,
                profile_handle=handle,
                n_reactions=seed_counter[wp_id],
            ))
        cliente_seed_matches.sort(key=lambda x: -x.n_reactions)

    await db.commit()

    return IngestReactionsResult(
        posts_received=len(payload.results),
        posts_resolved=posts_resolved,
        posts_skipped_no_match=posts_skipped_no_match,
        posts_skipped_ambiguous=posts_skipped_ambiguous,
        reactions_inserted=reactions_inserted,
        reactions_duplicates=reactions_duplicates,
        profiles_created_auto=profiles_created_auto,
        cliente_seed_matches=cliente_seed_matches,
        posts_detail=posts_detail,
    )
