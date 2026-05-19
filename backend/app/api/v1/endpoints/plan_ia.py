"""Plan IA · endpoints de generación (T4 Sprint S4 D-17 → S5 T0 Celery migration).

POST /api/v1/plan-ia/generate/{dirigente_id}
    Arranca el pipeline LLM Gemma 3:12b **vía Celery worker** (cola ``ai``)
    y persiste recomendaciones aprobadas. Bloquea hasta 180s esperando el
    resultado. Si timeout, retorna HTTP 504 con task_id para polling.

GET /api/v1/plan-ia/generate/status/{task_id}
    Polling de estado (pending | running | success | failure) para un task
    que excedió el timeout síncrono.

Motivación S5 T0 (DIFERIDO-06):
    FastAPI + httpx.AsyncClient + host.docker.internal/Coolify-VPS se cuelga
    silenciosamente en payloads Ollama grandes (>60s). Al mover el HTTP call
    al worker Celery (event loop independiente + anyio.to_thread) el endpoint
    responde sin bloquear uvicorn. Gold: 144s warm con gemma3:12b (S4 Agent A).

Auth:
    - JWT obligatoria.
    - Role ADMIN puede generar para cualquier dirigente de cualquier org.
    - Role no-ADMIN solo puede generar para dirigentes de su propia org.

Rate limit:
    - 1 generación por dirigente cada 24h (evita spam y costos NLP).
    - Bypass: ?force=true disponible solo para role=ADMIN.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from celery.exceptions import TimeoutError as CeleryTimeoutError
from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.dirigente import Dirigente
from app.models.recomendacion_plan_ia import RecomendacionPlanIA
from app.models.user import User
from app.workers.celery_app import celery_app
from app.workers.tasks import plan_ia_generate_async

logger = logging.getLogger(__name__)

router = APIRouter()

# Timeout sincrónico antes de devolver 504 + task_id.
# Empírico (S5 T0 2026-04-20): pipeline warm gemma3:12b Mac M4 GPU
# ≈208s con prompt_chars=15525 + num_predict=900 + 4 recs válidas.
# 240s da headroom sobre la media observada. Si excede → 504 con
# task_id para polling vía GET /generate/status/{task_id}.
_SYNC_TIMEOUT_S = 300.0
_SYNC_POLL_INTERVAL_S = 2.0


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
    """⚠️ FEATURE PAUSADA 2026-05-15 ⚠️

    El pipeline actual llama a Ollama remoto (VPS Coolify) declarado OFF por
    CEO 2026-05-15. La decisión arquitectural es migrar a subprocess Claude
    Code CLI + Gemini CLI (zero API). Mientras se completa el refactor, el
    endpoint retorna HTTP 503.

    Para reactivar: completar refactor en `app/services/plan_ia/llm_pipeline.py`
    reemplazando `_call_ollama` por subprocess CC + Gemini CLI según patrón
    documentado en DECISIONS.md D-PLAN-IA-CC-GEMINI-CLI-1.

    Reels (feature nueva paralela): ver `/api/v1/reels/*` para generación de
    guiones con Groq Llama 3.3 70B (tier gratuito).
    """
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={
            "error": "feature_paused",
            "message": (
                "Generador de plan IA pausado por refactor a subprocess CC + Gemini CLI. "
                "Ver DECISIONS.md D-PLAN-IA-CC-GEMINI-CLI-1. Para generación de "
                "contenido reciente, usar /reels/generate-script."
            ),
            "since": "2026-05-15",
            "alternative": "/api/v1/reels/generate-script",
        },
    )

    # ⬇ Código debajo es el flujo ORIGINAL · preservado para refactor futuro ⬇
    """Encola pipeline Plan IA en Celery worker y espera hasta 180s.

    Flujo:
    1. Valida dirigente existe y el caller tiene acceso (scope org).
    2. Rate limit: 1 generación / dirigente / 24h (bypass admin con force=true).
    3. Encola `plan_ia_generate_async` en la cola ``ai`` (gemma3:12b).
    4. Poll `task.get(timeout=180, interval=2)` — si completa antes, HTTP 200.
       Si timeout, HTTP 504 con task_id (cliente puede poll'ear status).
    5. Si task falla, HTTP 500 con error string.

    Returns (HTTP 200):
        {
          "dirigente_id", "org_id", "generated_by_user",
          "task_id", "elapsed_s",
          "pipeline": {...}, "recomendaciones_creadas": [...],
          "rechazadas": [...]
        }
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

    effective_org = dirigente.org_id or org_id

    # Encolar en Celery (cola "ai")
    queued_at = datetime.now(UTC)
    async_result: AsyncResult = plan_ia_generate_async.apply_async(
        args=(dirigente_id, effective_org, bool(force)),
        queue="ai",
    )
    task_id = async_result.id
    logger.info(
        "plan_ia.generate queued task_id=%s dirigente_id=%d org_id=%d force=%s user=%d",
        task_id,
        dirigente_id,
        effective_org,
        force,
        current_user.id,
    )

    # Wait bloqueante pero FUERA del httpx event loop. Celery pool de
    # threads + Redis polling — el worker corre Ollama en su propio loop.
    try:
        result = async_result.get(
            timeout=_SYNC_TIMEOUT_S,
            interval=_SYNC_POLL_INTERVAL_S,
            propagate=False,  # no raise si la task lanzó — la manejamos abajo
        )
    except CeleryTimeoutError:
        logger.warning(
            "plan_ia.generate timeout (>%.0fs) task_id=%s dirigente_id=%d — cliente debe poll /generate/status/%s",
            _SYNC_TIMEOUT_S,
            task_id,
            dirigente_id,
            task_id,
        )
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={
                "task_id": task_id,
                "status": "pending",
                "message": (
                    f"LLM sigue procesando (>{int(_SYNC_TIMEOUT_S)}s). "
                    f"Use GET /api/v1/plan-ia/generate/status/{task_id} para polling."
                ),
                "dirigente_id": dirigente_id,
                "org_id": effective_org,
            },
        ) from None

    completed_at = datetime.now(UTC)
    elapsed_s = (completed_at - queued_at).total_seconds()

    # Task completó — puede ser ok o error lógico (sin excepción pero status=error)
    if not isinstance(result, dict):
        logger.error(
            "plan_ia.generate bad_result task_id=%s type=%s",
            task_id,
            type(result).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "task_id": task_id,
                "error": f"Worker devolvió resultado inesperado ({type(result).__name__})",
            },
        )

    if result.get("status") == "error":
        logger.error(
            "plan_ia.generate worker_error task_id=%s err=%s",
            task_id,
            result.get("error"),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "task_id": task_id,
                "error": result.get("error"),
                "elapsed_s": result.get("elapsed_s", elapsed_s),
            },
        )

    logger.info(
        "plan_ia.generate success task_id=%s dirigente_id=%d n_recs=%d elapsed=%.2fs",
        task_id,
        dirigente_id,
        len(result.get("recomendaciones_ids") or []),
        elapsed_s,
    )

    return {
        "dirigente_id": dirigente_id,
        "org_id": effective_org,
        "generated_by_user": current_user.id,
        "task_id": task_id,
        "queued_at": queued_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "elapsed_s": round(elapsed_s, 2),
        "recomendaciones_ids": result.get("recomendaciones_ids") or [],
        "recomendaciones_creadas": result.get("recomendaciones_creadas") or [],
        "rechazadas": result.get("rechazadas") or [],
        "pipeline": result.get("pipeline") or {},
    }


@router.get("/recomendaciones")
async def list_recomendaciones(
    current_user: Annotated[User, Depends(get_current_user)],
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    estado: list[str] | None = Query(
        None,
        description="propuesta|aprobada|rechazada|modificada|ejecutada|completada|fallida · acepta múltiples ?estado=a&estado=b",
    ),
    dirigente_id: int | None = Query(None),
    tipo: str | None = Query(None, description="start|stop|continue"),
    limit: int = Query(50, ge=1, le=200),
) -> list[dict[str, Any]]:
    """Lista recomendaciones con filtros opcionales.

    - Admin: ve todas (con override X-Org-Id) o con filtro dirigente_id.
    - Viewer: solo ve las de su propia org + solo estados visibles al cliente
      (aprobada/modificada/ejecutada/completada).
    """
    org_id = _resolve_org_id(current_user, request)
    stmt = select(RecomendacionPlanIA)

    estados_filter = [e for e in (estado or []) if e]

    # Org scoping · viewer solo ve su org
    if current_user.role != "admin":
        if org_id is None:
            return []
        stmt = stmt.where(RecomendacionPlanIA.org_id == org_id)
        # Viewer NO ve estado=propuesta ni rechazada (solo pass MD review)
        visible_estados = {"aprobada", "modificada", "ejecutada", "completada"}
        if not estados_filter:
            stmt = stmt.where(RecomendacionPlanIA.estado.in_(visible_estados))
        else:
            allowed = [e for e in estados_filter if e in visible_estados]
            if not allowed:
                return []
            estados_filter = allowed
    else:
        if org_id is not None:
            stmt = stmt.where(RecomendacionPlanIA.org_id == org_id)

    if dirigente_id is not None:
        stmt = stmt.where(RecomendacionPlanIA.dirigente_id == dirigente_id)
    if estados_filter:
        stmt = stmt.where(RecomendacionPlanIA.estado.in_(estados_filter))
    if tipo:
        stmt = stmt.where(RecomendacionPlanIA.tipo == tipo)

    stmt = stmt.order_by(RecomendacionPlanIA.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    rows = result.scalars().all()

    return [
        {
            "id": r.id,
            "plan_ia_id": r.plan_ia_id,
            "dirigente_id": r.dirigente_id,
            "org_id": r.org_id,
            "tipo": r.tipo,
            "accion_texto": r.accion_texto,
            "ventana_inicio": r.ventana_inicio.isoformat() if r.ventana_inicio else None,
            "ventana_fin": r.ventana_fin.isoformat() if r.ventana_fin else None,
            "ventana_duracion_dias": r.ventana_duracion_dias,
            "criterio_exito": r.criterio_exito,
            "principio_conductual": r.principio_conductual,
            "evidencia_respaldo": r.evidencia_respaldo,
            "plataformas_destino": r.plataformas_destino,
            "estado": r.estado,
            "post_ejecutor_id": r.post_ejecutor_id,
            "metricas_predichas": r.metricas_predichas,
            "metricas_observadas": r.metricas_observadas,
            "veredicto": r.veredicto,
            "veredicto_editado_por_cliente": r.veredicto_editado_por_cliente,
            "veredicto_original": r.veredicto_original,
            "notas_cliente": r.notas_cliente,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in rows
    ]


_ALLOWED_TRANSITIONS = {
    "propuesta": {"aprobada", "rechazada", "modificada"},
    "aprobada": {"ejecutada", "rechazada", "modificada"},
    "modificada": {"aprobada", "ejecutada", "rechazada"},
    "ejecutada": {"completada", "fallida"},
    # rechazada · completada · fallida son terminales
}


@router.put("/{recomendacion_id}/estado")
async def transicionar_estado(
    recomendacion_id: int,
    payload: dict[str, Any],
    current_user: Annotated[User, Depends(get_current_user)],
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """Transición de estado · payload {estado, motivo?, notas?, accion_texto?, ...}.

    Admin: puede transicionar propuesta→aprobada/rechazada/modificada (MD review).
    Viewer: puede transicionar aprobada→ejecutada (aceptar y publicar) o rechazada.
    """
    nuevo_estado = payload.get("estado")
    if not nuevo_estado:
        raise HTTPException(status_code=422, detail="campo 'estado' requerido")

    r = await db.get(RecomendacionPlanIA, recomendacion_id)
    if not r:
        raise HTTPException(status_code=404, detail=f"recomendacion {recomendacion_id} no existe")

    # Org scoping
    if current_user.role != "admin":
        user_org = getattr(current_user, "org_id", None)
        if user_org is None or r.org_id != user_org:
            raise HTTPException(status_code=403, detail="fuera de tu organización")

    estado_actual = r.estado
    permitidas = _ALLOWED_TRANSITIONS.get(estado_actual, set())
    if nuevo_estado not in permitidas:
        raise HTTPException(
            status_code=409,
            detail=f"transición {estado_actual} → {nuevo_estado} no permitida. Válidas: {sorted(permitidas)}",
        )

    # Role-based restrictions
    if current_user.role != "admin":
        # Viewer solo puede aceptar (aprobada→ejecutada) o rechazar recs aprobadas
        if estado_actual != "aprobada":
            raise HTTPException(status_code=403, detail="viewer solo puede transicionar desde estado=aprobada")
        if nuevo_estado not in {"ejecutada", "rechazada"}:
            raise HTTPException(status_code=403, detail="viewer no puede aprobar/modificar")

    # Aplicar cambios
    r.estado = nuevo_estado
    if payload.get("accion_texto"):
        r.accion_texto = payload["accion_texto"]
    if payload.get("criterio_exito"):
        r.criterio_exito = payload["criterio_exito"]
    if "ventana_duracion_dias" in payload:
        r.ventana_duracion_dias = int(payload["ventana_duracion_dias"])
    if "notas_cliente" in payload:
        r.notas_cliente = str(payload["notas_cliente"])[:1000]
    r.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(r)

    return {"id": r.id, "estado": r.estado, "updated_at": r.updated_at.isoformat()}


@router.put("/{recomendacion_id}/post-ejecutor")
async def vincular_post_ejecutor(
    recomendacion_id: int,
    payload: dict[str, Any],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """Cliente vincula post publicado tras aceptar recomendación (T7 S4).

    payload: {post_id: int}
    Transición automática: estado → 'ejecutada' + ventana_inicio=NOW +
    ventana_fin=NOW+ventana_duracion_dias.
    """
    post_id = payload.get("post_id")
    if not post_id:
        raise HTTPException(status_code=422, detail="campo 'post_id' requerido")

    r = await db.get(RecomendacionPlanIA, recomendacion_id)
    if not r:
        raise HTTPException(status_code=404, detail=f"recomendacion {recomendacion_id} no existe")

    # Org scoping
    if current_user.role != "admin":
        user_org = getattr(current_user, "org_id", None)
        if user_org is None or r.org_id != user_org:
            raise HTTPException(status_code=403, detail="fuera de tu organización")

    if r.estado not in {"aprobada", "modificada"}:
        raise HTTPException(
            status_code=409,
            detail=f"vinculación solo desde estado aprobada/modificada (actual: {r.estado})",
        )

    now = datetime.now(UTC)
    r.post_ejecutor_id = int(post_id)
    r.ventana_inicio = now
    r.ventana_fin = now + timedelta(days=r.ventana_duracion_dias or 14)
    r.estado = "ejecutada"
    r.updated_at = now
    await db.commit()

    return {
        "id": r.id,
        "post_ejecutor_id": r.post_ejecutor_id,
        "estado": r.estado,
        "ventana_inicio": r.ventana_inicio.isoformat(),
        "ventana_fin": r.ventana_fin.isoformat(),
    }


@router.get("/generate/status/{task_id}")
async def generate_plan_ia_status(
    task_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    """Poll estado de un task encolado via POST /generate/{dirigente_id}.

    Estados Celery:
        - PENDING: aún no iniciado (o task_id desconocido)
        - STARTED: worker lo tomó (task_track_started=True en config)
        - SUCCESS: terminó ok — result contiene dict del pipeline
        - FAILURE: excepción no manejada en el worker
        - RETRY: reintentando

    Returns:
        {
          "task_id", "state", "ready": bool,
          "result"?: dict (solo si state=SUCCESS),
          "error"?: str  (solo si state=FAILURE)
        }
    """
    async_result = AsyncResult(task_id, app=celery_app)
    state = async_result.state
    ready = async_result.ready()

    response: dict[str, Any] = {
        "task_id": task_id,
        "state": state,
        "ready": ready,
    }

    if state == "SUCCESS":
        result = async_result.result
        if isinstance(result, dict):
            response["result"] = result
    elif state == "FAILURE":
        response["error"] = str(async_result.result) if async_result.result else "unknown"
    elif state in ("PENDING", "STARTED", "RETRY"):
        # nada extra; cliente sigue poll'eando
        pass

    return response
