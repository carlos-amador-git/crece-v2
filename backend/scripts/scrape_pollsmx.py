"""Orchestrator PollsMX → encuestas_publicas."""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

sys.path.insert(0, "/app")
from app.scrapers.encuestas_pollsmx import EncuestaRow, scrape_pollsmx  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("scrape_pollsmx")


async def upsert_rows(db, rows: list[EncuestaRow], dry_run: bool = False) -> tuple[int, int]:
    if dry_run:
        return 0, 0
    inserted = skipped = 0
    for r in rows:
        existing = (await db.execute(
            text("""
                SELECT 1 FROM encuestas_publicas
                WHERE fuente = :fuente
                  AND fecha_publicacion = :fecha
                  AND COALESCE(entidad, '') = COALESCE(:entidad, '')
                  AND actor_nombre = :actor
                  AND metrica = :metrica
                LIMIT 1
            """),
            {"fuente": r.fuente, "fecha": r.fecha_publicacion,
             "entidad": r.entidad, "actor": r.actor_nombre, "metrica": r.metrica},
        )).first()
        if existing:
            skipped += 1
            continue
        await db.execute(
            text("""
                INSERT INTO encuestas_publicas (
                    fuente, fecha_publicacion, ambito, entidad,
                    actor_tipo, actor_nombre, actor_partido,
                    metrica, valor_pct, valor_delta_vs_anterior,
                    tamanyo_muestra, margen_error, url_fuente, created_at
                ) VALUES (
                    :fuente, :fecha, :ambito, :entidad,
                    :actor_tipo, :actor, :partido,
                    :metrica, :valor, NULL,
                    NULL, NULL, :url, NOW()
                )
            """),
            {
                "fuente": r.fuente, "fecha": r.fecha_publicacion,
                "ambito": r.ambito, "entidad": r.entidad,
                "actor_tipo": r.actor_tipo, "actor": r.actor_nombre,
                "partido": r.actor_partido,
                "metrica": r.metrica, "valor": r.valor_pct,
                "url": r.url_fuente,
            },
        )
        inserted += 1
    await db.commit()
    return inserted, skipped


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    eng = create_async_engine(os.environ["DATABASE_URL"], echo=False)
    Session = async_sessionmaker(eng, expire_on_commit=False)

    with httpx.Client(follow_redirects=True, timeout=30.0) as http:
        rows = scrape_pollsmx(http)
    log.info("Total rows extraídas: %d", len(rows))

    async with Session() as db:
        ins, skp = await upsert_rows(db, rows, dry_run=args.dry_run)

    print()
    print("=" * 60)
    print(f"DONE PollsMX")
    print(f"  rows extraídas:  {len(rows)}")
    print(f"  inserted:        {ins}")
    print(f"  skipped (dedup): {skp}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
