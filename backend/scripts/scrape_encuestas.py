"""Corre scrapers de encuestas (Oraculus, Demoscopía) e ingesta a BD.

Usage:
  docker exec crece-backend python scripts/scrape_encuestas.py
  docker exec crece-backend python scripts/scrape_encuestas.py --source oraculus
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.scrapers.encuestas_oraculus import scrape_oraculus


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["oraculus", "all"], default="all")
    ap.add_argument("--historical", action="store_true", help="Incluir presidentes históricos (AMLO, EPN, ...)")
    args = ap.parse_args()

    eng = create_async_engine(os.environ["DATABASE_URL"], echo=False)
    Session = async_sessionmaker(eng, expire_on_commit=False)

    results = {}
    async with Session() as db:
        if args.source in ("oraculus", "all"):
            try:
                r = await scrape_oraculus(db, active_only=not args.historical)
                results["oraculus"] = r
                print(f"✔ Oraculus: {r['rows_inserted']} nuevas, {r['rows_skipped_duplicate']} duplicadas")
            except Exception as e:
                results["oraculus"] = {"error": str(e)}
                print(f"✗ Oraculus FAILED: {e}")

    print("\n" + json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
