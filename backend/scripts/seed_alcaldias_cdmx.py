"""Seed S4.1 — Catálogo INEGI de las 16 alcaldías de CDMX.

Fuente primaria (opción 1 del plan aprobado por CEO 2026-04-11):
    Marco Geoestadístico INEGI 2023, entidad 09 (Ciudad de México),
    redistribuido como GeoJSON en github.com/PhantomInsights/mexico-geojson
    (mantiene CVEGEO, CVE_ENT, CVE_MUN, NOMGEO intactos del shapefile INEGI).

El archivo se cachea localmente en `backend/data/raw/cdmx_alcaldias_inegi_2023.geojson`
para que el seed sea idempotente y offline.

Uso:
    docker exec crece-backend python -m scripts.seed_alcaldias_cdmx

Criterio de aceptación (S4.1):
    16 rows en `alcaldias_cdmx`, `ST_Contains` funciona contra
    al menos un punto conocido de Cuauhtémoc.
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

import httpx
from shapely.geometry import shape
from shapely.geometry.multipolygon import MultiPolygon
from shapely.geometry.polygon import Polygon
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("seed_alcaldias_cdmx")

GEOJSON_URL = (
    "https://raw.githubusercontent.com/PhantomInsights/mexico-geojson/main/"
    "2023/states/Ciudad%20de%20M%C3%A9xico.json"
)
CACHE_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "raw" / "cdmx_alcaldias_inegi_2023.geojson"
)


def fetch_geojson() -> dict:
    if CACHE_PATH.exists():
        log.info("using cached geojson: %s", CACHE_PATH)
        return json.loads(CACHE_PATH.read_text())
    log.info("downloading geojson from INEGI mirror: %s", GEOJSON_URL)
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    resp = httpx.get(GEOJSON_URL, timeout=30.0, follow_redirects=True)
    resp.raise_for_status()
    CACHE_PATH.write_bytes(resp.content)
    return resp.json()


def to_multipolygon_wkt(geom_dict: dict) -> str:
    g = shape(geom_dict)
    if isinstance(g, Polygon):
        g = MultiPolygon([g])
    if not isinstance(g, MultiPolygon):
        raise ValueError(f"unexpected geometry type: {type(g).__name__}")
    return g.wkt


async def seed() -> int:
    geojson = fetch_geojson()
    features = geojson.get("features", [])
    if len(features) != 16:
        log.warning("expected 16 alcaldías, got %d", len(features))

    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    inserted = 0
    updated = 0
    async with async_session() as session:
        for feat in features:
            props = feat["properties"]
            cvegeo = props["CVEGEO"]
            if props.get("CVE_ENT") != "09":
                log.warning("skipping non-CDMX feature %s", cvegeo)
                continue
            wkt = to_multipolygon_wkt(feat["geometry"])

            existing = (
                await session.execute(
                    text("SELECT id FROM alcaldias_cdmx WHERE cvegeo = :c"),
                    {"c": cvegeo},
                )
            ).first()

            params = {
                "cvegeo": cvegeo,
                "cve_mun": props["CVE_MUN"],
                "nombre": props["NOMGEO"],
                "area": props.get("AREA"),
                "perim": props.get("PERIMETER"),
                "wkt": wkt,
            }
            if existing is None:
                await session.execute(
                    text(
                        "INSERT INTO alcaldias_cdmx "
                        "(cvegeo, cve_mun, nombre, area_km2, perimetro_km, geom) "
                        "VALUES (:cvegeo, :cve_mun, :nombre, :area, :perim, "
                        "ST_Multi(ST_GeomFromText(:wkt, 4326)))"
                    ),
                    params,
                )
                inserted += 1
            else:
                await session.execute(
                    text(
                        "UPDATE alcaldias_cdmx SET "
                        "geom = ST_Multi(ST_GeomFromText(:wkt, 4326)), "
                        "area_km2 = :area, perimetro_km = :perim, nombre = :nombre "
                        "WHERE cvegeo = :cvegeo"
                    ),
                    params,
                )
                updated += 1
        await session.commit()
    await engine.dispose()
    log.info("seed done: inserted=%d updated=%d", inserted, updated)
    return inserted + updated


if __name__ == "__main__":
    try:
        n = asyncio.run(seed())
        sys.exit(0 if n == 16 else 2)
    except Exception as exc:
        log.exception("seed failed: %s", exc)
        sys.exit(1)
