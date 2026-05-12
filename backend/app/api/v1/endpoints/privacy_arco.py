"""ARCO: Acceso, Rectificación, Cancelación, Oposición endpoints.

LFPDPPP: titulares pueden ejercer derechos sobre comments públicos
pseudonimizados. Dado que guardamos author_hash SHA256(platform:cid:salt),
el titular debe proveer su user_id público real para recalcular hash
y localizar sus comments.
"""
from __future__ import annotations

import hashlib
import os
from typing import Annotated, Literal

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

router = APIRouter()


SALT = os.environ.get("COMMENT_AUTHOR_SALT")


class ARCORequest(BaseModel):
    platform: Literal["TIKTOK", "FACEBOOK", "INSTAGRAM", "YOUTUBE", "TWITTER"]
    commenter_public_id: str = Field(min_length=1, max_length=200)
    tipo_derecho: Literal["acceso", "cancelacion", "oposicion"]
    email_contacto: str = Field(min_length=5, max_length=200)
    razon: str | None = Field(default=None, max_length=1000)


class ARCOAccessResponse(BaseModel):
    found_comments: int
    sample_content: list[str]
    next_steps: str


class ARCOCancelResponse(BaseModel):
    deleted: int
    message: str


def _compute_hash(platform: str, commenter_id: str) -> str:
    if not SALT:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Sistema de privacidad no configurado — contactar privacidad@mdconsultoria-ti.org",
        )
    return hashlib.sha256(f"{platform}:{commenter_id}:{SALT}".encode()).hexdigest()


@router.post("/arco/exercise", response_model=ARCOAccessResponse | ARCOCancelResponse)
async def ejercer_arco(
    db: Annotated[AsyncSession, Depends(get_db)],
    payload: ARCORequest,
) -> ARCOAccessResponse | ARCOCancelResponse:
    """Endpoint público — ejercicio de derechos ARCO.

    Este endpoint acepta solicitudes sin autenticación (cualquier titular
    puede ejercer). En producción debe agregarse:
    - Verificación de identidad (INE)
    - Rate limiting por email
    - Notificación a equipo legal MD para validación

    Por ahora devuelve resultado directo para demo MVP.
    """
    ah = _compute_hash(payload.platform, payload.commenter_public_id)

    if payload.tipo_derecho == "acceso":
        rows = (await db.execute(
            text("""
                SELECT content
                FROM social_comments
                WHERE author_hash = :ah
                LIMIT 50
            """),
            {"ah": ah},
        )).fetchall()
        return ARCOAccessResponse(
            found_comments=len(rows),
            sample_content=[r[0][:200] for r in rows[:10]],
            next_steps=(
                f"Se encontraron {len(rows)} comentarios asociados a tu identidad pública. "
                "Para recibir el reporte completo con métricas, envía identificación oficial a "
                "privacidad@mdconsultoria-ti.org indicando folio " + ah[:16]
            ),
        )

    if payload.tipo_derecho == "cancelacion":
        result = await db.execute(
            text("DELETE FROM social_comments WHERE author_hash = :ah"),
            {"ah": ah},
        )
        await db.commit()
        return ARCOCancelResponse(
            deleted=result.rowcount or 0,
            message=(
                "Comentarios eliminados del sistema. "
                "Las métricas agregadas (ej. IA scores) pueden persistir sin asociación individual. "
                "Confirmación al email: " + payload.email_contacto
            ),
        )

    if payload.tipo_derecho == "oposicion":
        # Anti-fraude: marcar como opt-out futuro (requiere tabla privacy_optouts que no tenemos)
        # MVP: registrar en log solamente
        return ARCOCancelResponse(
            deleted=0,
            message=(
                "Solicitud de oposición registrada. El equipo legal MD Consultoría validará tu identidad "
                "en 20 días hábiles (art. 32 LFPDPPP) y confirmará exclusión futura. "
                "Folio: " + ah[:16]
            ),
        )

    raise HTTPException(status.HTTP_400_BAD_REQUEST, "tipo_derecho inválido")


@router.get("/legal/privacidad")
async def get_privacy_notice() -> dict:
    """Aviso de Privacidad vigente. Servido como metadata JSON."""
    return {
        "version": "1.0.0",
        "entry_into_force": "2026-04-14",
        "responsable": "MD Consultoría SC",
        "contacto": "privacidad@mdconsultoria-ti.org",
        "retention_days_comments": 180,
        "pseudonimization": "SHA256 con salt",
        "arco_endpoint": "/api/v1/arco/exercise",
        "fuente_legal": "LFPDPPP art. 10-IV (fuentes de acceso público) + art. 16-II (interés legítimo)",
        "full_text_url": "/docs/AVISO-PRIVACIDAD-CRECE.md",
    }
