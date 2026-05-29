"""Endpoint de generación de guiones para reels (D-REELS-GROQ-1, 2026-05-15).

POST /api/v1/reels/generate-script — genera 1 guión vía Groq, persiste en
contenido_piezas, retorna el guión + metadata.

GET /api/v1/reels/recent?dirigente_id=N&limit=10 — historial reciente.

Scope multi-tenant: usa assert_dirigente_access del core.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID, uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.scope import assert_dirigente_access
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.reels import (
    GenerateReelScriptRequest,
    GenerateReelScriptResponse,
    ReelScript,
    ReelScriptListItem,
    ReelScriptMetadata,
)
from app.services.dirigente_context_builder import (
    build_context as build_dirigente_context,
    format_context_for_prompt as format_dirigente_context_for_prompt,
)
from app.services.reels_generator import generate_reel_script

router = APIRouter()
logger = logging.getLogger(__name__)


async def _fetch_dirigente_meta(
    db: AsyncSession, dirigente_id: int
) -> tuple[str, str | None]:
    row = (
        await db.execute(
            text("SELECT full_name, cargo FROM dirigentes WHERE id = :id"),
            {"id": dirigente_id},
        )
    ).first()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dirigente no existe")
    return row[0], row[1]


@router.post("/generate-script", response_model=GenerateReelScriptResponse)
async def generate_script(
    payload: GenerateReelScriptRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> GenerateReelScriptResponse:
    """Genera UN guión para reel vía Groq Llama 3.3 70B (tier gratuito).

    Latencia esperada: 1-2 segundos. Persiste en `contenido_piezas` con
    `variantes` JSON conteniendo {duracion_segundos, incluir_cta, script, metadata}.
    """
    # Scope multi-tenant
    org_id = await assert_dirigente_access(db, current_user, payload.dirigente_id)
    dirigente_nombre, dirigente_cargo = await _fetch_dirigente_meta(
        db, payload.dirigente_id
    )

    # Feature 2 (2026-05-17): enriquecer prompt con contexto BD del dirigente
    # (tono dominante, target predominante, posts recientes, promesas, efemérides).
    # Determinista, sin LLM, ~50ms.
    try:
        ctx_dict = await build_dirigente_context(db, payload.dirigente_id)
        contexto_dirigente_str = format_dirigente_context_for_prompt(ctx_dict) or None
    except Exception as e:
        # Si el builder falla, NO bloqueamos generación — caemos a modo genérico.
        logger.warning(
            f"reels.generate_script context_builder fallback (genérico) · {e}"
        )
        contexto_dirigente_str = None

    # Llamada a Groq
    try:
        result = await generate_reel_script(
            dirigente_nombre=dirigente_nombre,
            dirigente_cargo=dirigente_cargo,
            tema=payload.tema,
            duracion_segundos=payload.duracion_segundos,
            tono=payload.tono,
            incluir_cta=payload.incluir_cta,
            contexto_adicional=payload.contexto_adicional,
            contexto_dirigente=contexto_dirigente_str,
        )
    except RuntimeError as e:
        # GROQ_API_KEY no configurada
        logger.error(f"reels.generate_script config error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "groq_not_configured",
                "message": str(e),
            },
        ) from e
    except httpx.HTTPStatusError as e:
        logger.exception(f"reels.generate_script Groq HTTP {e.response.status_code}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": "groq_upstream",
                "status_code": e.response.status_code,
                "message": e.response.text[:300],
            },
        ) from e
    except (ValueError, KeyError) as e:
        logger.exception(f"reels.generate_script parse error: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": "groq_response_invalid",
                "message": str(e),
            },
        ) from e

    script = result["script"]
    metadata = result["metadata"]
    prompt_usado = result["prompt_usado"]

    # Persistir en contenido_piezas (reusar tabla · anti-over-engineering)
    pieza_id = uuid4()
    variantes = {
        "duracion_segundos": payload.duracion_segundos,
        "incluir_cta": payload.incluir_cta,
        "script": script,
        "metadata": metadata,
    }
    await db.execute(
        text(
            """
            INSERT INTO contenido_piezas
                (id, org_id, dirigente_id, tema, contexto, tono, variantes,
                 modelo_ia, prompt_usado, tokens_usados, estado, created_at)
            VALUES
                (:id, :org_id, :did, :tema, :contexto, :tono, CAST(:variantes AS JSONB),
                 :modelo, :prompt, :tokens, 'generado', NOW())
            """
        ),
        {
            "id": str(pieza_id),
            "org_id": org_id,
            "did": payload.dirigente_id,
            "tema": payload.tema or "(sin tema · libre)",
            "contexto": payload.contexto_adicional,
            "tono": payload.tono,
            "variantes": json.dumps(variantes),
            "modelo": metadata["model"],
            "prompt": prompt_usado,
            "tokens": metadata.get("completion_tokens") or 0,
        },
    )
    await db.commit()

    return GenerateReelScriptResponse(
        id=pieza_id,
        dirigente_id=payload.dirigente_id,
        dirigente_nombre=dirigente_nombre,
        tema=payload.tema,
        duracion_segundos=payload.duracion_segundos,
        tono=payload.tono,
        incluir_cta=payload.incluir_cta,
        script=ReelScript(**script),
        metadata=ReelScriptMetadata(**metadata),
        created_at=datetime.now(UTC),
    )


@router.get("/recent", response_model=list[ReelScriptListItem])
async def list_recent_scripts(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    dirigente_id: int = Query(..., gt=0),
    limit: int = Query(10, ge=1, le=50),
) -> list[ReelScriptListItem]:
    """Lista los N guiones más recientes de un dirigente (solo los generados
    via /reels/generate-script · filtra por modelo_ia LIKE 'groq/%')."""
    await assert_dirigente_access(db, current_user, dirigente_id)

    rows = (
        await db.execute(
            text(
                """
                SELECT id, tema, tono, variantes, modelo_ia, created_at
                FROM contenido_piezas
                WHERE dirigente_id = :did
                  AND modelo_ia LIKE 'groq/%'
                ORDER BY created_at DESC
                LIMIT :lim
                """
            ),
            {"did": dirigente_id, "lim": limit},
        )
    ).mappings().all()

    out: list[ReelScriptListItem] = []
    for r in rows:
        v: dict[str, Any] = r["variantes"] or {}
        script = v.get("script") or {}
        out.append(
            ReelScriptListItem(
                id=UUID(str(r["id"])),
                tema=r["tema"] if r["tema"] != "(sin tema · libre)" else None,
                duracion_segundos=int(v.get("duracion_segundos") or 30),
                tono=r["tono"],
                script=ReelScript(
                    hook=script.get("hook", ""),
                    desarrollo=script.get("desarrollo", ""),
                    cta=script.get("cta", ""),
                ),
                modelo_ia=r["modelo_ia"],
                created_at=r["created_at"],
            )
        )
    return out
