"""Competitor profiles — modelo ligero benchmark-oriented.

Origen: B-COMPETIDORES-MODELO-1 (Opción C) + PLAN-2026-05-14-war-room-personal.md (W1).

Endpoints en /api/v1/aceptacion/competitors:
- GET /                            — listar competidores (org-scoped via dirigente_objetivo_id)
- GET /{id}                        — detalle + métricas mensuales
- POST /                           — crear (admin/analyst only)
- PATCH /{id}                      — actualizar (admin/analyst only)
- DELETE /{id}                     — soft delete (admin/analyst only)
- GET /admin/rankings              — ranking cross-org (admin/analyst only)

D-MODEL-WAR-ROOM-1: competitor_profiles es la tabla canónica. Light pipeline (sin NLP).
D-SEC-WATCHED-SCOPE-1: todos los endpoints aplican _check_org via dirigente_objetivo_id.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import Role, RoleChecker, get_current_user
from app.models.user import User

router = APIRouter()

PLATFORMS = ("TWITTER", "INSTAGRAM", "FACEBOOK", "TIKTOK", "YOUTUBE", "BLUESKY", "THREADS", "TELEGRAM")

# Solo admin/analyst pueden mutar competidores (CEO confirmó "MD los carga").
RequireMutator = RoleChecker([Role.ADMIN, Role.ANALYST])


# ── Helpers ──────────────────────────────────────────────────────────

def _check_org(user: User, dirigente_org_id: int | None) -> None:
    """Misma semántica que watched_profiles._check_org."""
    if user.role == "admin":
        return
    if dirigente_org_id is None or user.org_id != dirigente_org_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Sin acceso a esta organización")


async def _assert_dirigente_access(
    db: AsyncSession, user: User, dirigente_id: int
) -> int:
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


async def _assert_competitor_access(
    db: AsyncSession, user: User, competitor_id: int
) -> int:
    """Resuelve competitor → dirigente_objetivo → org → check. Retorna dirigente_objetivo_id."""
    row = (
        await db.execute(
            text(
                """
                SELECT cp.dirigente_objetivo_id, d.org_id
                FROM competitor_profiles cp
                JOIN dirigentes d ON d.id = cp.dirigente_objetivo_id
                WHERE cp.id = :cid
                """
            ),
            {"cid": competitor_id},
        )
    ).first()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Competidor no existe")
    _check_org(user, row[1])
    return row[0]


# ── Schemas ──────────────────────────────────────────────────────────

class CompetitorRead(BaseModel):
    id: int
    dirigente_objetivo_id: int
    display_name: str
    partido: str | None
    cargo: str | None
    platform: str
    profile_handle: str | None
    profile_url: str | None
    notes: str | None
    tags: list[str]
    is_active: bool
    verified: bool
    last_scraped_at: datetime | None
    created_at: datetime


class MonthlyMetric(BaseModel):
    month_start: date
    posts_count: int
    total_reactions: int
    total_comments: int
    engagement_rate: float | None
    followers_total: int | None


class CompetitorDetail(CompetitorRead):
    last_6_months: list[MonthlyMetric]


# A8 fix (2026-05-15): agrupar profiles por persona en la capa de presentación.
# El modelo competitor_profiles tiene 1 fila por (persona, plataforma) — ej.
# Taboada tiene 2 rows (TW + IG). La UI antes mostraba "dup". Esta vista
# agrega los profiles de la misma persona en una sola estructura, sin tocar BD.
# Group key: (display_name, dirigente_objetivo_id, partido).
class CompetitorProfileItem(BaseModel):
    id: int
    platform: str
    profile_handle: str | None
    profile_url: str | None
    last_scraped_at: datetime | None


class CompetitorGrouped(BaseModel):
    display_name: str
    partido: str | None
    cargo: str | None
    dirigente_objetivo_id: int
    verified: bool
    tags: list[str]
    notes: str | None
    profiles: list[CompetitorProfileItem]


class CompetitorCreate(BaseModel):
    dirigente_objetivo_id: int
    display_name: str = Field(min_length=1, max_length=255)
    partido: str | None = Field(default=None, max_length=64)
    cargo: str | None = Field(default=None, max_length=255)
    platform: Literal["TWITTER", "INSTAGRAM", "FACEBOOK", "TIKTOK", "YOUTUBE", "BLUESKY", "THREADS", "TELEGRAM"]
    profile_external_id: str = Field(min_length=1, max_length=100)
    profile_handle: str | None = Field(default=None, max_length=255)
    profile_url: str | None = Field(default=None, max_length=500)
    notes: str | None = None
    tags: list[str] = Field(default_factory=list)
    verified: bool = False


class CompetitorUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=255)
    partido: str | None = Field(default=None, max_length=64)
    cargo: str | None = Field(default=None, max_length=255)
    profile_handle: str | None = Field(default=None, max_length=255)
    profile_url: str | None = Field(default=None, max_length=500)
    notes: str | None = None
    tags: list[str] | None = None
    verified: bool | None = None
    is_active: bool | None = None


class AdminRankingRow(BaseModel):
    competitor_id: int
    display_name: str
    partido: str | None
    platform: str
    dirigente_objetivo_id: int
    dirigente_objetivo_name: str
    org_id: int
    followers_total: int | None
    engagement_rate: float | None
    posts_count: int | None
    last_month: date | None


# ── Read endpoints ───────────────────────────────────────────────────

@router.get("/", response_model=list[CompetitorRead])
async def list_competitors(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    dirigente_objetivo_id: int | None = Query(default=None),
) -> list[CompetitorRead]:
    """Lista competidores. Si dirigente_objetivo_id se pasa, valida org; si no,
    devuelve solo competidores del org del user (admin ve todos)."""
    where = ["cp.is_active = TRUE"]
    params: dict = {}
    if dirigente_objetivo_id is not None:
        await _assert_dirigente_access(db, user, dirigente_objetivo_id)
        where.append("cp.dirigente_objetivo_id = :did")
        params["did"] = dirigente_objetivo_id
    elif user.role != Role.ADMIN:
        where.append("cp.org_id = :user_org")
        params["user_org"] = user.org_id

    sql = f"""
        SELECT cp.id, cp.dirigente_objetivo_id, cp.display_name, cp.partido, cp.cargo,
               cp.platform, cp.profile_handle, cp.profile_url, cp.notes, cp.tags,
               cp.is_active, cp.verified, cp.last_scraped_at, cp.created_at
        FROM competitor_profiles cp
        WHERE {' AND '.join(where)}
        ORDER BY cp.verified DESC, cp.display_name
    """
    rows = (await db.execute(text(sql), params)).mappings().all()
    return [CompetitorRead.model_validate(dict(r)) for r in rows]


@router.get("/grouped", response_model=list[CompetitorGrouped])
async def list_competitors_grouped(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    dirigente_objetivo_id: int | None = Query(default=None),
) -> list[CompetitorGrouped]:
    """A8 fix (2026-05-15) — competidores agrupados por persona.

    Resuelve el problema "Taboada duplicado" en la capa de presentación
    sin tocar el modelo: una sola entrada por persona con `profiles` como
    array de sus N plataformas. Group key = (display_name, dirigente_objetivo_id,
    partido). Cross-audit Gemini validó este approach vs refactor de BD
    (over-engineering para 1 caso real en 6 personas).
    """
    where = ["cp.is_active = TRUE"]
    params: dict = {}
    if dirigente_objetivo_id is not None:
        await _assert_dirigente_access(db, user, dirigente_objetivo_id)
        where.append("cp.dirigente_objetivo_id = :did")
        params["did"] = dirigente_objetivo_id
    elif user.role != Role.ADMIN:
        where.append("cp.org_id = :user_org")
        params["user_org"] = user.org_id

    sql = f"""
        SELECT cp.id, cp.dirigente_objetivo_id, cp.display_name, cp.partido,
               cp.cargo, cp.platform, cp.profile_handle, cp.profile_url,
               cp.notes, cp.tags, cp.verified, cp.last_scraped_at
        FROM competitor_profiles cp
        WHERE {' AND '.join(where)}
        ORDER BY cp.verified DESC, cp.display_name, cp.platform
    """
    rows = (await db.execute(text(sql), params)).mappings().all()

    # Group by (display_name, dirigente_objetivo_id, partido). Para 6 competidores
    # curados manualmente por CEO, GROUP BY display_name es seguro (homónimos =
    # fantasma académico según Gemini cross-audit).
    grouped: dict[tuple, dict] = {}
    for r in rows:
        key = (r["display_name"], r["dirigente_objetivo_id"], r["partido"])
        if key not in grouped:
            grouped[key] = {
                "display_name": r["display_name"],
                "partido": r["partido"],
                "cargo": r["cargo"],
                "dirigente_objetivo_id": r["dirigente_objetivo_id"],
                "verified": r["verified"],
                "tags": r["tags"] or [],
                "notes": r["notes"],
                "profiles": [],
            }
        # Si cualquier profile está verificado, la persona se considera verified.
        # Si cualquier profile tiene notes/tags, usamos los del primer profile
        # ordenado (verified DESC, platform).
        if r["verified"]:
            grouped[key]["verified"] = True
        grouped[key]["profiles"].append({
            "id": r["id"],
            "platform": r["platform"],
            "profile_handle": r["profile_handle"],
            "profile_url": r["profile_url"],
            "last_scraped_at": r["last_scraped_at"],
        })

    return [CompetitorGrouped.model_validate(v) for v in grouped.values()]


@router.get("/admin/rankings", response_model=list[AdminRankingRow])
async def admin_rankings(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    _admin: Annotated[None, Depends(RequireMutator)],
    limit: int = Query(default=100, le=500),
) -> list[AdminRankingRow]:
    """Cross-org ranking — solo admin/analyst. Vista MD/MC central para benchmark transversal."""
    rows = (
        await db.execute(
            text(
                """
                SELECT cp.id AS competitor_id,
                       cp.display_name, cp.partido, cp.platform,
                       cp.dirigente_objetivo_id,
                       d.full_name AS dirigente_objetivo_name,
                       d.org_id,
                       m.followers_total, m.engagement_rate, m.posts_count,
                       m.month_start AS last_month
                FROM competitor_profiles cp
                JOIN dirigentes d ON d.id = cp.dirigente_objetivo_id
                LEFT JOIN LATERAL (
                    SELECT followers_total, engagement_rate, posts_count, month_start
                    FROM competitor_metrics_monthly
                    WHERE competitor_id = cp.id
                    ORDER BY month_start DESC NULLS LAST
                    LIMIT 1
                ) m ON true
                WHERE cp.is_active = TRUE
                ORDER BY m.followers_total DESC NULLS LAST, cp.display_name
                LIMIT :limit
                """
            ),
            {"limit": limit},
        )
    ).mappings().all()
    return [AdminRankingRow.model_validate(dict(r)) for r in rows]


@router.get("/{competitor_id}", response_model=CompetitorDetail)
async def get_competitor(
    competitor_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> CompetitorDetail:
    await _assert_competitor_access(db, user, competitor_id)
    base = (
        await db.execute(
            text(
                """SELECT id, dirigente_objetivo_id, display_name, partido, cargo,
                          platform, profile_handle, profile_url, notes, tags,
                          is_active, verified, last_scraped_at, created_at
                   FROM competitor_profiles WHERE id = :cid"""
            ),
            {"cid": competitor_id},
        )
    ).mappings().first()
    if not base:
        raise HTTPException(404, "Competidor no encontrado")

    metrics_rows = (
        await db.execute(
            text(
                """SELECT month_start, posts_count, total_reactions, total_comments,
                          engagement_rate, followers_total
                   FROM competitor_metrics_monthly
                   WHERE competitor_id = :cid
                   ORDER BY month_start DESC
                   LIMIT 6"""
            ),
            {"cid": competitor_id},
        )
    ).mappings().all()

    data = dict(base)
    data["last_6_months"] = [MonthlyMetric.model_validate(dict(m)) for m in metrics_rows]
    return CompetitorDetail.model_validate(data)


# ── Mutation endpoints (admin/analyst only) ──────────────────────────

@router.post("/", response_model=CompetitorRead, status_code=status.HTTP_201_CREATED)
async def create_competitor(
    payload: CompetitorCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    _admin: Annotated[None, Depends(RequireMutator)],
) -> CompetitorRead:
    org_id = await _assert_dirigente_access(db, user, payload.dirigente_objetivo_id)

    try:
        result = await db.execute(
            text(
                """
                INSERT INTO competitor_profiles
                  (org_id, dirigente_objetivo_id, display_name, partido, cargo,
                   platform, profile_external_id, profile_handle, profile_url,
                   notes, tags, verified, created_by)
                VALUES (:org, :did, :name, :partido, :cargo,
                        :plat, :eid, :handle, :url,
                        :notes, CAST(:tags AS jsonb), :verified, :uid)
                RETURNING id, dirigente_objetivo_id, display_name, partido, cargo,
                          platform, profile_handle, profile_url, notes, tags,
                          is_active, verified, last_scraped_at, created_at
                """
            ),
            {
                "org": org_id,
                "did": payload.dirigente_objetivo_id,
                "name": payload.display_name,
                "partido": payload.partido,
                "cargo": payload.cargo,
                "plat": payload.platform,
                "eid": payload.profile_external_id,
                "handle": payload.profile_handle,
                "url": payload.profile_url,
                "notes": payload.notes,
                "tags": __import__("json").dumps(payload.tags),
                "verified": payload.verified,
                "uid": user.id,
            },
        )
        row = result.mappings().first()
        await db.commit()
        return CompetitorRead.model_validate(dict(row))
    except Exception as e:
        await db.rollback()
        if "uq_competitor_profile_dirigente_platform" in str(e) or "unique" in str(e).lower():
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Ya existe un competidor con esa combinación dirigente+platform+external_id",
            )
        raise


@router.patch("/{competitor_id}", response_model=CompetitorRead)
async def update_competitor(
    competitor_id: int,
    payload: CompetitorUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    _admin: Annotated[None, Depends(RequireMutator)],
) -> CompetitorRead:
    await _assert_competitor_access(db, user, competitor_id)

    sets, params = [], {"cid": competitor_id}
    if payload.display_name is not None:
        sets.append("display_name = :name")
        params["name"] = payload.display_name
    if payload.partido is not None:
        sets.append("partido = :partido")
        params["partido"] = payload.partido
    if payload.cargo is not None:
        sets.append("cargo = :cargo")
        params["cargo"] = payload.cargo
    if payload.profile_handle is not None:
        sets.append("profile_handle = :handle")
        params["handle"] = payload.profile_handle
    if payload.profile_url is not None:
        sets.append("profile_url = :url")
        params["url"] = payload.profile_url
    if payload.notes is not None:
        sets.append("notes = :notes")
        params["notes"] = payload.notes
    if payload.tags is not None:
        sets.append("tags = CAST(:tags AS jsonb)")
        params["tags"] = __import__("json").dumps(payload.tags)
    if payload.verified is not None:
        sets.append("verified = :verified")
        params["verified"] = payload.verified
    if payload.is_active is not None:
        sets.append("is_active = :active")
        params["active"] = payload.is_active
    if not sets:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Sin campos para actualizar")

    sets.append("updated_at = now()")
    sql = f"""
        UPDATE competitor_profiles SET {', '.join(sets)} WHERE id = :cid
        RETURNING id, dirigente_objetivo_id, display_name, partido, cargo,
                  platform, profile_handle, profile_url, notes, tags,
                  is_active, verified, last_scraped_at, created_at
    """
    row = (await db.execute(text(sql), params)).mappings().first()
    if not row:
        raise HTTPException(404, "Competidor no encontrado")
    # S8 audit log · UPDATE manual de competidor
    from app.core.audit_listeners import log_destructive_op
    changed_cols = [k for k in payload.model_dump(exclude_unset=True).keys()]
    await log_destructive_op(
        db,
        action="UPDATE",
        model="competitor_profiles",
        record_id=competitor_id,
        changes_summary={"changed_columns": changed_cols},
    )
    await db.commit()
    return CompetitorRead.model_validate(dict(row))


@router.delete("/{competitor_id}")
async def delete_competitor(
    competitor_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    _admin: Annotated[None, Depends(RequireMutator)],
    hard: bool = False,
):
    await _assert_competitor_access(db, user, competitor_id)
    if hard:
        await db.execute(text("DELETE FROM competitor_profiles WHERE id = :cid"), {"cid": competitor_id})
    else:
        await db.execute(
            text("UPDATE competitor_profiles SET is_active = FALSE, updated_at = now() WHERE id = :cid"),
            {"cid": competitor_id},
        )
    # S8 audit log · DELETE/soft-delete competidor
    from app.core.audit_listeners import log_destructive_op
    await log_destructive_op(
        db,
        action="DELETE" if hard else "UPDATE",
        model="competitor_profiles",
        record_id=competitor_id,
        changes_summary=({"soft_delete": True} if not hard else None),
    )
    await db.commit()
    return {"ok": True, "hard": hard}


# ── Monthly snapshot ingest (D-1.4, 2026-05-16) ─────────────────────
#
# Recibe JSON producido por scraper externo (browser-harness Juan o
# pipeline propio) con post-metadata mensual del competidor. Upsert posts
# + recompute competitor_metrics_monthly del periodo cubierto.
#
# NO ejecuta NLP (sentiment_score/label quedan NULL). Sin scraping de
# comments. Sin reactor detail. Solo metadata agregada.


class IngestPostItem(BaseModel):
    platform_post_id: str = Field(..., max_length=255)
    post_url: str | None = None
    content: str | None = None
    published_at: datetime | None = None
    reactions: int = Field(0, ge=0)
    comments_count: int = Field(0, ge=0)
    shares: int = Field(0, ge=0)
    views: int | None = None


class IngestProfileSnapshot(BaseModel):
    """Snapshot mensual de UN competidor."""
    handle: str = Field(..., min_length=1)
    platform: Literal["FACEBOOK", "INSTAGRAM", "TWITTER", "TIKTOK", "YOUTUBE"]
    followers_count: int | None = Field(None, ge=0)
    month_start: date = Field(..., description="Primer día del mes cubierto · YYYY-MM-01")
    posts: list[IngestPostItem] = Field(default_factory=list)


class IngestMonthlySnapshotRequest(BaseModel):
    scraped_at: datetime | None = None
    profiles: list[IngestProfileSnapshot]


class IngestProfileResult(BaseModel):
    handle: str
    platform: str
    competitor_id: int | None = None
    posts_upserted: int = 0
    metric_row_id: int | None = None
    error: str | None = None


class IngestMonthlySnapshotResponse(BaseModel):
    scraped_at: datetime
    profiles_processed: int
    posts_upserted_total: int
    results: list[IngestProfileResult]


@router.post(
    "/ingest-monthly-snapshot",
    response_model=IngestMonthlySnapshotResponse,
    dependencies=[Depends(RequireMutator)],
)
async def ingest_monthly_snapshot(
    body: IngestMonthlySnapshotRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
) -> IngestMonthlySnapshotResponse:
    """Ingesta de snapshot mensual de competidores (D-1.4 · 2026-05-16).

    Idempotente: posts dedup por `(competitor_id, platform_post_id)`. Métricas
    mensuales recalculadas por `(competitor_id, month_start)`.

    El caller debe haber resuelto handles→competidores antes (handles que NO
    matcheen filas de competitor_profiles activas resultan en error=handle_not_found).
    """
    scraped_at = body.scraped_at or datetime.utcnow()
    results: list[IngestProfileResult] = []
    posts_total = 0

    for snap in body.profiles:
        # Resolver competitor_id por handle + platform (case-insensitive handle)
        comp_row = (
            await db.execute(
                text(
                    """
                    SELECT id, dirigente_objetivo_id, org_id
                    FROM competitor_profiles
                    WHERE LOWER(profile_handle) = LOWER(:h)
                      AND platform = :p
                      AND is_active = TRUE
                    LIMIT 1
                    """
                ),
                {"h": snap.handle, "p": snap.platform},
            )
        ).first()

        if not comp_row:
            results.append(
                IngestProfileResult(
                    handle=snap.handle,
                    platform=snap.platform,
                    error="handle_not_found",
                )
            )
            continue

        competitor_id = comp_row[0]

        # Upsert followers_count en competitor_profiles si vino
        if snap.followers_count is not None:
            await db.execute(
                text(
                    "UPDATE competitor_profiles "
                    "SET last_scraped_at = :ts, updated_at = now() "
                    "WHERE id = :cid"
                ),
                {"ts": scraped_at, "cid": competitor_id},
            )

        # Upsert cada post (ON CONFLICT actualiza counts + content)
        posts_upserted = 0
        for post in snap.posts:
            await db.execute(
                text(
                    """
                    INSERT INTO competitor_posts (
                        competitor_id, platform_post_id, post_url, content,
                        published_at, reactions, comments_count, shares, views,
                        scraped_at
                    ) VALUES (
                        :cid, :pid, :url, :content,
                        :pub, :rx, :cm, :sh, :vw,
                        :ts
                    )
                    ON CONFLICT ON CONSTRAINT uq_competitor_post_id
                    DO UPDATE SET
                        post_url = COALESCE(EXCLUDED.post_url, competitor_posts.post_url),
                        content = COALESCE(EXCLUDED.content, competitor_posts.content),
                        published_at = COALESCE(EXCLUDED.published_at, competitor_posts.published_at),
                        reactions = EXCLUDED.reactions,
                        comments_count = EXCLUDED.comments_count,
                        shares = EXCLUDED.shares,
                        views = COALESCE(EXCLUDED.views, competitor_posts.views),
                        scraped_at = EXCLUDED.scraped_at
                    """
                ),
                {
                    "cid": competitor_id,
                    "pid": post.platform_post_id,
                    "url": post.post_url,
                    "content": post.content,
                    "pub": post.published_at,
                    "rx": post.reactions,
                    "cm": post.comments_count,
                    "sh": post.shares,
                    "vw": post.views,
                    "ts": scraped_at,
                },
            )
            posts_upserted += 1
        posts_total += posts_upserted

        # Recompute competitor_metrics_monthly del mes cubierto
        agg = (
            await db.execute(
                text(
                    """
                    SELECT
                        COUNT(*)::INT AS posts_count,
                        COALESCE(SUM(reactions), 0)::INT AS total_reactions,
                        COALESCE(SUM(comments_count), 0)::INT AS total_comments,
                        COALESCE(SUM(shares), 0)::INT AS total_shares
                    FROM competitor_posts
                    WHERE competitor_id = :cid
                      AND published_at >= :ms
                      AND published_at < (:ms::date + interval '1 month')
                    """
                ),
                {"cid": competitor_id, "ms": snap.month_start},
            )
        ).first()

        metric_id = (
            await db.execute(
                text(
                    """
                    INSERT INTO competitor_metrics_monthly (
                        competitor_id, month_start,
                        posts_count, total_reactions, total_comments, total_shares,
                        computed_at
                    ) VALUES (
                        :cid, :ms,
                        :pc, :tr, :tc, :ts_count,
                        now()
                    )
                    ON CONFLICT ON CONSTRAINT uq_competitor_month
                    DO UPDATE SET
                        posts_count = EXCLUDED.posts_count,
                        total_reactions = EXCLUDED.total_reactions,
                        total_comments = EXCLUDED.total_comments,
                        total_shares = EXCLUDED.total_shares,
                        computed_at = now()
                    RETURNING id
                    """
                ),
                {
                    "cid": competitor_id,
                    "ms": snap.month_start,
                    "pc": agg[0],
                    "tr": agg[1],
                    "tc": agg[2],
                    "ts_count": agg[3],
                },
            )
        ).scalar()

        results.append(
            IngestProfileResult(
                handle=snap.handle,
                platform=snap.platform,
                competitor_id=competitor_id,
                posts_upserted=posts_upserted,
                metric_row_id=metric_id,
            )
        )

    await db.commit()
    return IngestMonthlySnapshotResponse(
        scraped_at=scraped_at,
        profiles_processed=len(body.profiles),
        posts_upserted_total=posts_total,
        results=results,
    )
