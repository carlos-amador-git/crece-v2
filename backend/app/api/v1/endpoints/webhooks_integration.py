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
    x_chatwoot_signature: Annotated[str | None, Header(alias="X-Chatwoot-Signature")] = None,
) -> dict:
    """Receive events from Chatwoot (directly or via n8n).

    Accepts signatures from both X-N8N-Signature and X-Chatwoot-Signature headers.
    Dispatches by event type — supports both n8n-preprocessed and raw Chatwoot payloads.
    """
    payload_bytes = await request.body()

    # Accept signature from either header
    signature = x_n8n_signature or x_chatwoot_signature
    if not _verify_signature(payload_bytes, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing webhook signature",
        )

    import json

    try:
        raw = json.loads(payload_bytes)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        ) from None

    # Handle raw Chatwoot payload (has "event" key) vs n8n-preprocessed (has "tipo" key)
    if "event" in raw and "tipo" not in raw:
        return await _handle_chatwoot_direct(db, raw)

    payload = ChatwootWebhookPayload(**raw)

    if payload.tipo == "message_reply":
        return await _handle_message_reply(db, payload.data)
    elif payload.tipo == "contact_created":
        return await _handle_contact_created(db, payload.data)
    elif payload.tipo == "propuesta":
        return await _handle_propuesta(db, payload.data)
    else:
        logger.warning("Unknown webhook event type: %s", payload.tipo)
        return {"status": "ignored", "tipo": payload.tipo}


async def _handle_chatwoot_direct(db: AsyncSession, raw: dict) -> dict:
    """Handle raw Chatwoot webhook payloads (not preprocessed by n8n)."""
    event = raw.get("event", "")
    logger.info("Chatwoot direct event: %s", event)

    if event == "contact_created":
        contact = raw.get("contact", {}) or raw.get("data", {})
        data = {
            "nombre": contact.get("name", "Contacto"),
            "telefono": contact.get("phone_number"),
        }
        if data["telefono"]:
            return await _handle_contact_created(db, data)
        return {"status": "skipped", "reason": "no phone_number"}

    elif event == "message_created":
        message = raw.get("message", {}) or raw.get("data", {})
        conversation = raw.get("conversation", {})
        return {
            "status": "received",
            "event": event,
            "conversation_id": conversation.get("id"),
            "message_type": message.get("message_type"),
        }

    elif event in ("conversation_created", "message_updated"):
        return {"status": "received", "event": event}

    else:
        logger.info("Unhandled Chatwoot event: %s", event)
        return {"status": "ignored", "event": event}


async def _handle_message_reply(db: AsyncSession, data: dict) -> dict:
    """Update CRM interaction when a citizen replies via Chatwoot."""
    ciudadano_id = data.get("ciudadano_id")
    mensaje = data.get("mensaje", "")
    canal = data.get("canal", "chatwoot")

    if not ciudadano_id:
        return {"status": "skipped", "reason": "no ciudadano_id in payload"}

    # D.2b — Opt-out handler (LFPDPPP / WABA compliance)
    if mensaje and mensaje.strip().upper() in ("STOP", "BAJA", "CANCELAR", "NO MAS"):
        from app.models.ciudadano import Ciudadano

        result = await db.execute(select(Ciudadano).where(Ciudadano.id == ciudadano_id))
        ciudadano = result.scalar_one_or_none()
        if ciudadano:
            ciudadano.no_contactar = True
            await db.flush()
            logger.info("Opt-out: ciudadano %d marked no_contactar=True", ciudadano_id)
            return {"status": "opt_out", "ciudadano_id": ciudadano_id}

    # D.2 fix: resolve org_id from the ciudadano record
    org_id = data.get("org_id")
    if not org_id:
        from app.models.ciudadano import Ciudadano

        c_result = await db.execute(select(Ciudadano.org_id).where(Ciudadano.id == ciudadano_id))
        org_id = c_result.scalar_one_or_none() or 3  # fallback MC CDMX

    try:
        from app.models.crm_interaccion import CrmInteraccion

        interaccion = CrmInteraccion(
            ciudadano_id=ciudadano_id,
            org_id=org_id,
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
    result = await db.execute(select(Ciudadano).where(Ciudadano.telefono == telefono).limit(1))
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
        org_id=data.get("org_id") or 3,  # D.2 fix: default MC CDMX org
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
        # D.2 fix: resolve org_id from ciudadano
        from app.models.ciudadano import Ciudadano
        from app.models.crm_interaccion import CrmInteraccion

        c_result = await db.execute(select(Ciudadano.org_id).where(Ciudadano.id == ciudadano_id))
        prop_org_id = c_result.scalar_one_or_none() or 3

        interaccion = CrmInteraccion(
            ciudadano_id=ciudadano_id,
            org_id=prop_org_id,
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
