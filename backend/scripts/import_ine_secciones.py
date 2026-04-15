"""Importa shapefile INE de secciones electorales → ``secciones_electorales``.

Fase 2 del SEED-PLAN REV 3. Genérico para cualquier entidad federativa.

Uso:
    # CDMX (entidad 09) — pasar el directorio que contiene SECCION.shp + MUNICIPIO.shp
    docker exec -e INE_SHP_DIR=/app/data/raw/ine_cartografia/cdmx/09 \\
        crece-backend python -m scripts.import_ine_secciones cdmx

    # Oaxaca (entidad 20)
    docker exec -e INE_SHP_DIR=/app/data/raw/ine_cartografia/oaxaca/20 \\
        crece-backend python -m scripts.import_ine_secciones oaxaca

El SECCION.shp trae ``municipio`` como código numérico; el nombre vive en
MUNICIPIO.shp. El script carga ambos como staging y JOIN por (entidad, municipio).

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
    "seccion": ["seccion", "SECCION", "secc"],
    "distrito_federal": ["distrito_f", "DISTRITO_F", "DISTRITO_FEDERAL", "DTTO_FED"],
    "distrito_local": ["distrito_l", "DISTRITO_L", "DISTRITO_LOCAL", "DTTO_LOC"],
    "municipio_cod": ["municipio", "MUNICIPIO"],
    "entidad_cod": ["entidad", "ENTIDAD"],
}
MUN_FIELDS = {
    "municipio_cod": ["municipio", "MUNICIPIO"],
    "entidad_cod": ["entidad", "ENTIDAD"],
    "nombre": ["nombre", "NOMBRE", "NOMBRE_MUN", "NOM_MUN", "NOMGEO"],
}

STAGING_SECCIONES = "secciones_ine_staging"
STAGING_MUNICIPIOS = "municipios_ine_staging"


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


def run_ogr2ogr(shp_path: Path, pg_dsn: str, staging_table: str, with_geom: bool = True) -> int:
    cmd = [
        "ogr2ogr",
        "-f",
        "PostgreSQL",
        f"PG:{pg_dsn}",
        str(shp_path),
        "-nln",
        staging_table,
        "-nlt",
        "PROMOTE_TO_MULTI" if with_geom else "NONE",
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
    log.info("ogr2ogr %s → %s", shp_path.name, staging_table)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    if result.returncode != 0:
        log.error("ogr2ogr falló (%d): %s", result.returncode, result.stderr[-2000:])
        return result.returncode
    log.info("  OK")
    return 0


def build_case_municipio(canon_map: dict[str, str], qualified_col: str) -> str:
    """``qualified_col`` viene ya con alias, por ejemplo ``m.nombre`` o ``s.nombre``."""
    if not canon_map:
        return f"INITCAP({qualified_col})"
    case = "CASE "
    for raw, canon in canon_map.items():
        raw_safe = raw.replace("'", "''")
        canon_safe = canon.replace("'", "''")
        case += f"WHEN UPPER(TRIM({qualified_col})) = '{raw_safe}' THEN '{canon_safe}' "
    case += f"ELSE INITCAP({qualified_col}) END"
    return case


# ─────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────


def main(entidad_key: str) -> int:
    if entidad_key not in ENTIDADES:
        log.error("Entidad '%s' desconocida. Opciones: %s", entidad_key, list(ENTIDADES))
        return 1
    ent = ENTIDADES[entidad_key]

    shp_dir_str = os.environ.get("INE_SHP_DIR") or os.environ.get("INE_SHP_PATH")
    if not shp_dir_str:
        log.error(
            "INE_SHP_DIR env requerido. Debe apuntar al directorio con SECCION.shp "
            "y MUNICIPIO.shp (entidad %s).",
            ent.estado_nombre,
        )
        return 1
    shp_dir = Path(shp_dir_str)
    if shp_dir.is_file() and shp_dir.suffix.lower() == ".shp":
        shp_dir = shp_dir.parent
    seccion_shp = shp_dir / "SECCION.shp"
    municipio_shp = shp_dir / "MUNICIPIO.shp"
    if not seccion_shp.exists() or not municipio_shp.exists():
        log.error(
            "Falta SECCION.shp (%s) o MUNICIPIO.shp (%s)",
            seccion_shp,
            municipio_shp,
        )
        return 1

    from sqlalchemy import create_engine  # noqa: WPS433

    from app.core.config import settings  # noqa: WPS433

    pg_dsn = settings.DATABASE_URL_SYNC.replace("postgresql+psycopg2://", "postgresql://")

    rc = run_ogr2ogr(seccion_shp, pg_dsn, STAGING_SECCIONES, with_geom=True)
    if rc:
        return rc
    rc = run_ogr2ogr(municipio_shp, pg_dsn, STAGING_MUNICIPIOS, with_geom=False)
    if rc:
        return rc

    engine = create_engine(settings.DATABASE_URL_SYNC, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        raw_conn = conn.connection
        cur = raw_conn.cursor()

        det_sec: dict[str, str] = {}
        for target, candidates in FIELD_MAP.items():
            col = detect_field(cur, STAGING_SECCIONES, candidates)
            if col is None:
                log.error("Campo '%s' no detectado en SECCION. Probados: %s", target, candidates)
                return 2
            det_sec[target] = col
        log.info("Secciones: %s", det_sec)

        det_mun: dict[str, str] = {}
        for target, candidates in MUN_FIELDS.items():
            col = detect_field(cur, STAGING_MUNICIPIOS, candidates)
            if col is None:
                log.error("Campo '%s' no detectado en MUNICIPIO. Probados: %s", target, candidates)
                return 2
            det_mun[target] = col
        log.info("Municipios: %s", det_mun)

        case_municipio = build_case_municipio(ent.canon_map, f"m.{det_mun['nombre']}")
        estado_safe = ent.estado_nombre.replace("'", "''")

        insert_sql = f"""
            INSERT INTO secciones_electorales
                (seccion, estado, distrito_federal, distrito_local, municipio, geometry)
            SELECT
                '{ent.codigo}' || '-' || LPAD(s.{det_sec["seccion"]}::text, 4, '0'),
                '{estado_safe}',
                s.{det_sec["distrito_federal"]}::text,
                s.{det_sec["distrito_local"]}::text,
                {case_municipio},
                ST_Multi(ST_Transform(s.geometry, 4326))
            FROM {STAGING_SECCIONES} s
            JOIN {STAGING_MUNICIPIOS} m
              ON m.{det_mun["entidad_cod"]} = s.{det_sec["entidad_cod"]}
             AND m.{det_mun["municipio_cod"]} = s.{det_sec["municipio_cod"]}
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
        for row in by_mun[:20]:
            log.info("  %-35s %5d", row[0], row[1])
        if len(by_mun) > 20:
            log.info("  ... +%d municipios más", len(by_mun) - 20)

        if not os.environ.get("KEEP_STAGING"):
            cur.execute(f"DROP TABLE IF EXISTS {STAGING_SECCIONES}")
            cur.execute(f"DROP TABLE IF EXISTS {STAGING_MUNICIPIOS}")
            log.info("staging dropped")

    if len(by_mun) < ent.municipios_esperados * 0.9:
        log.warning(
            "Municipios (%d) por debajo del esperado (%d) × 0.9.",
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
