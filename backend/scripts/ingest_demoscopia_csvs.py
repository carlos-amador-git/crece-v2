"""Ingest 3 Demoscopía Digital CSVs into encuestas_publicas (Sprint 7 · 2026-05-09).

CSVs:
- presidenta_historico_2024_2026.csv (federal)
- gobernadores_historico_2022_2026.csv (estatal)
- alcaldes_historico_2021_2026.csv (municipal)

Cada fila CSV produce 2 filas BD (aprobacion + desaprobacion).

Usage:
  docker exec -e DATABASE_URL='postgresql+asyncpg://crece:crece_dev@db:5432/crece' \\
    crece-backend python /app/scripts/ingest_demoscopia_csvs.py [--dry-run]
"""
from __future__ import annotations

import argparse
import asyncio
import calendar
import csv
import os
import sys
from datetime import date
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

CSV_DIR = Path("/app/data/demoscopia_csvs")
FUENTE = "Demoscopía Digital"


def fecha_from(anio: int, mes: int) -> date:
    last_day = calendar.monthrange(anio, mes)[1]
    return date(anio, mes, last_day)


def normalize_partido(p: str | None) -> str | None:
    if not p:
        return None
    p = p.strip().upper()
    if p in {"INDEPENDIENTE", "SIN PARTIDO", "S/P", ""}:
        return None
    return p[:20]


def rows_from_presidenta(csv_path: Path) -> list[dict]:
    out: list[dict] = []
    with csv_path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                anio = int(row["anio"]); mes = int(row["mes"])
                aprueba = float(row["aprueba"]); desaprueba = float(row["desaprueba"])
            except (KeyError, ValueError):
                continue
            base = {
                "fuente": FUENTE,
                "fecha_publicacion": fecha_from(anio, mes),
                "ambito": "federal",
                "entidad": "México",
                "municipio": None,
                "actor_tipo": "presidenta",
                "actor_nombre": row["nombre"].strip()[:150],
                "actor_partido": normalize_partido(row.get("partido")),
            }
            for metrica, valor in (("aprobacion", aprueba), ("desaprobacion", desaprueba)):
                out.append({**base, "metrica": metrica, "valor_pct": valor})
    return out


def rows_from_gobernadores(csv_path: Path) -> list[dict]:
    out: list[dict] = []
    with csv_path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                anio = int(row["anio"]); mes = int(row["mes"])
                aprueba = float(row["aprueba"]); desaprueba = float(row["desaprueba"])
            except (KeyError, ValueError):
                continue
            base = {
                "fuente": FUENTE,
                "fecha_publicacion": fecha_from(anio, mes),
                "ambito": "estatal",
                "entidad": (row.get("estado") or "").strip()[:80] or None,
                "municipio": None,
                "actor_tipo": "gobernador",
                "actor_nombre": row["nombre"].strip()[:150],
                "actor_partido": normalize_partido(row.get("partido")),
            }
            for metrica, valor in (("aprobacion", aprueba), ("desaprobacion", desaprueba)):
                out.append({**base, "metrica": metrica, "valor_pct": valor})
    return out


def rows_from_alcaldes(csv_path: Path) -> list[dict]:
    out: list[dict] = []
    with csv_path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                anio = int(row["anio"]); mes = int(row["mes"])
                aprueba = float(row["aprueba"]); desaprueba = float(row["desaprueba"])
            except (KeyError, ValueError):
                continue
            base = {
                "fuente": FUENTE,
                "fecha_publicacion": fecha_from(anio, mes),
                "ambito": "municipal",
                "entidad": (row.get("estado") or "").strip()[:80] or None,
                "municipio": (row.get("municipio") or "").strip()[:120] or None,
                "actor_tipo": "alcalde",
                "actor_nombre": row["nombre"].strip()[:150],
                "actor_partido": normalize_partido(row.get("partido")),
            }
            for metrica, valor in (("aprobacion", aprueba), ("desaprobacion", desaprueba)):
                out.append({**base, "metrica": metrica, "valor_pct": valor})
    return out


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only-municipal", action="store_true", help="Solo alcaldes (test)")
    args = ap.parse_args()

    pres = CSV_DIR / "presidenta_historico_2024_2026.csv"
    gob = CSV_DIR / "gobernadores_historico_2022_2026.csv"
    alc = CSV_DIR / "alcaldes_historico_2021_2026.csv"

    rows: list[dict] = []
    if not args.only_municipal:
        if pres.exists():
            r = rows_from_presidenta(pres)
            print(f"[+] presidenta: {len(r)} filas BD desde {pres.name}")
            rows.extend(r)
        if gob.exists():
            r = rows_from_gobernadores(gob)
            print(f"[+] gobernadores: {len(r)} filas BD desde {gob.name}")
            rows.extend(r)
    if alc.exists():
        r = rows_from_alcaldes(alc)
        print(f"[+] alcaldes: {len(r)} filas BD desde {alc.name}")
        rows.extend(r)

    print(f"[+] Total filas a insertar: {len(rows)}")
    if args.dry_run:
        print("DRY-RUN: nada se insertó")
        return 0
    if not rows:
        print("ERROR: 0 filas — revisa CSV_DIR", file=sys.stderr)
        return 1

    eng = create_async_engine(os.environ["DATABASE_URL"], echo=False)
    Session = async_sessionmaker(eng, expire_on_commit=False)

    sql = text("""
        INSERT INTO encuestas_publicas (
            fuente, fecha_publicacion, ambito, entidad, municipio,
            actor_tipo, actor_nombre, actor_partido, metrica, valor_pct
        ) VALUES (
            :fuente, :fecha_publicacion, :ambito, :entidad, :municipio,
            :actor_tipo, :actor_nombre, :actor_partido, :metrica, :valor_pct
        )
        ON CONFLICT DO NOTHING
    """)

    BATCH = 500
    inserted = 0
    async with Session() as db:
        for i in range(0, len(rows), BATCH):
            chunk = rows[i:i + BATCH]
            await db.execute(sql, chunk)
            inserted += len(chunk)
            if (i // BATCH) % 5 == 0:
                print(f"  ... insertadas {inserted}/{len(rows)}")
        await db.commit()

    print(f"[OK] Insertadas {inserted} filas en encuestas_publicas")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
