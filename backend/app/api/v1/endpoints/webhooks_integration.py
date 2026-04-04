from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.schemas.integration import ChatwootWebhookPayload

logger = logging.getLogger(__name__)

router = APIRouter()

# The shared secret used by n8n to sign webhook payloads.
# Loaded from environment; falls back to JWT_SECRET for development simplicity.
_WEBHOOK_SECRET = getattr(settings, "N8N_WEBHOOK_SECRET", None) or settings.JWT_SECRET


def _verify_signature(payload_bytes: bytes, signature: str | None) -> bool:
    """Verify HMAC-SHA256 signature from n8n's X-N8N-Signature header."""
    if not signature:
        return False
    expected = hmac.new(
        _WEBHOOK_SECRET.encode(),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/chatwoot")
async def chatwoot_webhook(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    x_n8n_signature: Annotated[str | None, Header(alias="X-N8N-Signature")] = None,
) -> dict:
    """Receive events pre-processed by n8n from Chatwoot.

    Verifies HMAC-SHA256 signature, then dispatches by event type:
    - message_reply: update CRM interactions
    - contact_created: create ciudadano if not exists
    - propuesta: log proposal interaction
    """
    payload_bytes = await request.body()

    # Verify signature
    if not _verify_signature(payload_bytes, x_n8n_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing webhook signature",
        )

    # Parse payload
    import json

    try:
        raw = json.loads(payload_bytes)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )

    payload = ChatwootWebhookPayload(**raw)

    # Dispatch by event type
    if payload.tipo == "message_reply":
        return await _handle_message_reply(db, payload.data)
    elif payload.tipo == "contact_created":
        return await _handle_contact_created(db, payload.data)
    elif payload.tipo == "propuesta":
        return await _handle_propuesta(db, payload.data)
    else:
        logger.warning("Unknown webhook event type: %s", payload.tipo)
        return {"status": "ignored", "tipo": payload.tipo}


async def _handle_message_reply(db: AsyncSession, data: dict) -> dict:
    """Update CRM interaction when a citizen replies via Chatwoot."""
    ciudadano_id = data.get("ciudadano_id")
    mensaje = data.get("mensaje", "")
    canal = data.get("canal", "chatwoot")

    if not ciudadano_id:
        return {"status": "skipped", "reason": "no ciudadano_id in payload"}

    try:
        from app.models.crm_interaccion import CrmInteraccion

        interaccion = CrmInteraccion(
            ciudadano_id=ciudadano_id,
            tipo="respuesta_entrante",
            canal=canal,
            resultado="recibido",
            notas=mensaje[:2000] if mensaje else None,
            referencia_tipo="chatwoot",
            referencia_id=data.get("conversation_id"),
        )
        db.add(interaccion)
        await db.flush()
        return {"status": "ok", "interaction_id": interaccion.id}
    except ImportError:
        logger.warning("CrmInteraccion model not available")
        return {"status": "skipped", "reason": "model_not_available"}


async def _handle_contact_created(db: AsyncSession, data: dict) -> dict:
    """Create a ciudadano record if one doesn't already exist for this phone."""
    from app.models.ciudadano import Ciudadano

    telefono = data.get("telefono")
    if not telefono:
        return {"status": "skipped", "reason": "no telefono in payload"}

    # Check if already exists
    result = await db.execute(
        select(Ciudadano).where(Ciudadano.telefono == telefono).limit(1)
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        return {"status": "exists", "ciudadano_id": existing.id}

    # Minimal creation — field operator will enrich later
    ciudadano = Ciudadano(
        nombre=data.get("nombre", "Contacto"),
        apellido_paterno=data.get("apellido_paterno", "Chatwoot"),
        telefono=telefono,
        seccion_id=data.get("seccion_id", 1),  # Must be enriched later
        edad_rango=data.get("edad_rango", "26-35"),
        registrado_por_id=data.get("registrado_por_id", 1),
        org_id=data.get("org_id"),
    )
    db.add(ciudadano)
    await db.flush()
    await db.refresh(ciudadano)

    return {"status": "created", "ciudadano_id": ciudadano.id}


async def _handle_propuesta(db: AsyncSession, data: dict) -> dict:
    """Log a proposal/suggestion from a citizen as a CRM interaction."""
    ciudadano_id = data.get("ciudadano_id")
    propuesta = data.get("propuesta", "")

    if not ciudadano_id:
        return {"status": "skipped", "reason": "no ciudadano_id in payload"}

    try:
        from app.models.crm_interaccion import CrmInteraccion

        interaccion = CrmInteraccion(
            ciudadano_id=ciudadano_id,
            tipo="propuesta",
            canal=data.get("canal", "chatwoot"),
            resultado="registrada",
            notas=propuesta[:2000] if propuesta else None,
            referencia_tipo="chatwoot",
            referencia_id=data.get("conversation_id"),
        )
        db.add(interaccion)
        await db.flush()
        return {"status": "ok", "interaction_id": interaccion.id}
    except ImportError:
        logger.warning("CrmInteraccion model not available")
        return {"status": "skipped", "reason": "model_not_available"}
