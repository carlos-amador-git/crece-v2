"""Orchestrator Mitofsky PDFs → encuestas_publicas.

Lee `captures/mitofsky-gdrive-catalog.json`, descarga cada PDF, lo parsea con
el parser adecuado según tipo (gobernadores | alcaldes | presidente),
e inserta a BD con UPSERT idempotente.

Usage:
    docker exec crece-backend python scripts/ingest_mitofsky_pdfs.py [--type all|gobernadores|alcaldes|presidente] [--limit N] [--dry-run]
"""
from __future__ import annotations

import argparse
import asyncio
import io
import json
import logging
import os
import re
import sys
from pathlib import Path

import httpx
import pdfplumber
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

sys.path.insert(0, "/app")
from app.scrapers.encuestas_mitofsky_pdf import (  # noqa: E402
    EncuestaRow,
    detect_pdf_type,
    download_gdrive_pdf,
    parse_pdf_alcaldes,
    parse_pdf_gobernadores,
    parse_pdf_presidente,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("ingest_mitofsky")

DEFAULT_CATALOG = "/tmp/cat.json"

SLUGS_GOBERNADORES = re.compile(r"gobernador|governator", re.I)
SLUGS_ALCALDES = re.compile(r"alcald|150-alcald|presidentes-municipales|municipios", re.I)
SLUGS_PRESIDENTE = re.compile(
    r"presidenc|sheinbaum|amlo|lopez-obrador|llegar-a-su.*ano|llegar-a-su.*trimestre", re.I
)


def classify_entry(entry: dict) -> str:
    """Devuelve tipo: 'gobernadores' | 'alcaldes' | 'presidente' | 'unknown'."""
    title = (entry.get("post_title") or "") + " " + entry.get("post_url", "")
    if SLUGS_GOBERNADORES.search(title) and not SLUGS_ALCALDES.search(title):
        return "gobernadores"
    if SLUGS_ALCALDES.search(title):
        return "alcaldes"
    if SLUGS_PRESIDENTE.search(title) and "gobernador" not in title.lower():
        return "presidente"
    return "unknown"


def filter_catalog(catalog: list[dict], wanted_type: str) -> list[dict]:
    if wanted_type == "all":
        return [e for e in catalog if e.get("gdrive_id")]
    return [
        e for e in catalog
        if e.get("gdrive_id") and classify_entry(e) == wanted_type
    ]


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
                  AND actor_tipo = :actor_tipo
                LIMIT 1
            """),
            {"fuente": r.fuente, "fecha": r.fecha_publicacion,
             "entidad": r.entidad, "actor": r.actor_nombre,
             "metrica": r.metrica, "actor_tipo": r.actor_tipo},
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


def parse_dispatch(pdf_bytes: bytes, url_fuente: str, ptype: str, fallback_post_date: str | None = None) -> list[EncuestaRow]:
    if ptype == "gobernadores":
        return parse_pdf_gobernadores(pdf_bytes, url_fuente, fallback_post_date)
    if ptype == "alcaldes":
        return parse_pdf_alcaldes(pdf_bytes, url_fuente, fallback_post_date)
    if ptype == "presidente":
        return parse_pdf_presidente(pdf_bytes, url_fuente, fallback_post_date)
    return []


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", default=DEFAULT_CATALOG)
    ap.add_argument(
        "--type",
        choices=["all", "gobernadores", "alcaldes", "presidente"],
        default="all",
    )
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--throttle", type=float, default=2.0)
    ap.add_argument("--detect-from-pdf", action="store_true",
                    help="Si --type=all, detectar tipo del PDF (más lento pero exacto).")
    args = ap.parse_args()

    cat_path = Path(args.catalog)
    if not cat_path.exists():
        log.error("Catalog no encontrado: %s", cat_path)
        return 1
    catalog = json.loads(cat_path.read_text())
    targets = filter_catalog(catalog, args.type)
    log.info("Catalog: %d entries · target type=%s · %d targets",
             len(catalog), args.type, len(targets))

    if args.limit:
        targets = targets[: args.limit]
        log.info("Limit %d", len(targets))

    eng = create_async_engine(os.environ["DATABASE_URL"], echo=False)
    Session = async_sessionmaker(eng, expire_on_commit=False)

    total_inserted = total_skipped = 0
    failed: list[dict] = []
    by_type: dict[str, int] = {"gobernadores": 0, "alcaldes": 0, "presidente": 0, "unknown": 0}

    async with Session() as db:
        with httpx.Client(follow_redirects=True, timeout=60.0) as http:
            for i, e in enumerate(targets, 1):
                gid = e["gdrive_id"]
                url = e["post_url"]
                title = (e.get("post_title") or "")[:55]
                ptype_slug = classify_entry(e)
                log.info("[%d/%d] (%s) %s — %s", i, len(targets), ptype_slug, gid, title)
                try:
                    pdf_bytes = download_gdrive_pdf(gid, http=http)
                except Exception as ex:
                    log.error("  download FAILED: %s", ex)
                    failed.append({"gid": gid, "url": url, "stage": "download",
                                   "type": ptype_slug, "err": str(ex)})
                    continue

                # Verify ptype using PDF content if requested or if slug uncertain
                ptype = ptype_slug
                if args.detect_from_pdf or ptype_slug == "unknown":
                    try:
                        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                            pages_text = [(p.extract_text() or "") for p in pdf.pages]
                        ptype = detect_pdf_type(pages_text)
                    except Exception:
                        ptype = "unknown"

                try:
                    rows = parse_dispatch(pdf_bytes, url, ptype, fallback_post_date=e.get("post_date"))
                except Exception as ex:
                    log.error("  parse FAILED: %s", ex)
                    failed.append({"gid": gid, "url": url, "stage": "parse",
                                   "type": ptype, "err": str(ex)})
                    continue
                if not rows:
                    log.warning("  parse 0 rows (type=%s)", ptype)
                    failed.append({"gid": gid, "url": url, "stage": "parse",
                                   "type": ptype, "err": "0 rows"})
                    continue

                ins, skp = await upsert_rows(db, rows, dry_run=args.dry_run)
                total_inserted += ins
                total_skipped += skp
                by_type[ptype if ptype in by_type else "unknown"] += ins
                log.info("  rows=%d  inserted=%d  skipped=%d", len(rows), ins, skp)
                await asyncio.sleep(args.throttle)

    print()
    print("=" * 60)
    print(f"DONE  · {len(targets)} PDFs procesados · type={args.type}")
    print(f"  inserted total: {total_inserted}")
    print(f"  skipped total:  {total_skipped} (dedupe)")
    print(f"  failed:         {len(failed)}")
    print(f"  by type: {by_type}")
    if failed:
        print("\nFailures:")
        for f in failed[:15]:
            print(f"  {f['stage']:<8s} {f['type']:<14s} {f['gid']:<35s} {f['err'][:50]}")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
