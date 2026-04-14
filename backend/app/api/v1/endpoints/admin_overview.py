"""Dashboard admin operativo MD Consultoría.

Vista de flota — NO muestra datos políticos del cliente.
Muestra: estado de flota, cola semanal, salud pipeline NLP, health del sistema.

Solo accesible role=admin.
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


class OrgStatus(BaseModel):
    org_id: int
    nombre: str
    dirigentes: int
    posts_total: int
    posts_clasificados: int
    coverage_framework_pct: float
    posts_nlp_procesados: int
    coverage_nlp_pct: float
    planes_total: int
    planes_con_tareas: int
    tareas_total: int


class PipelineNLP(BaseModel):
    posts_total: int
    procesados: int
    pendientes_sin_texto: int
    pendientes_con_texto: int
    coverage_pct: float


class ColaSemanal(BaseModel):
    posts_pendientes_clasificar: int
    posts_pendientes_whisper: int
    planes_sin_tareas_estructuradas: int
    dirigentes_sin_plan: int


class HealthCheck(BaseModel):
    db: str
    redis: str
    overall: str


class AdminOverview(BaseModel):
    flota: list[OrgStatus]
    pipeline_nlp: PipelineNLP
    cola_semanal: ColaSemanal
    health: HealthCheck
    divergencia_alerts: int
    totales: dict


def _require_admin(user: User) -> None:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo admin MD Consultoría",
        )


@router.get("/overview", response_model=AdminOverview)
async def admin_overview(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AdminOverview:
    _require_admin(current_user)

    flota_sql = text("""
        SELECT
            o.id AS org_id,
            o.nombre,
            COUNT(DISTINCT d.id) AS dirigentes,
            COUNT(p.id) AS posts_total,
            COUNT(p.id) FILTER (WHERE p.tono_discurso IS NOT NULL) AS posts_clasif,
            COUNT(p.id) FILTER (WHERE p.nlp_model_version = 'multi-model-v1') AS posts_nlp,
            COUNT(DISTINCT pl.id) AS planes_total,
            COUNT(DISTINCT pl.id) FILTER (WHERE pl.id IN (SELECT plan_id FROM plan_tareas)) AS planes_con_tareas,
            COUNT(DISTINCT t.id) AS tareas_total
        FROM organizaciones o
        LEFT JOIN dirigentes d ON d.org_id = o.id
        LEFT JOIN social_profiles sp ON sp.dirigente_id = d.id
        LEFT JOIN social_posts p ON p.profile_id = sp.id
        LEFT JOIN planes_ia pl ON pl.dirigente_id = d.id
        LEFT JOIN plan_tareas t ON t.plan_id = pl.id
        GROUP BY o.id, o.nombre
        ORDER BY o.id
    """)
    rows = (await db.execute(flota_sql)).fetchall()
    flota = [
        OrgStatus(
            org_id=r[0],
            nombre=r[1],
            dirigentes=r[2] or 0,
            posts_total=r[3] or 0,
            posts_clasificados=r[4] or 0,
            coverage_framework_pct=round(100.0 * (r[4] or 0) / r[3], 1) if r[3] else 0.0,
            posts_nlp_procesados=r[5] or 0,
            coverage_nlp_pct=round(100.0 * (r[5] or 0) / r[3], 1) if r[3] else 0.0,
            planes_total=r[6] or 0,
            planes_con_tareas=r[7] or 0,
            tareas_total=r[8] or 0,
        )
        for r in rows
    ]

    pipeline_sql = text("""
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE nlp_model_version = 'multi-model-v1') AS procesados,
            COUNT(*) FILTER (
                WHERE nlp_model_version IS NULL
                  AND (content IS NULL OR length(content) < 10)
            ) AS pend_sin_texto,
            COUNT(*) FILTER (
                WHERE nlp_model_version IS NULL
                  AND content IS NOT NULL
                  AND length(content) >= 10
            ) AS pend_con_texto
        FROM social_posts
    """)
    pr = (await db.execute(pipeline_sql)).first()
    total = pr[0] or 0
    proc = pr[1] or 0
    pipeline = PipelineNLP(
        posts_total=total,
        procesados=proc,
        pendientes_sin_texto=pr[2] or 0,
        pendientes_con_texto=pr[3] or 0,
        coverage_pct=round(100.0 * proc / total, 1) if total else 0.0,
    )

    cola_sql = text("""
        SELECT
            (SELECT COUNT(*) FROM social_posts
                WHERE tono_discurso IS NULL
                  AND content IS NOT NULL
                  AND length(content) >= 30
                  AND content NOT LIKE 'RT @%'
                  AND published_at >= NOW() - INTERVAL '30 days'
            ) AS pend_clasif,
            (SELECT COUNT(*) FROM social_posts p
                JOIN social_profiles sp ON sp.id = p.profile_id
                WHERE sp.platform::text = 'TIKTOK'
                  AND (p.content IS NULL OR length(p.content) < 10)
            ) AS pend_whisper,
            (SELECT COUNT(*) FROM planes_ia pl
                WHERE NOT EXISTS (SELECT 1 FROM plan_tareas t WHERE t.plan_id = pl.id)
            ) AS planes_sin_tareas,
            (SELECT COUNT(*) FROM dirigentes d
                WHERE NOT EXISTS (SELECT 1 FROM planes_ia pl WHERE pl.dirigente_id = d.id)
            ) AS dirig_sin_plan
    """)
    cr = (await db.execute(cola_sql)).first()
    cola = ColaSemanal(
        posts_pendientes_clasificar=cr[0] or 0,
        posts_pendientes_whisper=cr[1] or 0,
        planes_sin_tareas_estructuradas=cr[2] or 0,
        dirigentes_sin_plan=cr[3] or 0,
    )

    db_status = "OK"

    redis_status = "OK"
    try:
        from app.core.config import settings
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        await r.ping()
        await r.aclose()
    except Exception:
        redis_status = "WARN"

    overall = "OK" if db_status == "OK" and redis_status == "OK" else ("WARN" if db_status == "OK" else "ERROR")
    health = HealthCheck(db=db_status, redis=redis_status, overall=overall)

    div_count = 0

    totales_sql = text("""
        SELECT
            (SELECT COUNT(*) FROM organizaciones) AS orgs,
            (SELECT COUNT(*) FROM dirigentes) AS dirigentes,
            (SELECT COUNT(*) FROM social_posts) AS posts,
            (SELECT COUNT(*) FROM planes_ia) AS planes,
            (SELECT COUNT(*) FROM plan_tareas) AS tareas
    """)
    tr = (await db.execute(totales_sql)).first()
    totales = {
        "orgs": tr[0] or 0,
        "dirigentes": tr[1] or 0,
        "posts": tr[2] or 0,
        "planes": tr[3] or 0,
        "tareas": tr[4] or 0,
    }

    return AdminOverview(
        flota=flota,
        pipeline_nlp=pipeline,
        cola_semanal=cola,
        health=health,
        divergencia_alerts=0,
        totales=totales,
    )
