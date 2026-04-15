"""Importa shapefile INE de secciones electorales → ``secciones_electorales``.

Fase 2 del SEED-PLAN REV 3. Genérico para cualquier entidad federativa.

Uso:
    # CDMX (entidad 09)
    docker exec -e INE_SHP_PATH=/app/data/raw/ine_cartografia/cdmx/SECCION.shp \\
        crece-backend python -m scripts.import_ine_secciones cdmx

    # Oaxaca (entidad 20)
    docker exec -e INE_SHP_PATH=/app/data/raw/ine_cartografia/oaxaca/SECCION.shp \\
        crece-backend python -m scripts.import_ine_secciones oaxaca

SHP se descarga manualmente desde https://cartografia.ine.mx/sige8/ — portal SPA
sin URL directa pública.

Schema destino (existente en BD, no modificar):
- ``seccion`` VARCHAR (formato 'EE-SSSS', ej. '09-0900' CDMX, '20-0600' Oaxaca)
- ``estado`` VARCHAR
- ``distrito_federal`` VARCHAR
- ``distrito_local`` VARCHAR
- ``municipio`` VARCHAR
- ``geometry`` GEOMETRY(MultiPolygon, 4326)

Idempotente via ``ON CONFLICT DO NOTHING`` — re-run safe.
Deps runtime: ``ogr2ogr`` (GDAL CLI) incluido en container crece-backend.
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("import_ine")


# ─────────────────────────────────────────────────────────────────────
# Config por entidad
# ─────────────────────────────────────────────────────────────────────

# Alcaldías CDMX — mapeo CAPS del SHP → canonical INEGI (con acentos).
ALCALDIAS_CDMX_CANON: dict[str, str] = {
    "ALVARO OBREGON": "Álvaro Obregón",
    "AZCAPOTZALCO": "Azcapotzalco",
    "BENITO JUAREZ": "Benito Juárez",
    "COYOACAN": "Coyoacán",
    "CUAJIMALPA DE MORELOS": "Cuajimalpa de Morelos",
    "CUAUHTEMOC": "Cuauhtémoc",
    "GUSTAVO A MADERO": "Gustavo A. Madero",
    "GUSTAVO A. MADERO": "Gustavo A. Madero",
    "IZTACALCO": "Iztacalco",
    "IZTAPALAPA": "Iztapalapa",
    "LA MAGDALENA CONTRERAS": "La Magdalena Contreras",
    "MAGDALENA CONTRERAS": "La Magdalena Contreras",
    "MIGUEL HIDALGO": "Miguel Hidalgo",
    "MILPA ALTA": "Milpa Alta",
    "TLAHUAC": "Tláhuac",
    "TLALPAN": "Tlalpan",
    "VENUSTIANO CARRANZA": "Venustiano Carranza",
    "XOCHIMILCO": "Xochimilco",
}


@dataclass
class Entidad:
    codigo: str  # '09', '20', etc.
    estado_nombre: str  # 'Ciudad de México'
    municipios_esperados: int  # 16 (CDMX), 570 (Oaxaca)
    canon_map: dict[str, str] = field(default_factory=dict)
    # Si canon_map está vacío, el script usa INITCAP sobre el string tal cual.


ENTIDADES: dict[str, Entidad] = {
    "cdmx": Entidad(
        codigo="09",
        estado_nombre="Ciudad de México",
        municipios_esperados=16,
        canon_map=ALCALDIAS_CDMX_CANON,
    ),
    "oaxaca": Entidad(
        codigo="20",
        estado_nombre="Oaxaca",
        # Oaxaca tiene 570 municipios — imposible mapear a mano. Usamos INITCAP
        # contra el string CAPS del SHP. Si hay discrepancia con seed manual
        # posterior, se reconcilia por nombre canónico INEGI.
        municipios_esperados=570,
        canon_map={},
    ),
}


FIELD_MAP = {
    "seccion": ["SECCION", "seccion", "secc"],
    "distrito_federal": ["DISTRITO_F", "DISTRITO_FEDERAL", "DTTO_FED", "distrito_f"],
    "distrito_local": ["DISTRITO_L", "DISTRITO_LOCAL", "DTTO_LOC", "distrito_l"],
    "municipio": ["NOMBRE_MUN", "MUNICIPIO", "NOMBRE_MPO", "NOMGEO", "NOM_MUN"],
}

STAGING_TABLE = "secciones_ine_staging"


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────


def detect_field(cur, table: str, candidates: list[str]) -> str | None:
    cur.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name = %s",
        (table,),
    )
    cols_lower = {r[0].lower(): r[0] for r in cur.fetchall()}
    for candidate in candidates:
        if candidate.lower() in cols_lower:
            return cols_lower[candidate.lower()]
    return None


def run_ogr2ogr(shp_path: Path, pg_dsn: str) -> int:
    cmd = [
        "ogr2ogr",
        "-f",
        "PostgreSQL",
        f"PG:{pg_dsn}",
        str(shp_path),
        "-nln",
        STAGING_TABLE,
        "-nlt",
        "PROMOTE_TO_MULTI",
        "-t_srs",
        "EPSG:4326",
        "-overwrite",
        "-lco",
        "GEOMETRY_NAME=geometry",
        "-lco",
        "FID=gid",
        "--config",
        "PG_USE_COPY",
        "YES",
    ]
    log.info("ogr2ogr → %s", STAGING_TABLE)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    if result.returncode != 0:
        log.error("ogr2ogr falló (%d): %s", result.returncode, result.stderr[-2000:])
        return result.returncode
    log.info("ogr2ogr OK")
    return 0


def build_case_municipio(canon_map: dict[str, str], municipio_col: str) -> str:
    if not canon_map:
        # INITCAP simple. INE entrega municipios en CAPS; INITCAP genera 'San Juan Bautista'.
        return f"INITCAP(s.{municipio_col})"
    case = "CASE "
    for raw, canon in canon_map.items():
        # Escape comilla sencilla duplicando.
        raw_safe = raw.replace("'", "''")
        canon_safe = canon.replace("'", "''")
        case += f"WHEN UPPER(TRIM(s.{municipio_col})) = '{raw_safe}' THEN '{canon_safe}' "
    case += f"ELSE INITCAP(s.{municipio_col}) END"
    return case


# ─────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────


def main(entidad_key: str) -> int:
    if entidad_key not in ENTIDADES:
        log.error("Entidad '%s' desconocida. Opciones: %s", entidad_key, list(ENTIDADES))
        return 1
    ent = ENTIDADES[entidad_key]

    shp_path_str = os.environ.get("INE_SHP_PATH")
    if not shp_path_str:
        log.error(
            "INE_SHP_PATH env requerido. Descargar SHP desde "
            "https://cartografia.ine.mx/sige8/ entidad %s.",
            ent.estado_nombre,
        )
        return 1
    shp = Path(shp_path_str)
    if not shp.exists() or shp.suffix.lower() != ".shp":
        log.error("SHP no encontrado o invalido: %s", shp_path_str)
        return 1

    from sqlalchemy import create_engine  # noqa: WPS433

    from app.core.config import settings  # noqa: WPS433

    pg_dsn = settings.DATABASE_URL_SYNC.replace("postgresql+psycopg2://", "postgresql://")

    rc = run_ogr2ogr(shp, pg_dsn)
    if rc:
        return rc

    engine = create_engine(settings.DATABASE_URL_SYNC, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        raw_conn = conn.connection
        cur = raw_conn.cursor()

        detected: dict[str, str] = {}
        for target, candidates in FIELD_MAP.items():
            col = detect_field(cur, STAGING_TABLE, candidates)
            if col is None:
                log.error("Campo '%s' no detectado. Probados: %s", target, candidates)
                cur.execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_name = %s",
                    (STAGING_TABLE,),
                )
                for row in cur.fetchall():
                    log.info("  staging.%s", row[0])
                return 2
            detected[target] = col
        log.info("Campos detectados: %s", detected)

        case_municipio = build_case_municipio(ent.canon_map, detected["municipio"])
        estado_safe = ent.estado_nombre.replace("'", "''")

        insert_sql = f"""
            INSERT INTO secciones_electorales
                (seccion, estado, distrito_federal, distrito_local, municipio, geometry)
            SELECT
                '{ent.codigo}' || '-' || LPAD(s.{detected["seccion"]}::text, 4, '0'),
                '{estado_safe}',
                s.{detected["distrito_federal"]}::text,
                s.{detected["distrito_local"]}::text,
                {case_municipio},
                ST_Multi(ST_Transform(s.geometry, 4326))
            FROM {STAGING_TABLE} s
            ON CONFLICT DO NOTHING
        """
        cur.execute(insert_sql)
        log.info("INSERT idempotente ejecutado para %s", ent.estado_nombre)

        cur.execute(
            "SELECT COUNT(*) FROM secciones_electorales WHERE estado = %s",
            (ent.estado_nombre,),
        )
        total_estado = cur.fetchone()[0]
        cur.execute(
            "SELECT municipio, COUNT(*) FROM secciones_electorales "
            "WHERE estado = %s GROUP BY municipio ORDER BY municipio",
            (ent.estado_nombre,),
        )
        by_mun = cur.fetchall()
        log.info(
            "[%s] total=%d municipios=%d (esperado=%d)",
            ent.estado_nombre,
            total_estado,
            len(by_mun),
            ent.municipios_esperados,
        )
        # Preview (primeros 20 municipios).
        for row in by_mun[:20]:
            log.info("  %-35s %5d", row[0], row[1])
        if len(by_mun) > 20:
            log.info("  ... +%d municipios más", len(by_mun) - 20)

        if not os.environ.get("KEEP_STAGING"):
            cur.execute(f"DROP TABLE IF EXISTS {STAGING_TABLE}")
            log.info("staging dropped")

    if len(by_mun) < ent.municipios_esperados * 0.9:
        # Tolerancia 10% por si el corte INE tiene leves divergencias.
        log.warning(
            "Municipios (%d) por debajo del esperado (%d) × 0.9. Revisar nombres o campos.",
            len(by_mun),
            ent.municipios_esperados,
        )
        return 3

    log.info("✅ Import %s completo.", ent.estado_nombre)
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: import_ine_secciones.py <cdmx|oaxaca>")
        sys.exit(1)
    sys.exit(main(sys.argv[1].lower()))
