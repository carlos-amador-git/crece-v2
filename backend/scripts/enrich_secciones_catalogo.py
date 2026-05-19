#!/usr/bin/env python3
"""
Enrich secciones_geo_cdmx with data from master_catalogo.csv.

Adds: volatilidad, estrato, lista_nominal, categoria, dtto_local_cat, dtto_fed_cat, alcaldia
Idempotent — safe to run multiple times.

Usage:
    docker exec -i crece-backend python scripts/enrich_secciones_catalogo.py
    # or locally:
    python backend/scripts/enrich_secciones_catalogo.py
"""
import csv
import os
import sys

import psycopg2

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://crece:crece_dev@localhost:5438/crece",
)

CSV_PATH = os.environ.get(
    "CATALOGO_CSV",
    os.path.join(os.path.dirname(__file__), "..", "data", "raw", "mc_original", "master_catalogo.csv"),
)


def main():
    csv_path = os.path.abspath(CSV_PATH)
    if not os.path.exists(csv_path):
        print(f"ERROR: CSV not found at {csv_path}")
        sys.exit(1)

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # Step 1: Add columns if they don't exist
    columns = [
        ("volatilidad", "DOUBLE PRECISION"),
        ("estrato", "VARCHAR(20)"),
        ("lista_nominal", "INTEGER"),
        ("categoria", "VARCHAR(10)"),
        ("dtto_local_cat", "INTEGER"),
        ("dtto_fed_cat", "INTEGER"),
        ("alcaldia", "VARCHAR(80)"),
        ("nivel_socioeconomico", "VARCHAR(80)"),
    ]

    for col_name, col_type in columns:
        cur.execute(f"""
            DO $$
            BEGIN
                ALTER TABLE secciones_geo_cdmx ADD COLUMN {col_name} {col_type};
            EXCEPTION WHEN duplicate_column THEN
                NULL;
            END $$;
        """)

    conn.commit()
    print("Columns ensured.")

    # Step 2: Load CSV into temp table
    cur.execute("""
        CREATE TEMP TABLE _catalogo_tmp (
            id TEXT,
            alcaldia TEXT,
            clave_ut TEXT,
            cabecera TEXT,
            dtto_local TEXT,
            parcial_completa TEXT,
            circunscripcion_2022 TEXT,
            dtto_fed TEXT,
            seccion TEXT,
            grado_estudios TEXT,
            p_viv_inter TEXT,
            estrato TEXT,
            nivel_socioeconomico TEXT,
            resumen_nivel TEXT,
            lista_nominal TEXT,
            volatilidad TEXT,
            categoria TEXT,
            circunscripcion_2024 TEXT
        );
    """)

    with open(csv_path, encoding="latin-1") as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        rows_loaded = 0
        for row in reader:
            if len(row) < 18:
                continue
            seccion = row[8].strip()
            if not seccion:
                continue
            cur.execute(
                "INSERT INTO _catalogo_tmp VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                row[:18],
            )
            rows_loaded += 1

    conn.commit()
    print(f"Loaded {rows_loaded} rows from CSV into temp table.")

    # Step 3: UPDATE join
    cur.execute("""
        UPDATE secciones_geo_cdmx g
        SET
            volatilidad = NULLIF(c.volatilidad, '')::double precision,
            estrato = NULLIF(TRIM(c.estrato), ''),
            lista_nominal = NULLIF(c.lista_nominal, '')::integer,
            categoria = NULLIF(TRIM(c.categoria), ''),
            dtto_local_cat = NULLIF(c.dtto_local, '')::integer,
            dtto_fed_cat = NULLIF(c.dtto_fed, '')::integer,
            alcaldia = NULLIF(TRIM(c.alcaldia), ''),
            nivel_socioeconomico = NULLIF(TRIM(c.nivel_socioeconomico), '')
        FROM _catalogo_tmp c
        WHERE g.seccion::int = c.seccion::int;
    """)

    updated = cur.rowcount
    conn.commit()

    # Step 4: Report
    cur.execute("SELECT COUNT(*) FROM secciones_geo_cdmx WHERE volatilidad IS NOT NULL;")
    enriched = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM secciones_geo_cdmx WHERE volatilidad IS NULL;")
    missing = cur.fetchone()[0]

    cur.execute("""
        SELECT alcaldia, COUNT(*), ROUND(AVG(volatilidad)::numeric, 2) as avg_vol,
               ROUND(AVG(lista_nominal)::numeric, 0) as avg_ln
        FROM secciones_geo_cdmx
        WHERE alcaldia IS NOT NULL
        GROUP BY alcaldia
        ORDER BY alcaldia;
    """)
    stats = cur.fetchall()

    print("\nResults:")
    print(f"  Updated: {updated} rows")
    print(f"  Enriched: {enriched} / {enriched + missing} secciones")
    print(f"  Missing (no match in CSV): {missing}")
    print("\nPer alcaldía:")
    print(f"  {'Alcaldía':<25} {'Secciones':>10} {'Avg Vol':>10} {'Avg LN':>10}")
    print(f"  {'-'*55}")
    for row in stats:
        print(f"  {row[0]:<25} {row[1]:>10} {row[2]:>10} {row[3]:>10}")

    cur.close()
    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
