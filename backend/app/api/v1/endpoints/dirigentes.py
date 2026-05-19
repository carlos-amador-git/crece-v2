from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.scope import assert_dirigente_access
from app.core.security import Role, RoleChecker, get_current_user, hash_password
from app.models.dirigente import Dirigente, DirigenteSyncStatus
from app.models.social import DataSource, Platform, SocialPost, SocialProfile, SocialProfileSnapshot
from app.models.user import User
from app.schemas.dirigente import (
    DiagnosticoResponse,
    DirigenteCreate,
    DirigenteResponse,
    DirigenteUpdate,
    FlashAnalysisResponse,
    OnboardingProgressResponse,
    OnboardingProgressStep,
    OnboardingRequest,
    OnboardingResponse,
    SocialSummary,
)
from app.services.actividad_alineada import (
    compute_actividad_alineada,
)
from app.services.diagnostico import calculate_ipd

router = APIRouter()


@router.get("/")
async def list_dirigentes(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    estado: str | None = None,
    partido: str | None = None,
    search: str | None = None,
) -> dict:
    """List dirigentes with IPD scores and platform counts.

    If user has dirigente_id, only show their own dirigente.
    Admin can switch org via X-Org-Id header.
    """
    query = select(Dirigente)
    count_query = select(func.count(Dirigente.id))

    # Resolve effective org_id: admin can switch via X-Org-Id header
    effective_org_id: int | None = getattr(current_user, "org_id", None)
    if current_user.role == "admin":
        header_org = request.headers.get("x-org-id")
        if header_org and header_org.isdigit():
            effective_org_id = int(header_org)

    # Auto-scope: dirigente users see only their own; other users see their org's dirigentes
    if current_user.dirigente_id is not None:
        query = query.where(Dirigente.id == current_user.dirigente_id)
        count_query = count_query.where(Dirigente.id == current_user.dirigente_id)
    elif effective_org_id is not None:
        query = query.where(Dirigente.org_id == effective_org_id)
        count_query = count_query.where(Dirigente.org_id == effective_org_id)

    if estado:
        query = query.where(Dirigente.estado == estado)
        count_query = count_query.where(Dirigente.estado == estado)
    if partido:
        query = query.where(Dirigente.partido == partido)
        count_query = count_query.where(Dirigente.partido == partido)
    if search:
        query = query.where(Dirigente.full_name.ilike(f"%{search}%"))
        count_query = count_query.where(Dirigente.full_name.ilike(f"%{search}%"))

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(Dirigente.full_name).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = list(result.scalars().all())

    # F-PERF-01 fix (audit 2026-05-15): batched query para platform_count.
    # Antes hacíamos 1 query por dirigente dentro del loop (N+1). Ahora 1 sola
    # query agregada para los IDs paginados. calculate_ipd internamente sigue
    # con queries por dirigente — refactor anidado queda para sprint dedicado
    # si el throughput lo justifica (medible vía /api/v1/dirigentes/ EXPLAIN).
    dirigente_ids = [d.id for d in items]
    platform_counts: dict[int, int] = {}
    if dirigente_ids:
        counts_result = await db.execute(
            select(SocialProfile.dirigente_id, func.count(SocialProfile.id))
            .where(SocialProfile.dirigente_id.in_(dirigente_ids))
            .group_by(SocialProfile.dirigente_id)
        )
        platform_counts = {row[0]: row[1] for row in counts_result.all()}

    # Enrich each dirigente with IPD and platform count
    enriched = []
    for d in items:
        base = DirigenteResponse.model_validate(d).model_dump()
        try:
            ipd = await calculate_ipd(db, d)
            base["ipd_score"] = ipd.ipd_score
            base["platform_coverage"] = ipd.platform_coverage
        except Exception:
            base["ipd_score"] = 0.0
            base["platform_coverage"] = 0.0

        base["platform_count"] = platform_counts.get(d.id, 0)
        enriched.append(base)

    return {
        "items": enriched,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if total > 0 else 0,
    }


@router.get("/{dirigente_id}")
async def get_dirigente(
    dirigente_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Get a single dirigente by ID with enriched data for the dashboard.

    Scope enforcement (P0 — data leak fix 2026-04-14):
    - Viewer con ``dirigente_id`` asignado sólo puede ver su propio dirigente.
    - Non-admin sólo puede ver dirigentes de su misma ``org_id``.
    - Admin bypasses ambos checks (puede cambiar org vía X-Org-Id a futuro).

    Patrón idéntico al ya aplicado en ``/flash-analysis`` y ``/crecimiento``.
    """
    from datetime import UTC, datetime, timedelta

    # Viewer (o cualquier user con dirigente_id) sólo ve el suyo.
    if (
        current_user.dirigente_id is not None
        and current_user.dirigente_id != dirigente_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este dirigente",
        )

    result = await db.execute(select(Dirigente).where(Dirigente.id == dirigente_id))
    dirigente = result.scalar_one_or_none()
    if dirigente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dirigente not found")

    # Org-level isolation para non-admin.
    if (
        current_user.role != "admin"
        and dirigente.org_id is not None
        and current_user.org_id is not None
        and dirigente.org_id != current_user.org_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dirigente pertenece a otra organizacion",
        )

    # Base response
    base = DirigenteResponse.model_validate(dirigente).model_dump()

    # Enrich: IPD breakdown from diagnostico
    try:
        ipd = await calculate_ipd(db, dirigente)
        base["ipd_score"] = ipd.ipd_score
        base["ipd_breakdown"] = ipd.platform_scores
    except Exception:
        base["ipd_score"] = 0.0
        base["ipd_breakdown"] = {}

    # Enrich: stats (7d)
    seven_days_ago = datetime.now(UTC) - timedelta(days=7)
    datetime.now(UTC) - timedelta(days=30)

    profiles_result = await db.execute(
        select(SocialProfile).where(SocialProfile.dirigente_id == dirigente_id)
    )
    profiles = list(profiles_result.scalars().all())
    profile_ids = [p.id for p in profiles]

    total_posts_7d = 0
    total_engagement_7d = 0.0
    sentiment_sum = 0.0

    if profile_ids:
        # Fix S2 (audit 2026-05-15 · Gemini A1.4): la columna engagement_rate
        # quedaba en 0 porque los scrapers no la pueblan (engagement_rate
        # típicamente = interacciones / followers, requiere followers_at_post_time
        # que no capturamos). El UI trata total_engagement_7d como TOTAL de
        # interacciones (compara contra 5000 como threshold), no como rate. Por
        # eso sumamos likes+comments+shares directos. Saymi tenía 30 posts con
        # 8086 interacciones reales mostrando "0" antes de este fix.
        stats_r = await db.execute(
            select(
                func.count(SocialPost.id),
                func.coalesce(
                    func.sum(SocialPost.likes + SocialPost.comments + SocialPost.shares),
                    0,
                ),
                func.avg(SocialPost.sentiment_score),
            ).where(
                SocialPost.profile_id.in_(profile_ids),
                SocialPost.published_at >= seven_days_ago,
            )
        )
        row = stats_r.one()
        total_posts_7d = int(row[0])
        total_engagement_7d = float(row[1]) if row[1] else 0.0
        sentiment_sum = float(row[2]) if row[2] else 0.5

    sum(p.followers_count for p in profiles)

    # D-23-G' · KPI Actividad Política Alineada (reemplaza flip de sentimiento)
    # D-23-H · Phase B · doble métrica (default + ajustado) · vista personal vs comparativa
    actividad_default = await compute_actividad_alineada(db, dirigente, days=7, modo="default")
    actividad_ajustada = await compute_actividad_alineada(db, dirigente, days=7, modo="ajustado")

    base["stats"] = {
        "total_posts_7d": total_posts_7d,
        "total_engagement_7d": round(total_engagement_7d, 4),
        "sentiment_avg_7d": round(sentiment_sum, 2),  # se preserva como subline informacional · sin flip
        "follower_growth_30d": 0,  # Would need historical data
        # Backward compat · clientes Phase A leen `actividad_alineada` (= default)
        "actividad_alineada": actividad_default,
        # Phase B · doble métrica explícita
        "actividad_alineada_default": actividad_default,
        "actividad_alineada_ajustada": actividad_ajustada,
        "pesos_target_politico": dirigente.pesos_target_politico,
        "pesos_last_modified_at": (
            dirigente.pesos_last_modified_at.isoformat()
            if dirigente.pesos_last_modified_at
            else None
        ),
    }

    # Enrich: social_accounts (what frontend expects)
    base["social_accounts"] = [
        {
            "platform": p.platform.value.lower(),
            "handle": p.handle,
            "followers": p.followers_count,
            "url": p.url,
        }
        for p in profiles
    ]

    # Enrich: recent_posts
    if profile_ids:
        posts_r = await db.execute(
            select(SocialPost)
            .where(SocialPost.profile_id.in_(profile_ids))
            .order_by(SocialPost.published_at.desc())
            .limit(10)
        )
        posts = list(posts_r.scalars().all())
        base["recent_posts"] = [
            {
                "id": post.id,
                "content": post.content,
                "platform": next(
                    (p.platform.value.lower() for p in profiles if p.id == post.profile_id),
                    "unknown",
                ),
                "published_at": post.published_at.isoformat() if post.published_at else None,
                "likes": post.likes,
                "comments": post.comments,
                "shares": post.shares,
                "engagement_rate": post.engagement_rate,
                "sentiment_score": post.sentiment_score,
                "sentiment_label": post.sentiment_label.value if post.sentiment_label else None,
                "media_urls": post.media_urls,
                "url": (
                    (post.raw_data or {}).get("url")
                    or (post.raw_data or {}).get("post_url")
                    or (post.raw_data or {}).get("topLevelUrl")
                ),
            }
            for post in posts
        ]
    else:
        base["recent_posts"] = []

    base["secciones"] = []

    return base


@router.post(
    "/",
    response_model=DirigenteResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST]))],
)
async def create_dirigente(
    payload: DirigenteCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Dirigente:
    """Create a new dirigente."""
    dirigente = Dirigente(**payload.model_dump())
    db.add(dirigente)
    await db.flush()
    await db.refresh(dirigente)
    return dirigente


@router.patch(
    "/{dirigente_id}",
    response_model=DirigenteResponse,
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST]))],
)
async def update_dirigente(
    dirigente_id: int,
    payload: DirigenteUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Dirigente:
    """Update an existing dirigente."""
    result = await db.execute(select(Dirigente).where(Dirigente.id == dirigente_id))
    dirigente = result.scalar_one_or_none()
    if dirigente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dirigente not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(dirigente, field, value)

    await db.flush()
    await db.refresh(dirigente)
    return dirigente


class PesosUpdate(BaseModel):
    """D-23-H · Phase B · pesos editables target_politico.

    Cap 0.5-1.5 enforced en CHECK constraint BD + aquí en validación
    aplicación. Default neutro = 1.0 (sin ajuste).
    """

    oficialismo: float = Field(..., ge=0.5, le=1.5)
    oposicion: float = Field(..., ge=0.5, le=1.5)
    propio: float = Field(..., ge=0.5, le=1.5)
    personal: float = Field(..., ge=0.5, le=1.5)

    @field_validator("oficialismo", "oposicion", "propio", "personal")
    @classmethod
    def _round_to_2(cls, v: float) -> float:
        # Reduce ruido de floats. UI usa 5 puntos discretos
        # (0.5, 0.75, 1.0, 1.25, 1.5) pero aceptamos cualquier float en rango.
        return round(float(v), 2)


@router.patch(
    "/{dirigente_id}/pesos",
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST, Role.VIEWER]))],
)
async def update_dirigente_pesos(
    dirigente_id: int,
    payload: PesosUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Actualiza los pesos por categoría target_politico de un dirigente.

    D-23-H · Phase B · Panel Editable de Evaluación · Palanca 1.

    Permisos: ADMIN/ANALYST puede editar cualquier dirigente · VIEWER solo
    si su `dirigente_id == dirigente_id` (vista personal).

    Audit: actualiza ``pesos_last_modified_by`` y ``pesos_last_modified_at``.

    Retorna ambos KPIs recalculados (default + ajustado) para que el cliente
    refresque la doble métrica sin un GET adicional.
    """
    result = await db.execute(select(Dirigente).where(Dirigente.id == dirigente_id))
    dirigente = result.scalar_one_or_none()
    if dirigente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dirigente not found")

    # VIEWER solo puede editar sus propios pesos.
    if current_user.role == Role.VIEWER and current_user.dirigente_id != dirigente_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para editar pesos de otro dirigente",
        )

    dirigente.pesos_target_politico = payload.model_dump()
    dirigente.pesos_last_modified_by = current_user.id
    dirigente.pesos_last_modified_at = datetime.now(UTC)

    await db.flush()
    await db.refresh(dirigente)

    actividad_default = await compute_actividad_alineada(
        db, dirigente, days=7, modo="default"
    )
    actividad_ajustada = await compute_actividad_alineada(
        db, dirigente, days=7, modo="ajustado"
    )

    return {
        "pesos_target_politico": dirigente.pesos_target_politico,
        "pesos_last_modified_at": dirigente.pesos_last_modified_at.isoformat(),
        "pesos_last_modified_by": dirigente.pesos_last_modified_by,
        "actividad_alineada_default": actividad_default,
        "actividad_alineada_ajustada": actividad_ajustada,
    }


@router.delete(
    "/{dirigente_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RoleChecker([Role.ADMIN]))],
)
async def delete_dirigente(
    dirigente_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a dirigente and all related data."""
    result = await db.execute(select(Dirigente).where(Dirigente.id == dirigente_id))
    dirigente = result.scalar_one_or_none()
    if dirigente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dirigente not found")
    await db.delete(dirigente)


@router.get("/{dirigente_id}/diagnostico", response_model=DiagnosticoResponse)
async def get_diagnostico(
    dirigente_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> DiagnosticoResponse:
    """Get the aggregated digital penetration index (IPD) for a dirigente."""
    await assert_dirigente_access(db, current_user, dirigente_id)
    result = await db.execute(select(Dirigente).where(Dirigente.id == dirigente_id))
    dirigente = result.scalar_one_or_none()
    if dirigente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dirigente not found")
    return await calculate_ipd(db, dirigente)


@router.get("/{dirigente_id}/flash-analysis", response_model=FlashAnalysisResponse)
async def get_flash_analysis(
    dirigente_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    days: int = Query(7, ge=1, le=90, description="Ventana de analisis en dias"),
) -> FlashAnalysisResponse:
    """Flash Analysis: quick aggregated snapshot of a dirigente's digital presence.

    Pure SQL aggregations — no LLM call. Returns sentiment, engagement,
    top post, and a suggested action computed from data patterns.
    """
    from datetime import UTC, datetime, timedelta

    # Scope check: viewer users can only see their own dirigente
    if current_user.dirigente_id is not None and current_user.dirigente_id != dirigente_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este dirigente",
        )

    # Fetch dirigente
    result = await db.execute(select(Dirigente).where(Dirigente.id == dirigente_id))
    dirigente = result.scalar_one_or_none()
    if dirigente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dirigente not found")

    # Fetch profiles
    profiles_result = await db.execute(
        select(SocialProfile).where(SocialProfile.dirigente_id == dirigente_id)
    )
    profiles = list(profiles_result.scalars().all())
    profile_ids = [p.id for p in profiles]

    followers_total = sum(p.followers_count for p in profiles)
    platforms_active = len(profiles)

    now = datetime.now(UTC)
    period_start = now - timedelta(days=days)
    prev_period_start = period_start - timedelta(days=days)
    periodo = f"Ultimos {days} dias"

    # Defaults for empty data
    total_posts = 0
    avg_sentiment = 0.0
    engagement_avg = 0.0
    engagement_delta = 0.0
    top_post_content: str | None = None
    top_post_likes = 0

    if profile_ids:
        # Current period aggregations
        stats_r = await db.execute(
            select(
                func.count(SocialPost.id),
                func.avg(SocialPost.sentiment_score),
                func.avg(SocialPost.engagement_rate),
            ).where(
                SocialPost.profile_id.in_(profile_ids),
                SocialPost.published_at >= period_start,
            )
        )
        row = stats_r.one()
        total_posts = int(row[0])
        avg_sentiment = round(float(row[1]), 3) if row[1] is not None else 0.0
        engagement_avg = round(float(row[2]), 3) if row[2] is not None else 0.0

        # Previous period engagement for delta calculation
        prev_r = await db.execute(
            select(func.avg(SocialPost.engagement_rate)).where(
                SocialPost.profile_id.in_(profile_ids),
                SocialPost.published_at >= prev_period_start,
                SocialPost.published_at < period_start,
            )
        )
        prev_engagement = prev_r.scalar_one()
        if prev_engagement is not None and float(prev_engagement) > 0:
            engagement_delta = round(
                ((engagement_avg - float(prev_engagement)) / float(prev_engagement)) * 100, 1
            )

        # Top post by likes in current period
        top_r = await db.execute(
            select(SocialPost.content, SocialPost.likes)
            .where(
                SocialPost.profile_id.in_(profile_ids),
                SocialPost.published_at >= period_start,
            )
            .order_by(SocialPost.likes.desc())
            .limit(1)
        )
        top_row = top_r.one_or_none()
        if top_row is not None:
            top_post_content = top_row[0]
            top_post_likes = int(top_row[1])

    # Sentiment label
    if avg_sentiment > 0.1:
        sentiment_label = "Positivo"
    elif avg_sentiment < -0.1:
        sentiment_label = "Negativo"
    else:
        sentiment_label = "Neutral"

    # Suggested action logic
    if total_posts == 0:
        suggested_action = "Sin publicaciones en el periodo. Activar calendario editorial."
    elif avg_sentiment < -0.2:
        suggested_action = (
            "Atencion: sentimiento negativo predominante. "
            "Considerar respuesta o reposicionamiento."
        )
    elif engagement_avg < 2.0:
        suggested_action = (
            "El engagement esta por debajo del promedio. "
            "Incrementar contenido interactivo."
        )
    elif avg_sentiment > 0.3 and engagement_avg > 3.0:
        suggested_action = "Buen momento. Capitalizar con contenido de valor."
    else:
        suggested_action = "Rendimiento estable. Mantener frecuencia de publicacion."

    return FlashAnalysisResponse(
        dirigente_name=dirigente.full_name,
        periodo=periodo,
        total_posts=total_posts,
        avg_sentiment=avg_sentiment,
        sentiment_label=sentiment_label,
        engagement_avg=engagement_avg,
        engagement_delta=engagement_delta,
        top_post_content=top_post_content,
        top_post_likes=top_post_likes,
        followers_total=followers_total,
        platforms_active=platforms_active,
        suggested_action=suggested_action,
    )


@router.get("/{dirigente_id}/social-summary", response_model=SocialSummary)
async def get_social_summary(
    dirigente_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> SocialSummary:
    """Get a social media summary for a dirigente across all platforms."""
    await assert_dirigente_access(db, current_user, dirigente_id)
    result = await db.execute(select(Dirigente).where(Dirigente.id == dirigente_id))
    dirigente = result.scalar_one_or_none()
    if dirigente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dirigente not found")

    profiles_result = await db.execute(
        select(SocialProfile).where(SocialProfile.dirigente_id == dirigente_id)
    )
    profiles = list(profiles_result.scalars().all())

    total_followers = sum(p.followers_count for p in profiles)
    total_posts = sum(p.posts_count for p in profiles)

    # Average engagement across all recent posts
    eng_result = await db.execute(
        select(func.avg(SocialPost.engagement_rate))
        .join(SocialProfile, SocialPost.profile_id == SocialProfile.id)
        .where(SocialProfile.dirigente_id == dirigente_id)
    )
    avg_engagement = float(eng_result.scalar_one() or 0.0)

    # Sentiment breakdown
    sent_result = await db.execute(
        select(SocialPost.sentiment_label, func.count(SocialPost.id))
        .join(SocialProfile, SocialPost.profile_id == SocialProfile.id)
        .where(
            SocialProfile.dirigente_id == dirigente_id,
            SocialPost.sentiment_label.is_not(None),
        )
        .group_by(SocialPost.sentiment_label)
    )
    sentiment_rows = sent_result.all()
    total_sentiment = sum(row[1] for row in sentiment_rows) or 1
    sentiment_breakdown = {
        row[0].value: round(row[1] / total_sentiment, 4) for row in sentiment_rows
    }

    # Top platforms by followers
    top_platforms = sorted(
        [
            {
                "platform": p.platform.value,
                "followers": p.followers_count,
                "posts": p.posts_count,
            }
            for p in profiles
        ],
        key=lambda x: x["followers"],
        reverse=True,
    )

    return SocialSummary(
        dirigente_id=dirigente_id,
        total_followers=total_followers,
        total_posts=total_posts,
        avg_engagement=round(avg_engagement, 4),
        sentiment_breakdown=sentiment_breakdown,
        top_platforms=top_platforms,
    )


# ─────────────────────────────────────────────────────────────
# S5 — Onboarding wizard endpoints
# ─────────────────────────────────────────────────────────────


@router.post(
    "/onboard",
    response_model=OnboardingResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker([Role.ADMIN]))],
)
async def onboard_dirigente(
    payload: OnboardingRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> OnboardingResponse:
    """S5.3a — Crear User + Dirigente + SocialProfiles en una transacción.

    Retorna 201 con `sync_status='pending'` inmediatamente (D-S5-01). Dispara
    la Celery chain `onboard_dirigente_chain` para scrape inicial → NLP → IPD,
    pero NO espera a que termine — el wizard UI consulta `/onboarding-progress`.
    """
    from datetime import UTC, datetime

    # 1. Reject duplicate email
    existing_user = await db.execute(select(User).where(User.email == payload.email))
    if existing_user.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Usuario con email {payload.email} ya existe",
        )

    # 2. Default org: admin's own org, or id=3 (MC CDMX root) per D16
    org_id = payload.org_id or current_user.org_id or 3

    # 3. Create Dirigente (without sync_status default so we override it)
    dirigente = Dirigente(
        full_name=payload.full_name,
        cargo=payload.cargo,
        partido=payload.partido,
        estado=payload.estado,
        municipio=payload.municipio,
        seccion_electoral=payload.seccion_electoral,
        org_id=org_id,
        sync_status=DirigenteSyncStatus.PENDING,
        sync_updated_at=datetime.now(UTC),
    )
    db.add(dirigente)
    await db.flush()  # get dirigente.id

    # 4. Create User for the new dirigente with role=cliente (viewer)
    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=Role.VIEWER,
        is_active=True,
        org_id=org_id,
        dirigente_id=dirigente.id,
    )
    db.add(user)
    await db.flush()

    # 5. Create SocialProfiles (one per handle)
    profiles_created = 0
    for h in payload.handles:
        try:
            plat_enum = Platform[h.platform]
        except KeyError:
            continue  # ignore invalid platform silently (validated by Pydantic Literal)
        profile = SocialProfile(
            dirigente_id=dirigente.id,
            platform=plat_enum,
            handle=h.handle,
            url=h.url,
            followers_count=0,
            following_count=0,
            posts_count=0,
        )
        db.add(profile)
        profiles_created += 1

    await db.flush()
    await db.commit()
    await db.refresh(dirigente)

    # 6. Fire-and-forget Celery chain (S5.3b). If the worker is down,
    # the chain enqueue fails silently and sync_status stays 'pending'.
    task_id: str | None = None
    try:
        from app.workers.tasks import onboard_dirigente_chain

        result = onboard_dirigente_chain.delay(dirigente.id)
        task_id = str(result.id)
        dirigente.sync_task_id = task_id
        await db.flush()
        await db.commit()
    except Exception:
        # Don't block the response on a worker outage
        pass

    return OnboardingResponse(
        dirigente_id=dirigente.id,
        user_id=user.id,
        sync_status=dirigente.sync_status.value,
        task_id=task_id,
        profiles_created=profiles_created,
    )


@router.get(
    "/{dirigente_id}/onboarding-progress",
    response_model=OnboardingProgressResponse,
)
async def get_onboarding_progress(
    dirigente_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
) -> OnboardingProgressResponse:
    """S5.4 — Poll del estado de onboarding."""
    result = await db.execute(select(Dirigente).where(Dirigente.id == dirigente_id))
    dirigente = result.scalar_one_or_none()
    if dirigente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dirigente not found")

    status_map = {
        DirigenteSyncStatus.PENDING: 0,
        DirigenteSyncStatus.SCRAPING: 25,
        DirigenteSyncStatus.ANALYZING: 55,
        DirigenteSyncStatus.CALCULATING_IPD: 85,
        DirigenteSyncStatus.READY: 100,
        DirigenteSyncStatus.ERROR: 0,
    }
    progress_pct = status_map.get(dirigente.sync_status, 0)

    def _step_status(step_order: int, current_order: int) -> str:
        if dirigente.sync_status == DirigenteSyncStatus.ERROR and step_order == current_order:
            return "error"
        if step_order < current_order:
            return "done"
        if step_order == current_order:
            return "running" if dirigente.sync_status != DirigenteSyncStatus.READY else "done"
        return "pending"

    order = {
        DirigenteSyncStatus.PENDING: 0,
        DirigenteSyncStatus.SCRAPING: 1,
        DirigenteSyncStatus.ANALYZING: 2,
        DirigenteSyncStatus.CALCULATING_IPD: 3,
        DirigenteSyncStatus.READY: 4,
        DirigenteSyncStatus.ERROR: -1,
    }
    current_order = order.get(dirigente.sync_status, 0)

    steps = [
        OnboardingProgressStep(
            name="scraping",
            status=_step_status(1, current_order),  # type: ignore[arg-type]
        ),
        OnboardingProgressStep(
            name="analyzing",
            status=_step_status(2, current_order),  # type: ignore[arg-type]
        ),
        OnboardingProgressStep(
            name="calculating_ipd",
            status=_step_status(3, current_order),  # type: ignore[arg-type]
        ),
        OnboardingProgressStep(
            name="ready",
            status="done" if dirigente.sync_status == DirigenteSyncStatus.READY else "pending",
        ),
    ]

    return OnboardingProgressResponse(
        dirigente_id=dirigente.id,
        sync_status=dirigente.sync_status.value,
        task_id=dirigente.sync_task_id,
        error=dirigente.sync_error,
        progress_pct=progress_pct,
        steps=steps,
        updated_at=dirigente.sync_updated_at,
    )


# ─────────────────────────────────────────────────────────────
# Cirugía dirigente — crecimiento por red con semáforo
# ─────────────────────────────────────────────────────────────

_FRESH_STALENESS_HOURS = 48


def _growth_status(delta_pct: float | None) -> str:
    if delta_pct is None:
        return "desconocido"
    if delta_pct > 1.0:
        return "verde"
    if delta_pct < -1.0:
        return "rojo"
    return "ambar"


@router.get("/{dirigente_id}/crecimiento")
async def get_crecimiento(
    dirigente_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Crecimiento de followers por red — series 7d/30d/90d + semáforo 30d/30d.

    Consume ``social_profile_snapshots`` (denormalizada por ``platform`` + ``org_id``
    + ``dirigente_id``). Calcula deltas (followers_hoy − followers_hace_Nd) y
    semáforo comparando últimos 30d vs 30d anteriores. Marca ``stale_manual=true``
    si el perfil es ``data_source='manual_host_ingest'`` y ``last_manual_update``
    supera las 48h — alerta de deuda de frescura.
    """
    from datetime import UTC, datetime, timedelta

    # Scope check — viewer solo ve su propio dirigente
    if current_user.dirigente_id is not None and current_user.dirigente_id != dirigente_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este dirigente",
        )

    result = await db.execute(select(Dirigente).where(Dirigente.id == dirigente_id))
    dirigente = result.scalar_one_or_none()
    if dirigente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dirigente not found")

    profiles_r = await db.execute(
        select(SocialProfile).where(SocialProfile.dirigente_id == dirigente_id)
    )
    profiles = list(profiles_r.scalars().all())

    now = datetime.now(UTC)
    windows = {"7d": 7, "30d": 30, "90d": 90}

    platforms_out: list[dict] = []

    for profile in profiles:
        deltas: dict[str, float | None] = {}
        for label, days in windows.items():
            past_cut = now - timedelta(days=days)
            past_r = await db.execute(
                select(SocialProfileSnapshot.followers_count)
                .where(
                    SocialProfileSnapshot.profile_id == profile.id,
                    SocialProfileSnapshot.taken_at <= past_cut,
                )
                .order_by(SocialProfileSnapshot.taken_at.desc())
                .limit(1)
            )
            past_followers = past_r.scalar_one_or_none()
            if past_followers is None or past_followers == 0:
                deltas[label] = None
                continue
            delta_pct = ((profile.followers_count - past_followers) / past_followers) * 100
            deltas[label] = round(delta_pct, 2)

        # Semáforo: 30d actual vs 30d anterior (medidos como avg en ventana)
        cur_start = now - timedelta(days=30)
        prev_start = now - timedelta(days=60)
        cur_r = await db.execute(
            select(func.avg(SocialProfileSnapshot.followers_count)).where(
                SocialProfileSnapshot.profile_id == profile.id,
                SocialProfileSnapshot.taken_at >= cur_start,
            )
        )
        prev_r = await db.execute(
            select(func.avg(SocialProfileSnapshot.followers_count)).where(
                SocialProfileSnapshot.profile_id == profile.id,
                SocialProfileSnapshot.taken_at >= prev_start,
                SocialProfileSnapshot.taken_at < cur_start,
            )
        )
        cur_avg = cur_r.scalar_one_or_none()
        prev_avg = prev_r.scalar_one_or_none()
        if cur_avg is not None and prev_avg is not None and float(prev_avg) > 0:
            trend_30v30 = round(
                ((float(cur_avg) - float(prev_avg)) / float(prev_avg)) * 100, 2
            )
        else:
            trend_30v30 = None
        semaforo = _growth_status(trend_30v30)

        # Deuda de frescura
        stale_manual = False
        if profile.data_source == DataSource.MANUAL_HOST_INGEST:
            if profile.last_manual_update is None:
                stale_manual = True
            else:
                age = now - profile.last_manual_update
                stale_manual = age > timedelta(hours=_FRESH_STALENESS_HOURS)

        platforms_out.append(
            {
                "platform": profile.platform.value,
                "handle": profile.handle,
                "followers_now": profile.followers_count,
                "delta_pct": deltas,
                "trend_30v30_pct": trend_30v30,
                "semaforo": semaforo,
                "data_source": profile.data_source.value,
                "last_manual_update": (
                    profile.last_manual_update.isoformat()
                    if profile.last_manual_update
                    else None
                ),
                "stale_manual": stale_manual,
            }
        )

    # Serie temporal para charts (union de todos los snapshots de todos los perfiles)
    profile_ids = [p.id for p in profiles]
    series_points: list[dict] = []
    if profile_ids:
        since = now - timedelta(days=90)
        snapshots_r = await db.execute(
            select(
                SocialProfileSnapshot.taken_at,
                SocialProfileSnapshot.platform,
                SocialProfileSnapshot.followers_count,
                SocialProfileSnapshot.posts_count,
            )
            .where(
                SocialProfileSnapshot.profile_id.in_(profile_ids),
                SocialProfileSnapshot.taken_at >= since,
            )
            .order_by(SocialProfileSnapshot.taken_at.asc())
        )
        for row in snapshots_r.all():
            series_points.append(
                {
                    "taken_at": row[0].isoformat(),
                    "platform": row[1].value,
                    "followers": int(row[2]),
                    "posts": int(row[3]),
                }
            )

    return {
        "dirigente_id": dirigente_id,
        "platforms": platforms_out,
        "series": series_points,
    }
