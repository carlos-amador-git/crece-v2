"""Sección 7 · Seed competidores (D-22).

El cliente declara 3-5 competidores directos en el wizard. Se usan para:
- Bloque #04 benchmark vs competidores
- Cálculo de quintiles comparativos
- Seguimiento de share of voice

Arquitectura final (2026-05-14, post war-room-personal · D-MODEL-WAR-ROOM-1):
    `competidores` legacy fue deprecada. Se usa `competitor_profiles` con
    `dirigente_objetivo_id` apuntando al cliente. Esta tabla soporta el
    pipeline light (sin NLP) y conecta directamente con la UI war-room.

    `dirigentes.competidor_directo_ids` queda como referencia agregada
    (array de competitor_profiles.id) para queries rápidas del benchmark service.
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.competitor_profile import CompetitorProfile
from app.models.dirigente import Dirigente


def _slugify_external_id(nombre: str) -> str:
    """Genera un profile_external_id placeholder cuando el wizard no provee handle real.

    Format: `wizard:<slug>` para distinguir de external_ids reales scrapeados.
    """
    slug = "".join(c if c.isalnum() else "_" for c in nombre.lower())[:80]
    return f"wizard:{slug}"


async def seed_competidores(
    db: AsyncSession,
    *,
    dirigente_id: int,
    competidores: list[dict[str, str | bool | None]],
) -> dict[str, Any]:
    """Inserta/reutiliza competidores y asocia al dirigente.

    competidores: [{full_name, cargo, partido?, url_ref?, es_piloto?}]

    Retorna:
        {
            dirigente_id,
            competidor_ids: [int],
            created: [{id, nombre, cargo}],
            reused: [{id, nombre}]
        }
    """
    dirigente = await db.get(Dirigente, dirigente_id)
    if dirigente is None:
        raise LookupError(f"Dirigente {dirigente_id} no existe")

    if not competidores:
        raise ValueError("Se requiere al menos 1 competidor declarado (D-22)")

    competidor_ids: list[int] = []
    created: list[dict[str, Any]] = []
    reused: list[dict[str, Any]] = []

    for item in competidores:
        nombre = (item.get("full_name") or "").strip()
        cargo = (item.get("cargo") or "").strip()
        partido = (item.get("partido") or "OTRO").strip().upper() or "OTRO"

        if not nombre or not cargo:
            continue

        external_id = _slugify_external_id(nombre)

        # Dedupe por (org_id, platform=FACEBOOK default, profile_external_id)
        # vía unique constraint `uq_competitor_org_platform_external`.
        q = await db.execute(
            select(CompetitorProfile).where(
                CompetitorProfile.org_id == dirigente.org_id,
                CompetitorProfile.profile_external_id == external_id,
            )
        )
        existing = q.scalar_one_or_none()
        if existing is not None:
            competidor_ids.append(existing.id)
            reused.append({"id": existing.id, "nombre": existing.display_name})
            continue

        new = CompetitorProfile(
            org_id=dirigente.org_id,
            dirigente_objetivo_id=dirigente_id,
            display_name=nombre,
            partido=partido,
            cargo=cargo,
            platform="FACEBOOK",  # default — wizard no captura plataforma todavía
            profile_external_id=external_id,
            verified=False,
            notes=item.get("url_ref"),
            tags=[],
        )
        db.add(new)
        await db.flush()
        competidor_ids.append(new.id)
        created.append({"id": new.id, "nombre": new.display_name, "cargo": new.cargo})

    # Persistir array de IDs en dirigentes.competidor_directo_ids
    # (ahora apuntan a competitor_profiles.id, no a competidores legacy)
    dirigente.competidor_directo_ids = competidor_ids
    await db.commit()

    return {
        "dirigente_id": dirigente_id,
        "competidor_ids": competidor_ids,
        "created": created,
        "reused": reused,
        "total": len(competidor_ids),
    }
