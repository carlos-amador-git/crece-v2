"""Sección 7 · Seed competidores (D-22).

El cliente declara 3-5 competidores directos en el wizard. Se usan para:
- Bloque #04 benchmark vs competidores (antes bloqueado)
- Cálculo de quintiles comparativos
- Seguimiento de share of voice

Arquitectura D-22 opción B (confirmada en SPRINT-S5-SCOPING):
    No se crean dirigentes con flag · se usa la tabla ``competidores`` existente
    (models.benchmark). Además se popula ``dirigentes.competidor_directo_ids``
    con los IDs persistidos para consumo rápido desde el dashboard.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.benchmark import Competidor
from app.models.dirigente import Dirigente


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

        # Dedupe por nombre + cargo
        q = await db.execute(
            select(Competidor).where(
                Competidor.nombre == nombre,
                Competidor.cargo == cargo,
            )
        )
        existing = q.scalar_one_or_none()
        if existing is not None:
            competidor_ids.append(existing.id)
            reused.append({"id": existing.id, "nombre": existing.nombre})
            continue

        new = Competidor(
            nombre=nombre,
            cargo=cargo,
            partido=partido,
            es_rival=True,
        )
        db.add(new)
        await db.flush()
        competidor_ids.append(new.id)
        created.append({"id": new.id, "nombre": new.nombre, "cargo": new.cargo})

    # Persistir array de IDs en dirigentes.competidor_directo_ids
    dirigente.competidor_directo_ids = competidor_ids
    await db.commit()

    return {
        "dirigente_id": dirigente_id,
        "competidor_ids": competidor_ids,
        "created": created,
        "reused": reused,
        "total": len(competidor_ids),
    }
