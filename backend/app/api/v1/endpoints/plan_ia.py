"""Plan IA · endpoints de generación (T4 Sprint S4 D-17).

POST /api/v1/plan-ia/generate/{dirigente_id}
    Arranca el pipeline LLM Gemma 3:12b y persiste recomendaciones aprobadas.

Auth:
    - JWT obligatoria.
    - Role ADMIN puede generar para cualquier dirigente de cualquier org.
    - Role no-ADMIN solo puede generar para dirigentes de su propia org.

Rate limit:
    - 1 generación por dirigente cada 24h (evita spam y costos NLP).
    - Bypass: ?force=true disponible solo para role=ADMIN.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.dirigente import Dirigente
from app.models.recomendacion_plan_ia import RecomendacionPlanIA
from app.models.user import User
from app.services.plan_ia.llm_pipeline import generate_for_dirigente

router = APIRouter()


def _resolve_org_id(current_user: User, request: Request) -> int | None:
    org_id = getattr(current_user, "org_id", None)
    if current_user.role == "admin":
        override = request.headers.get("x-org-id")
        if override and override.isdigit():
            return int(override)
    return org_id


@router.post("/generate/{dirigente_id}")
async def generate_plan_ia(
    dirigente_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    force: bool = Query(
        False,
        description="Admin-only bypass del rate limit 24h. Ignorado si no es admin.",
    ),
) -> dict[str, Any]:
    """Ejecuta pipeline Plan IA para un dirigente.

    Flujo:
    1. Valida dirigente existe y el caller tiene acceso (scope org).
    2. Rate limit: 1 generación / dirigente / 24h (bypass admin con force=true).
    3. Llama `PlanIAPipeline.generate(...)` que carga diagnóstico 18 bloques,
       arma prompt, llama Gemma 3:12b, valida anti-vanidad, persiste.
    4. Retorna lista de recomendaciones creadas + métricas del pipeline.
    """
    org_id = _resolve_org_id(current_user, request)
    if org_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="org_id no resoluble del usuario; admin puede enviar header X-Org-Id",
        )

    dirigente = await db.get(Dirigente, dirigente_id)
    if dirigente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dirigente {dirigente_id} no existe",
        )

    # Scope: no-admin solo accede a dirigentes de su org
    if current_user.role != "admin":
        if dirigente.org_id is None or dirigente.org_id != org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Dirigente fuera del scope de tu organización",
            )

    # Rate limit 24h (salvo admin + force=true)
    if not (current_user.role == "admin" and force):
        threshold = datetime.now(UTC) - timedelta(hours=24)
        recent = await db.scalar(
            select(func.count(RecomendacionPlanIA.id)).where(
                RecomendacionPlanIA.dirigente_id == dirigente_id,
                RecomendacionPlanIA.created_at >= threshold,
            )
        )
        if recent and recent > 0:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Ya se generaron recomendaciones para dirigente_id={dirigente_id} "
                    f"en las últimas 24h ({recent} registros). Admin puede forzar con "
                    "?force=true."
                ),
            )

    # Pipeline — persiste internamente
    effective_org = dirigente.org_id or org_id
    result = await generate_for_dirigente(db, dirigente_id, effective_org)

    return {
        "dirigente_id": dirigente_id,
        "org_id": effective_org,
        "generated_by_user": current_user.id,
        **result,
    }
