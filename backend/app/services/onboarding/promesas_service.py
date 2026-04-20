"""Sección 8 · Seed promesas (D-17).

Bulk insert de promesas declaradas por el cliente en el wizard.
La tabla ``promesas_dirigente`` ya existe desde Sprint S3 (B16).

Libera bloque B16 Rastreador Promesas de Campaña en el dashboard.
"""
from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dirigente import Dirigente
from app.models.promesa_dirigente import PromesaDirigente, PromesaEstado


async def bulk_seed_promesas(
    db: AsyncSession,
    *,
    dirigente_id: int,
    promesas: list[dict[str, Any]],
) -> dict[str, Any]:
    """Inserta N promesas del onboarding wizard.

    promesas: [{texto_promesa, fecha_compromiso?, evidencia_url?}]

    Retorna:
        {dirigente_id, inserted_ids, total}
    """
    dirigente = await db.get(Dirigente, dirigente_id)
    if dirigente is None:
        raise LookupError(f"Dirigente {dirigente_id} no existe")

    if not promesas:
        raise ValueError(
            "Se requiere al menos 1 promesa declarada (D-17 bloque B16)"
        )

    inserted_ids: list[int] = []
    now = datetime.now(UTC)

    for item in promesas:
        texto = (item.get("texto_promesa") or "").strip()
        if len(texto) < 10:
            continue
        fecha = item.get("fecha_compromiso")
        if isinstance(fecha, str):
            try:
                fecha = date.fromisoformat(fecha)
            except ValueError:
                fecha = None

        promesa = PromesaDirigente(
            dirigente_id=dirigente_id,
            texto_promesa=texto,
            fecha_compromiso=fecha,
            estado=PromesaEstado.PENDIENTE,
            evidencia_url=item.get("evidencia_url"),
            created_at=now,
            updated_at=now,
        )
        db.add(promesa)
        await db.flush()
        inserted_ids.append(promesa.id)

    await db.commit()
    return {
        "dirigente_id": dirigente_id,
        "inserted_ids": inserted_ids,
        "total": len(inserted_ids),
    }
