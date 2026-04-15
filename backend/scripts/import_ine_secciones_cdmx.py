"""Importa shapefile INE de secciones electorales CDMX → ``secciones_electorales``.

Fase 2 del SEED-PLAN REV 3. El shapefile se descarga manualmente por el CEO
desde https://cartografia.ine.mx/sige8/ (Entidad CDMX, corte vigente) y se
deja en una ruta pasada via env `INE_SHP_PATH` (apunta al archivo `.shp`).

Usa ``ogr2ogr`` (GDAL CLI ya disponible en el container `crece-backend`) para
ingesta directa a Postgres como tabla staging, luego un INSERT con mapping
idempotente al schema real de `secciones_electorales`.

Schema destino (no modificar — ya existe en BD):
- ``seccion`` VARCHAR (formato 'EE-SSSS' entidad-seccion, ej. '09-0900')
- ``estado`` VARCHAR = 'Ciudad de México'
- ``distrito_federal`` VARCHAR
- ``distrito_local`` VARCHAR
- ``municipio`` VARCHAR (alcaldía)
- ``geometry`` GEOMETRY(MultiPolygon, 4326)

Idempotente: ``ON CONFLICT ... DO NOTHING`` por ``(estado, seccion)``.

Uso:
    docker exec -e INE_SHP_PATH=/app/data/raw/ine_cartografia/cdmx/SECCION.shp \\
        crece-backend python -m scripts.import_ine_secciones_cdmx

Opcional: `KEEP_STAGING=1` para conservar la tabla staging para debug.

Campos INE esperados en el SHP (nombres típicos de cartografia.ine.mx):
    ENTIDAD, SECCION, DISTRITO_F, DISTRITO_L, MUNICIPIO, NOMBRE_MUN
Si el corte usa otros nombres, ajustar en ``FIELD_MAP`` tras inspección.
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

# Alcaldías CDMX canónicas (para normalizar NOMBRE_MUN del SHP que viene en ALL CAPS).
ALCALDIAS_CDMX_CANON = {
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

# Posibles nombres de campo en el SHP (ajustar tras inspección si el corte difiere).
FIELD_MAP = {
    "seccion": ["SECCION", "seccion", "secc"],
    "distrito_federal": ["DISTRITO_F", "DISTRITO_FEDERAL", "DTTO_FED", "distrito_f"],
    "distrito_local": ["DISTRITO_L", "DISTRITO_LOCAL", "DTTO_LOC", "distrito_l"],
    "municipio": ["NOMBRE_MUN", "MUNICIPIO", "NOMBRE_MPO", "NOMGEO"],
}

STAGING_TABLE = "secciones_ine_staging"
ENTIDAD_ID = "09"  # CDMX

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("import_ine_cdmx")


def detect_field(cur, table: str, candidates: list[str]) -> str | None:
    cur.execute(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_name = %s
        """,
        (table,),
    )
    cols_lower = {r[0].lower(): r[0] for r in cur.fetchall()}
    for candidate in candidates:
        if candidate.lower() in cols_lower:
            return cols_lower[candidate.lower()]
    return None


def main() -> int:
    shp_path = os.environ.get("INE_SHP_PATH")
    if not shp_path:
        log.error(
            "INE_SHP_PATH env no definido. Descargar SHP desde "
            "https://cartografia.ine.mx/sige8/ y pasar ruta al archivo .shp."
        )
        return 1
    shp = Path(shp_path)
    if not shp.exists() or shp.suffix.lower() != ".shp":
        log.error("SHP no encontrado o ruta invalida: %s", shp_path)
        return 1

    # Importar deps solo cuando el script se ejecuta (para que el import
    # del módulo no falle en entornos sin psycopg2).
    from sqlalchemy import create_engine, text  # noqa: WPS433

    from app.core.config import settings  # noqa: WPS433

    pg_conn_dsn = settings.DATABASE_URL_SYNC.replace("postgresql+psycopg2://", "postgresql://")

    # Paso 1 — ogr2ogr a tabla staging.
    log.info("ogr2ogr -> %s", STAGING_TABLE)
    cmd = [
        "ogr2ogr",
        "-f",
        "PostgreSQL",
        f"PG:{pg_conn_dsn}",
        str(shp),
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
    log.debug("cmd: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        log.error("ogr2ogr falló: %s\n%s", result.returncode, result.stderr[-2000:])
        return result.returncode
    log.info("ogr2ogr OK")

    # Paso 2 — detectar nombres de columna reales en staging + migrar a secciones_electorales.
    engine = create_engine(settings.DATABASE_URL_SYNC, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        raw_conn = conn.connection
        cur = raw_conn.cursor()

        detected = {}
        for target, candidates in FIELD_MAP.items():
            col = detect_field(cur, STAGING_TABLE, candidates)
            if col is None:
                log.error(
                    "Campo '%s' no detectado en staging. Candidatos probados: %s",
                    target,
                    candidates,
                )
                log.info("Inspección de staging columns:")
                cur.execute(
                    f"SELECT column_name FROM information_schema.columns WHERE table_name=%s",
                    (STAGING_TABLE,),
                )
                for row in cur.fetchall():
                    log.info("  staging.%s", row[0])
                return 2
            detected[target] = col
        log.info("Campos detectados en staging: %s", detected)

        # CASE para normalizar alcaldía.
        case_alcaldia = "CASE "
        for raw, canon in ALCALDIAS_CDMX_CANON.items():
            case_alcaldia += f"WHEN UPPER(TRIM(s.{detected['municipio']})) = '{raw}' THEN '{canon}' "
        case_alcaldia += f"ELSE INITCAP(s.{detected['municipio']}) END"

        # Insert idempotente.
        insert_sql = f"""
            INSERT INTO secciones_electorales
                (seccion, estado, distrito_federal, distrito_local, municipio, geometry)
            SELECT
                '{ENTIDAD_ID}' || '-' || LPAD(s.{detected['seccion']}::text, 4, '0'),
                'Ciudad de México',
                s.{detected['distrito_federal']}::text,
                s.{detected['distrito_local']}::text,
                {case_alcaldia},
                ST_Multi(ST_Transform(s.geometry, 4326))
            FROM {STAGING_TABLE} s
            ON CONFLICT DO NOTHING
        """
        cur.execute(insert_sql)
        log.info("INSERT idempotente ejecutado")

        cur.execute("SELECT COUNT(*) FROM secciones_electorales")
        total = cur.fetchone()[0]
        cur.execute(
            "SELECT municipio, COUNT(*) FROM secciones_electorales "
            "WHERE estado = 'Ciudad de México' "
            "GROUP BY municipio ORDER BY municipio"
        )
        by_alc = cur.fetchall()
        log.info("TOTAL secciones_electorales = %d", total)
        log.info("Alcaldías distintas: %d", len(by_alc))
        for row in by_alc:
            log.info("  %-30s %5d", row[0], row[1])

        # Limpieza staging.
        if not os.environ.get("KEEP_STAGING"):
            cur.execute(f"DROP TABLE IF EXISTS {STAGING_TABLE}")
            log.info("staging dropped")
        else:
            log.info("staging conservada (KEEP_STAGING)")

    # Validación final.
    if len(by_alc) < 16:
        log.warning("Se esperaban 16 alcaldías CDMX — se encontraron %d", len(by_alc))
        return 3
    log.info("✅ Import CDMX completo — %d alcaldías, %d secciones totales.", len(by_alc), total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
