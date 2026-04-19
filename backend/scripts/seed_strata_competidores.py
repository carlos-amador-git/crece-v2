"""Seed Sprint S1 T2 — estrato_politico + data_fidelity_tier + data_origin por dirigente.

Consume los JSON canónicos generados en Sprint S0:
- backend/research/2026-04-19/settings_strata.json
- backend/research/2026-04-19/settings_fidelity.json

Mapeo heurístico JSON key → DB dirigente por coincidencia aproximada del full_name.

Competidor_directo_ids NO se pobla aquí — requiere input CEO o research previo explícito
y se deja vacío (default '{}'). La semilla se marca como completa solo para los 3 campos
calibrables sin input humano externo.

Idempotente: puede correrse N veces sin duplicar ni sobrescribir valores válidos previos.
"""
from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.dirigente import Dirigente

SCRIPT_DIR = Path(__file__).resolve().parent
# En container: /app/scripts/ → busca /app/research; local: backend/scripts/ → backend/research
if (SCRIPT_DIR.parent / "research").exists():
    RESEARCH_ROOT = SCRIPT_DIR.parent / "research"
else:
    RESEARCH_ROOT = SCRIPT_DIR.parent.parent / "backend/research"
STRATA_PATH = RESEARCH_ROOT / "2026-04-19/settings_strata.json"
FIDELITY_PATH = RESEARCH_ROOT / "2026-04-19/settings_fidelity.json"


# Mapeo explícito JSON key → substring del full_name en DB.
# Evita ambigüedad de matching heurístico.
JSON_KEY_TO_NAME_SUBSTR: dict[str, str] = {
    "alejandro_pinha": "Piña",
    "rafael_solano": "Solano",
    "saymi_pineda": "Pineda",
    "yessenia_nolasco": "Nolasco",
    "gabriela_jimenez": "Jiménez",
    "cesar_cravioto": "Cravioto",
    "laura_ballesteros": "Ballesteros",
    "jorge_alvarez_maynez": "Máynez",
    # Fidelity JSON usa claves distintas (cortas)
    "pinha": "Piña",
    "solano": "Solano",
    "pineda": "Pineda",
    "nolasco": "Nolasco",
    "jimenez": "Jiménez",
    "cravioto": "Cravioto",
    "ballesteros": "Ballesteros",
    "maynez": "Máynez",
}


def estrato_to_db_value(raw: str) -> str:
    """Normaliza el valor 'Mid-Tier' de JSON al valor 'Mid' del CHECK constraint."""
    if raw == "Mid-Tier":
        return "Mid"
    return raw


def normalize_tier(raw: str) -> str:
    """Convierte 'T3-inferido' a 'T3' (el tier efectivo); preserva T1/T2/T3/N-A."""
    if raw.startswith("T3"):
        return "T3"
    if raw == "N-A":
        return "N-A"
    return raw


async def find_dirigente_by_substr(session: AsyncSession, name_substr: str) -> Dirigente | None:
    """Busca un dirigente cuyo full_name contenga el substring (case insensitive)."""
    escaped = re.escape(name_substr)
    pattern = f"%{name_substr}%"
    stmt = select(Dirigente).where(Dirigente.full_name.ilike(pattern))
    result = await session.execute(stmt)
    rows = result.scalars().all()
    if len(rows) == 1:
        return rows[0]
    if len(rows) > 1:
        print(f"  ⚠️  Ambigüedad: {len(rows)} matches para '{name_substr}': {[r.full_name for r in rows]}")
        return None
    return None


async def seed() -> None:
    print("=== Sprint S1 T2 — Seed estrato_politico + data_fidelity_tier + data_origin ===\n")

    strata_raw = json.loads(STRATA_PATH.read_text())
    fidelity_raw = json.loads(FIDELITY_PATH.read_text())

    strata_by_key = strata_raw.get("dirigentes", {})
    fidelity_by_key = fidelity_raw.get("asignaciones_pre_venta", {})

    summary = {
        "updated": 0,
        "missing_in_db": [],
        "ambiguous": [],
        "skipped_no_data": [],
    }

    async with async_session_factory() as session:
        # Iterar los 8 dirigentes esperados (unión de keys de ambos JSON)
        all_keys = set(strata_by_key.keys()) | set(fidelity_by_key.keys())
        for json_key in sorted(all_keys):
            name_substr = JSON_KEY_TO_NAME_SUBSTR.get(json_key)
            if not name_substr:
                print(f"  ❌ Key no mapeada: '{json_key}'")
                summary["missing_in_db"].append(json_key)
                continue

            dirigente = await find_dirigente_by_substr(session, name_substr)
            if not dirigente:
                print(f"  ❌ No hay dirigente en DB para '{json_key}' ({name_substr})")
                summary["missing_in_db"].append(json_key)
                continue

            # Determinar estrato (preferir el JSON strata con más info)
            strata_info: dict[str, Any] | None = strata_by_key.get(json_key)
            fidelity_info: dict[str, str] | None = fidelity_by_key.get(json_key)

            # Buscar alias corto si la key larga no aparece en fidelity
            if fidelity_info is None:
                short_key = json_key.split("_")[-1] if "_" in json_key else json_key
                fidelity_info = fidelity_by_key.get(short_key)

            values: dict[str, Any] = {}

            if strata_info and strata_info.get("estrato"):
                values["estrato_politico"] = estrato_to_db_value(strata_info["estrato"])

            if fidelity_info:
                # Normalizar cada valor de tier
                normalized_fidelity = {
                    plataforma: normalize_tier(tier)
                    for plataforma, tier in fidelity_info.items()
                }
                values["data_fidelity_tier"] = normalized_fidelity

                # data_origin global = max tier disponible (T1>T2>T3>N-A), T3 por default
                tiers = set(normalized_fidelity.values()) - {"N-A"}
                if "T1" in tiers:
                    values["data_origin"] = "T1"
                elif "T2" in tiers:
                    values["data_origin"] = "T2"
                elif "T3" in tiers:
                    values["data_origin"] = "T3"
                else:
                    values["data_origin"] = "N-A"

            if not values:
                summary["skipped_no_data"].append(json_key)
                print(f"  ⚠️  Sin data para '{json_key}' — skip")
                continue

            # Update
            stmt = update(Dirigente).where(Dirigente.id == dirigente.id).values(**values)
            await session.execute(stmt)
            summary["updated"] += 1
            print(
                f"  ✅ {dirigente.full_name} (id={dirigente.id}) · "
                f"estrato={values.get('estrato_politico', '—')} · "
                f"data_origin={values.get('data_origin', '—')} · "
                f"fidelity_platforms={len(values.get('data_fidelity_tier', {}))}"
            )

        await session.commit()

    print("\n=== Resumen ===")
    print(f"  Actualizados: {summary['updated']}")
    if summary["missing_in_db"]:
        print(f"  Missing en DB: {summary['missing_in_db']}")
    if summary["ambiguous"]:
        print(f"  Ambiguos (match múltiple): {summary['ambiguous']}")
    if summary["skipped_no_data"]:
        print(f"  Skip por sin data: {summary['skipped_no_data']}")
    print("\nNota: 'competidor_directo_ids' NO se pobla por este script.")
    print("      Requiere input CEO (30min) o research previo explícito.")
    print("      Default '{}' se mantiene hasta entonces.")


if __name__ == "__main__":
    asyncio.run(seed())
