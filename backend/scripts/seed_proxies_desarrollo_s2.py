"""Seed proxies de desarrollo D-22 — Sprint S2.

⚠️ ============================================================
   PROXIES DE DESARROLLO — NO PRODUCCIÓN
⚠️ ============================================================

Los 8 dirigentes del piloto NO tienen ``competidor_directo_ids`` reales. El
cliente los declara en el Onboarding Wizard S5 (D-22). Para que el bloque #04
Benchmark del Sprint S2 pueda computar sobre datos, se inyectan proxies
razonables usando los otros dirigentes del piloto como competidores sintéticos.

Este fixture vive SOLO durante el desarrollo S2 y debe ser reemplazado por
input real del cliente en S5. El script es idempotente: si un dirigente ya
tiene el mapeo del proxy, se saltea con un mensaje.

Mapeo aplicado (razonado — mismo rango geográfico o de estrato político):

    1 Piña (MC CDMX Nano)       → [2, 5, 8]  Solano, Jiménez, Ballesteros
    2 Solano (MC CDMX Nano mini) → [1]        Piña
    3 Pineda (MORENA Oaxaca)    → [4]        Nolasco (otra secretaria Oax.)
    4 Nolasco (MORENA Oaxaca)   → [3]        Pineda
    5 Jiménez (MORENA CDMX Mic) → [8, 7]     Ballesteros, Máynez
    6 Cravioto (MORENA CDMX)    → [1, 5]     Piña, Jiménez (mismo rango urbano CDMX)
    7 Máynez (MC Federal Macro) → [5, 8]     Jiménez, Ballesteros
    8 Ballesteros (MC Fed Micro) → [5, 7]     Jiménez, Máynez

Nota de fidelidad: tres son MORENA y cinco MC — el proxy NO implica que sean
competidores reales, solo que están en rangos geográficos o de estrato similares.
En producción (S5) cada cliente declarará sus 3-5 competidores directos reales
por nombre.

Uso::

    python backend/scripts/seed_proxies_desarrollo_s2.py
    python backend/scripts/seed_proxies_desarrollo_s2.py --dry-run

Desbloquea: bloque #04 Benchmark + bloque #08 SoV (ambos dependen de
``competidor_directo_ids`` no vacío).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select, update  # noqa: E402

from app.core.database import async_session_factory  # noqa: E402
from app.models.dirigente import Dirigente  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("seed_proxies_desarrollo_s2")


# Mapeo fixture S2 — ver docstring del módulo para la justificación razonada.
# NOTE: es un fixture de desarrollo, NO es una declaración real del cliente.
PROXY_MAP: dict[int, list[int]] = {
    1: [2, 5, 8],
    2: [1, 5, 8],
    3: [4],
    4: [3],
    5: [8, 7],
    6: [1, 5],
    7: [5, 8],
    8: [5, 7],
}


async def run(dry_run: bool = False) -> tuple[int, int, int]:
    """Aplica el seed. Devuelve (updated, skipped, missing)."""
    banner = (
        "\n"
        + "=" * 64
        + "\n"
        + "⚠️  PROXIES DE DESARROLLO — NO PRODUCCIÓN\n"
        + "   Fixture S2 D-22. Reemplazar por declaración real Onboarding S5.\n"
        + "=" * 64
        + "\n"
    )
    logger.warning(banner)

    updated = 0
    skipped = 0
    missing = 0

    async with async_session_factory() as session:
        stmt = select(Dirigente).where(Dirigente.id.in_(PROXY_MAP.keys()))
        result = await session.execute(stmt)
        by_id = {d.id: d for d in result.scalars().all()}

        for did, proxies in PROXY_MAP.items():
            d = by_id.get(did)
            if d is None:
                logger.error("dirigente_id=%d no existe en DB — revisar seed", did)
                missing += 1
                continue

            current = list(d.competidor_directo_ids or [])
            if sorted(current) == sorted(proxies):
                logger.info(
                    "skip id=%d %s — ya tiene proxies %s",
                    did,
                    d.full_name,
                    proxies,
                )
                skipped += 1
                continue

            if current:
                logger.warning(
                    "id=%d %s — reemplazando competidor_directo_ids previos %s → %s",
                    did,
                    d.full_name,
                    current,
                    proxies,
                )

            if dry_run:
                logger.info(
                    "DRY-RUN id=%d %s → competidor_directo_ids=%s",
                    did,
                    d.full_name,
                    proxies,
                )
                updated += 1
                continue

            await session.execute(
                update(Dirigente)
                .where(Dirigente.id == did)
                .values(competidor_directo_ids=proxies)
            )
            logger.info(
                "updated id=%d %s → competidor_directo_ids=%s",
                did,
                d.full_name,
                proxies,
            )
            updated += 1

        if not dry_run:
            await session.commit()

    logger.info(
        "Cierre: updated=%d skipped=%d missing=%d (dry_run=%s)",
        updated,
        skipped,
        missing,
        dry_run,
    )
    return updated, skipped, missing


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed proxies desarrollo D-22 — Sprint S2 (NO PRODUCCIÓN)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="No hace UPDATE, solo imprime el plan",
    )
    args = parser.parse_args()

    updated, skipped, missing = asyncio.run(run(dry_run=args.dry_run))
    sys.exit(2 if missing else 0)


if __name__ == "__main__":
    main()
