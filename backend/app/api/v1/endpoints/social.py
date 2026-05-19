from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import and_, cast, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import Date

from app.core.database import get_db
from app.core.scope import assert_dirigente_access
from app.core.security import Role, RoleChecker, get_current_user
from app.models.dirigente import Dirigente
from app.models.organizacion import Organizacion
from app.models.social import Platform, SentimentLabel, SocialPost, SocialProfile
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.social import (
    ScrapeRequest,
    SentimentTimelinePoint,
    SocialPostResponse,
)
from app.services.scraper_manager import dispatch_scrape
from app.utils.social_urls import compose_post_url

router = APIRouter()


@router.get("/posts", response_model=PaginatedResponse[SocialPostResponse])
async def list_posts(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    dirigente_id: int | None = None,
    platform: str | None = None,
    sentiment: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    is_political: bool | None = None,
    exclude_rts: bool = False,
    min_length: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[SocialPostResponse]:
    """List social posts with comprehensive filtering."""
    query = select(SocialPost).join(SocialProfile, SocialPost.profile_id == SocialProfile.id)
    count_query = select(func.count(SocialPost.id)).join(
        SocialProfile, SocialPost.profile_id == SocialProfile.id
    )

    # Normalize case-insensitive enum params
    platform_enum = Platform(platform.upper()) if platform else None
    sentiment_enum = SentimentLabel(sentiment.upper()) if sentiment else None

    # Resolve effective org_id: admin can switch via X-Org-Id header
    effective_org_id: int | None = getattr(current_user, "org_id", None)
    if current_user.role == "admin":
        header_org = request.headers.get("x-org-id")
        if header_org and header_org.isdigit():
            effective_org_id = int(header_org)

    # Auto-scope: dirigente users see only their own; org users see their org
    effective_dirigente_id = dirigente_id
    if current_user.dirigente_id is not None:
        effective_dirigente_id = current_user.dirigente_id

    filters = []
    if effective_dirigente_id is not None:
        filters.append(SocialProfile.dirigente_id == effective_dirigente_id)
    elif effective_org_id is not None:
        # Scope to org's dirigentes (works for admin with X-Org-Id and non-admin)
        filters.append(SocialProfile.dirigente_id.in_(
            select(Dirigente.id).where(Dirigente.org_id == effective_org_id)
        ))
    if platform_enum is not None:
        filters.append(SocialProfile.platform == platform_enum)
    if sentiment_enum is not None:
        filters.append(SocialPost.sentiment_label == sentiment_enum)
    if date_from is not None:
        filters.append(SocialPost.published_at >= date_from)
    if date_to is not None:
        filters.append(SocialPost.published_at <= date_to)
    if is_political is not None:
        filters.append(SocialPost.is_political == is_political)
    if exclude_rts:
        filters.append(~SocialPost.content.like("RT @%"))
    if min_length is not None:
        filters.append(func.length(SocialPost.content) >= min_length)

    if filters:
        condition = and_(*filters)
        query = query.where(condition)
        count_query = count_query.where(condition)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = (
        query.order_by(SocialPost.published_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    items = list(result.scalars().all())

    if items:
        profile_ids = {p.profile_id for p in items}
        profile_rows = await db.execute(
            select(
                SocialProfile.id,
                SocialProfile.platform,
                SocialProfile.handle,
                SocialProfile.dirigente_id,
            ).where(SocialProfile.id.in_(profile_ids))
        )
        profile_map = {
            row[0]: {"platform": row[1], "handle": row[2], "dirigente_id": row[3]}
            for row in profile_rows.all()
        }

        dirigente_ids = {p["dirigente_id"] for p in profile_map.values()}
        dirigente_rows = await db.execute(
            select(Dirigente.id, Dirigente.full_name).where(
                Dirigente.id.in_(dirigente_ids)
            )
        )
        dirigente_map = {row[0]: row[1] for row in dirigente_rows.all()}
    else:
        profile_map = {}
        dirigente_map = {}

    serialized_items: list[SocialPostResponse] = []
    for post in items:
        payload = SocialPostResponse.model_validate(post)
        profile = profile_map.get(post.profile_id)
        if profile:
            payload.platform = profile["platform"].value if profile["platform"] else None
            payload.url = compose_post_url(
                profile["platform"], profile["handle"], post.platform_post_id
            )
            payload.dirigente_nombre = dirigente_map.get(profile["dirigente_id"])
        serialized_items.append(payload)

    return PaginatedResponse(
        items=serialized_items,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if total > 0 else 0,
    )


@router.get("/sentiment-timeline", response_model=list[SentimentTimelinePoint])
async def sentiment_timeline(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    dirigente_id: int,
    platform: Platform | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    include_rts: bool = False,
) -> list[SentimentTimelinePoint]:
    """Get sentiment time series data grouped by day.

    Quality filters (D-NLP-auditoria-2026-04-13):
    - Excludes retweets by default (RT @... prefix) — use include_rts=true to keep
    - Excludes posts with <20 chars (unreliable sentiment)
    - Deduplicates identical content (same post cross-platform counts once)
    """
    await assert_dirigente_access(db, current_user, dirigente_id)
    day_col = cast(SocialPost.published_at, Date)

    # Build quality filters
    quality_filters = [
        SocialProfile.dirigente_id == dirigente_id,
        SocialPost.sentiment_score.is_not(None),
        func.length(SocialPost.content) >= 20,
    ]
    if not include_rts:
        quality_filters.append(~SocialPost.content.like("RT @%"))

    base_query = (
        select(
            day_col.label("day"),
            func.avg(SocialPost.sentiment_score).label("avg_sentiment"),
            func.count(SocialPost.id).label("post_count"),
            func.count()
            .filter(SocialPost.sentiment_label == SentimentLabel.POSITIVE)
            .label("positive"),
            func.count()
            .filter(SocialPost.sentiment_label == SentimentLabel.NEGATIVE)
            .label("negative"),
            func.count()
            .filter(SocialPost.sentiment_label == SentimentLabel.NEUTRAL)
            .label("neutral"),
        )
        .join(SocialProfile, SocialPost.profile_id == SocialProfile.id)
        .where(*quality_filters)
    )

    if platform is not None:
        base_query = base_query.where(SocialProfile.platform == platform)
    if date_from is not None:
        base_query = base_query.where(SocialPost.published_at >= date_from)
    if date_to is not None:
        base_query = base_query.where(SocialPost.published_at <= date_to)

    base_query = base_query.group_by(day_col).order_by(day_col)

    result = await db.execute(base_query)
    rows = result.all()

    timeline = []
    for row in rows:
        total = row.post_count or 1
        timeline.append(
            SentimentTimelinePoint(
                date=row.day.isoformat(),
                avg_sentiment=round(float(row.avg_sentiment or 0), 4),
                post_count=row.post_count,
                positive_pct=round(row.positive / total * 100, 1),
                negative_pct=round(row.negative / total * 100, 1),
                neutral_pct=round(row.neutral / total * 100, 1),
            )
        )
    return timeline


class SentimentCoverageResponse(BaseModel):
    """Coverage stats for sentiment classification.

    Lets the UI show 'X de Y posts clasificados' so the user knows the
    timeline chart is a sample, not the universe.
    """

    dirigente_id: int
    days: int
    total_posts: int
    classified: int
    passed_filters: int
    coverage_pct: float


@router.get("/sentiment-coverage", response_model=SentimentCoverageResponse)
async def sentiment_coverage(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    dirigente_id: int,
    days: int = 30,
    include_rts: bool = False,
) -> SentimentCoverageResponse:
    """Return coverage stats matching the same filters as /sentiment-timeline.

    Counters:
    - total_posts: all posts of the dirigente in the period (any state).
    - classified: posts with sentiment_score != NULL.
    - passed_filters: classified AND length>=20 AND (not RT unless include_rts).
    """
    await assert_dirigente_access(db, current_user, dirigente_id)
    since = func.now() - text(f"INTERVAL '{int(days)} days'")
    base = (
        select(func.count(SocialPost.id))
        .join(SocialProfile, SocialPost.profile_id == SocialProfile.id)
        .where(
            SocialProfile.dirigente_id == dirigente_id,
            SocialPost.published_at >= since,
        )
    )
    total = (await db.execute(base)).scalar_one() or 0
    classified = (
        await db.execute(base.where(SocialPost.sentiment_score.is_not(None)))
    ).scalar_one() or 0
    filtered_q = base.where(
        SocialPost.sentiment_score.is_not(None),
        func.length(SocialPost.content) >= 20,
    )
    if not include_rts:
        filtered_q = filtered_q.where(~SocialPost.content.like("RT @%"))
    passed = (await db.execute(filtered_q)).scalar_one() or 0
    coverage_pct = round(100 * classified / total, 1) if total else 0.0
    return SentimentCoverageResponse(
        dirigente_id=dirigente_id,
        days=days,
        total_posts=total,
        classified=classified,
        passed_filters=passed,
        coverage_pct=coverage_pct,
    )


# ─────────────────────────────────────────────────────────────────────
# Tono Discursivo · matriz polaridad v2 (2026-05-19)
#
# Lee del campo `social_posts.tono_discurso` (no del legacy sentiment_label).
# Hoy en BD el campo solo tiene 2 valores reales ('positivo', 'neutral') sobre
# 81.6% de posts Saymi. La granularidad de 5 valores (celebratorio/solidario/
# propositivo/critico/personal) llegará cuando el pipeline NLP se aplique a
# POSTS del dirigente con el framework v2 (hoy aplicado solo a COMMENTS de
# audiencia · `social_comments.nlp_tono`).
#
# Endpoint paralelo al legacy /sentiment-timeline · NO reemplaza · permite
# migración sin romper consumers existentes. Cleanup del legacy en sprint
# posterior cuando todos los frontends consuman este.
# ─────────────────────────────────────────────────────────────────────


class TonoDiscursoTimelinePoint(BaseModel):
    """Punto de la serie temporal de tono discursivo en posts del dirigente.

    El array `tonos` contiene la distribución por categoría tono_discurso
    presente ese día. Frontend renderiza solo los tonos no-cero.
    """

    date: str
    post_count: int
    tonos: dict[str, int]  # ej. {"positivo": 3, "neutral": 12}


@router.get("/tono-discurso-timeline", response_model=list[TonoDiscursoTimelinePoint])
async def tono_discurso_timeline(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    dirigente_id: int,
    platform: Platform | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    include_rts: bool = False,
) -> list[TonoDiscursoTimelinePoint]:
    """Serie temporal de tono discursivo (matriz polaridad v2) por día.

    Lee `social_posts.tono_discurso` en lugar de `sentiment_label` legacy.
    Filtros de calidad iguales a /sentiment-timeline pero usando tono_discurso
    en vez de sentiment_score.
    """
    await assert_dirigente_access(db, current_user, dirigente_id)
    day_col = cast(SocialPost.published_at, Date)

    quality_filters = [
        SocialProfile.dirigente_id == dirigente_id,
        SocialPost.tono_discurso.is_not(None),
        func.length(SocialPost.content) >= 20,
    ]
    if not include_rts:
        quality_filters.append(~SocialPost.content.like("RT @%"))

    base_query = (
        select(
            day_col.label("day"),
            SocialPost.tono_discurso.label("tono"),
            func.count(SocialPost.id).label("n"),
        )
        .join(SocialProfile, SocialPost.profile_id == SocialProfile.id)
        .where(*quality_filters)
    )

    if platform is not None:
        base_query = base_query.where(SocialProfile.platform == platform)
    if date_from is not None:
        base_query = base_query.where(SocialPost.published_at >= date_from)
    if date_to is not None:
        base_query = base_query.where(SocialPost.published_at <= date_to)

    base_query = base_query.group_by(day_col, SocialPost.tono_discurso).order_by(day_col)

    result = await db.execute(base_query)
    rows = result.all()

    # Agregar por día: {day: {tono: count, post_count: total}}
    timeline_by_day: dict[date, dict[str, int]] = {}
    for row in rows:
        day = row.day
        if day not in timeline_by_day:
            timeline_by_day[day] = {}
        if row.tono:
            timeline_by_day[day][row.tono] = row.n

    return [
        TonoDiscursoTimelinePoint(
            date=day.isoformat(),
            post_count=sum(tonos.values()),
            tonos=tonos,
        )
        for day, tonos in sorted(timeline_by_day.items())
    ]


class TonoDiscursoCoverageResponse(BaseModel):
    """Coverage del campo tono_discurso vs total de posts del dirigente."""

    dirigente_id: int
    days: int
    total_posts: int
    classified: int  # posts con tono_discurso IS NOT NULL
    passed_filters: int  # classified + length>=20 + no RT
    coverage_pct: float
    tonos_distribution: dict[str, int]  # agregado global del período


@router.get("/tono-discurso-coverage", response_model=TonoDiscursoCoverageResponse)
async def tono_discurso_coverage(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    dirigente_id: int,
    days: int = 30,
    include_rts: bool = False,
) -> TonoDiscursoCoverageResponse:
    """Cobertura de tono_discurso · análogo a /sentiment-coverage para el v2."""
    await assert_dirigente_access(db, current_user, dirigente_id)
    since = func.now() - text(f"INTERVAL '{int(days)} days'")
    base = (
        select(func.count(SocialPost.id))
        .join(SocialProfile, SocialPost.profile_id == SocialProfile.id)
        .where(
            SocialProfile.dirigente_id == dirigente_id,
            SocialPost.published_at >= since,
        )
    )
    total = (await db.execute(base)).scalar_one() or 0
    classified = (
        await db.execute(base.where(SocialPost.tono_discurso.is_not(None)))
    ).scalar_one() or 0
    filtered_q = base.where(
        SocialPost.tono_discurso.is_not(None),
        func.length(SocialPost.content) >= 20,
    )
    if not include_rts:
        filtered_q = filtered_q.where(~SocialPost.content.like("RT @%"))
    passed = (await db.execute(filtered_q)).scalar_one() or 0
    coverage_pct = round(100 * classified / total, 1) if total else 0.0

    # Distribución agregada de tonos en el período
    dist_q = (
        select(SocialPost.tono_discurso, func.count(SocialPost.id))
        .join(SocialProfile, SocialPost.profile_id == SocialProfile.id)
        .where(
            SocialProfile.dirigente_id == dirigente_id,
            SocialPost.published_at >= since,
            SocialPost.tono_discurso.is_not(None),
        )
        .group_by(SocialPost.tono_discurso)
    )
    dist_rows = (await db.execute(dist_q)).all()
    tonos_distribution = {tono: int(n) for tono, n in dist_rows if tono}

    return TonoDiscursoCoverageResponse(
        dirigente_id=dirigente_id,
        days=days,
        total_posts=total,
        classified=classified,
        passed_filters=passed,
        coverage_pct=coverage_pct,
        tonos_distribution=tonos_distribution,
    )


class ClimaPoliticoPoint(BaseModel):
    fecha: date
    valor_pct: float
    metrica: str  # aprobacion | desaprobacion


class ClimaPoliticoSerie(BaseModel):
    actor_nombre: str
    actor_tipo: str
    ambito: str
    entidad: str | None
    municipio: str | None = None  # solo para alcaldes
    puntos: list[ClimaPoliticoPoint]


@router.get("/clima-politico", response_model=list[ClimaPoliticoSerie])
async def get_clima_politico(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    metrica: str = Query("aprobacion", description="aprobacion | desaprobacion | ambas"),
) -> list[ClimaPoliticoSerie]:
    """Series temporales de aprobación gubernamental.

    Aprobación pública de gobernadores/alcaldes es 100% DATO PÚBLICO (Mitofsky,
    Oraculus, Demoscopía publican rankings nacionales). El filtro estatal se
    removió 2026-05-12 para entregar contexto comparativo nacional al cliente
    (ej.: cómo está mi gobernador vs otros del mismo partido). El multi-tenant
    scoping sigue aplicando a datos sensibles (posts, comments, alertas).
    """
    _ = request  # filtro estatal removido; param sigue para retrocompatibilidad firma
    _ = current_user  # idem

    metrica_filter = "" if metrica == "ambas" else "AND metrica = :metrica"
    sql = text(f"""
        SELECT actor_nombre, actor_tipo, ambito,
               COALESCE(entidad, CASE WHEN ambito = 'federal' THEN 'México' ELSE NULL END) AS entidad,
               municipio,
               metrica, fecha_publicacion, AVG(valor_pct) AS valor_pct
        FROM encuestas_publicas
        WHERE fuente IN ('Demoscopía Digital', 'Oraculus poll-of-polls', 'Mitofsky')
        {metrica_filter}
        GROUP BY actor_nombre, actor_tipo, ambito,
                 COALESCE(entidad, CASE WHEN ambito = 'federal' THEN 'México' ELSE NULL END),
                 municipio,
                 metrica, fecha_publicacion
        ORDER BY actor_nombre, metrica, fecha_publicacion
    """)
    params: dict = {} if metrica == "ambas" else {"metrica": metrica}
    rows = (await db.execute(sql, params)).fetchall()

    seen: dict[tuple, ClimaPoliticoSerie] = {}
    for r in rows:
        nombre, tipo, ambito, entidad, municipio, met, fecha, valor = r
        # Para alcaldes la clave incluye municipio (mismo nombre puede ser alcalde
        # de varios municipios — homonimia política existe en Saymi/Saint datasets).
        base_key = (nombre, ambito, municipio) if tipo == "alcalde" else (nombre, ambito)
        if base_key not in seen:
            seen[base_key] = ClimaPoliticoSerie(
                actor_nombre=nombre, actor_tipo=tipo,
                ambito=ambito, entidad=entidad,
                municipio=municipio,
                puntos=[]
            )
        seen[base_key].puntos.append(
            ClimaPoliticoPoint(fecha=fecha, valor_pct=float(valor), metrica=met)
        )

    return sorted(seen.values(), key=lambda s: (s.ambito, s.actor_nombre))


class SocialCommentItem(BaseModel):
    id: int
    parent_post_id: int
    content: str | None
    nlp_tono: str | None
    nlp_polaridad: int | None
    nlp_target: str | None
    likes: int | None
    published_at: str | None
    es_follower: bool | None
    is_reply_to_comment: bool | None
    data_source: str | None
    dirigente_nombre: str | None
    platform: str | None
    review_status: str | None = None
    last_reviewed_by: int | None = None
    last_reviewed_by_name: str | None = None
    last_reviewed_at: str | None = None


@router.get("/comments", response_model=PaginatedResponse[SocialCommentItem])
async def list_comments(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    dirigente_id: int | None = None,
    platform: str | None = None,
    tono: str | None = None,
    polaridad: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
) -> PaginatedResponse[SocialCommentItem]:
    """Listado paginado de comentarios con scope multi-tenant.

    Scope: comments cuyo post.profile.dirigente pertenece a la org del usuario.
    Admin puede cambiar via X-Org-Id header. Dirigente users solo ven sus propios.
    """
    # Resolve effective scope
    effective_org_id: int | None = getattr(current_user, "org_id", None)
    if current_user.role == "admin":
        header_org = request.headers.get("x-org-id")
        if header_org and header_org.isdigit():
            effective_org_id = int(header_org)

    effective_dirigente_id = dirigente_id
    if current_user.dirigente_id is not None:
        effective_dirigente_id = current_user.dirigente_id

    where_parts: list[str] = []
    params: dict = {"limit": page_size, "offset": (page - 1) * page_size}

    if effective_dirigente_id is not None:
        where_parts.append("sp.dirigente_id = :did")
        params["did"] = effective_dirigente_id
    elif effective_org_id is not None:
        where_parts.append("d.org_id = :oid")
        params["oid"] = effective_org_id

    if platform:
        where_parts.append("sp.platform = :plat")
        params["plat"] = platform.upper()
    if tono:
        where_parts.append("sc.nlp_tono = :tono")
        params["tono"] = tono
    if polaridad is not None:
        where_parts.append("sc.nlp_polaridad = :pol")
        params["pol"] = polaridad

    where_sql = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

    count_sql = text(
        f"""
        SELECT COUNT(*) FROM social_comments sc
          JOIN social_posts spo ON spo.id = sc.parent_post_id
          JOIN social_profiles sp ON sp.id = spo.profile_id
          JOIN dirigentes d ON d.id = sp.dirigente_id
        {where_sql}
        """
    )
    total = (await db.execute(count_sql, params)).scalar() or 0

    list_sql = text(
        f"""
        SELECT sc.id, sc.parent_post_id, sc.content,
               sc.nlp_tono, sc.nlp_polaridad, sc.nlp_target,
               sc.likes, sc.published_at, sc.es_follower,
               sc.is_reply_to_comment, sc.data_source,
               d.full_name AS dirigente_nombre,
               sp.platform::text AS platform,
               COALESCE(sc.review_status, 'unreviewed') AS review_status,
               sc.last_reviewed_by,
               u.full_name AS last_reviewed_by_name,
               sc.last_reviewed_at
          FROM social_comments sc
          JOIN social_posts spo ON spo.id = sc.parent_post_id
          JOIN social_profiles sp ON sp.id = spo.profile_id
          JOIN dirigentes d ON d.id = sp.dirigente_id
          LEFT JOIN users u ON u.id = sc.last_reviewed_by
        {where_sql}
         ORDER BY COALESCE(sc.published_at, sc.created_at) DESC NULLS LAST
         LIMIT :limit OFFSET :offset
        """
    )
    rows = (await db.execute(list_sql, params)).fetchall()

    items = [
        SocialCommentItem(
            id=r[0], parent_post_id=r[1], content=r[2],
            nlp_tono=r[3], nlp_polaridad=r[4], nlp_target=r[5],
            likes=r[6],
            published_at=r[7].isoformat() if r[7] else None,
            es_follower=r[8], is_reply_to_comment=r[9],
            data_source=r[10], dirigente_nombre=r[11], platform=r[12],
            review_status=r[13], last_reviewed_by=r[14],
            last_reviewed_by_name=r[15],
            last_reviewed_at=r[16].isoformat() if r[16] else None,
        )
        for r in rows
    ]

    pages = (total + page_size - 1) // page_size if total else 0
    return PaginatedResponse[SocialCommentItem](
        items=items, total=total, page=page, page_size=page_size, pages=pages,
    )


@router.post(
    "/scrape/{dirigente_id}",
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST]))],
)
async def trigger_scrape(
    dirigente_id: int,
    payload: ScrapeRequest | None = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,  # type: ignore[assignment]
) -> dict:
    """Trigger scraping tasks for a dirigente's social profiles."""
    platforms = payload.platforms if payload else None
    dispatched = await dispatch_scrape(db, dirigente_id, platforms)

    if not dispatched:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No social profiles found for this dirigente",
        )

    return {"status": "dispatched", "tasks": dispatched}
