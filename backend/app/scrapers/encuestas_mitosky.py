"""Importador Mitofsky — Aprobación Histórica de Gobernadores.

Lee el Excel /uploads/Aprobacion_Gobernadores_Historico.xlsx (o path custom)
y hace upsert a encuestas_publicas.

Formato del Excel esperado:
    Columnas: Lugar_*, Estado, Gobernador, {Mes_Año}...
    Filas:    una por gobernador, valores = % aprobación

Uso:
    python -m app.scrapers.encuestas_mitosky                          # desde BD container
    python -m app.scrapers.encuestas_mitosky --file /path/to/file.xlsx
    python -m app.scrapers.encuestas_mitosky --dry-run
"""

from __future__ import annotations

import argparse
import datetime as dt
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("encuestas_mitosky")

FUENTE = "Mitofsky"

# Mapeo abreviatura INE → nombre completo normalizado
ESTADO_MAP: dict[str, str] = {
    "AGS": "Aguascalientes",
    "BC": "Baja California",
    "BCS": "Baja California Sur",
    "CAMP": "Campeche",
    "CHIS": "Chiapas",
    "CHIH": "Chihuahua",
    "COAH": "Coahuila",
    "COL": "Colima",
    "CDMX": "Ciudad de México",
    "DGO": "Durango",
    "GTO": "Guanajuato",
    "GRO": "Guerrero",
    "HGO": "Hidalgo",
    "JAL": "Jalisco",
    "MÉX": "Estado de México",
    "MEX": "Estado de México",
    "MICH": "Michoacán",
    "MOR": "Morelos",
    "NAY": "Nayarit",
    "NL": "Nuevo León",
    "OAX": "Oaxaca",
    "PUE": "Puebla",
    "QRO": "Querétaro",
    "QR": "Quintana Roo",
    "SLP": "San Luis Potosí",
    "SIN": "Sinaloa",
    "SON": "Sonora",
    "TAB": "Tabasco",
    "TAM": "Tamaulipas",
    "TLAX": "Tlaxcala",
    "VER": "Veracruz",
    "YUC": "Yucatán",
    "ZAC": "Zacatecas",
}

# Parseo de cabeceras de mes: "Nov_25" → date(2025,11,1)
MES_MAP = {
    "Ene": 1, "Feb": 2, "Mar": 3, "Abr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Ago": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dic": 12,
}


def parse_month_col(col: str) -> dt.date | None:
    """'Nov_25' → date(2025,11,1); ignora columnas que no coincidan."""
    parts = col.split("_")
    if len(parts) != 2:
        return None
    mes_str, yr_str = parts
    mes = MES_MAP.get(mes_str.capitalize())
    if mes is None or not yr_str.isdigit():
        return None
    year = 2000 + int(yr_str)
    return dt.date(year, mes, 1)


@dataclass
class EncuestaRow:
    fuente: str
    fecha_publicacion: dt.date
    ambito: str
    entidad: str
    actor_tipo: str
    actor_nombre: str
    actor_partido: str | None
    metrica: str
    valor_pct: float
    url_fuente: str


def load_excel(path: Path) -> list[EncuestaRow]:
    try:
        import openpyxl  # noqa: WPS433
    except ImportError:
        log.error("openpyxl no instalado — pip install openpyxl")
        sys.exit(1)

    wb = openpyxl.load_workbook(path)
    ws = wb.active

    rows_out: list[EncuestaRow] = []
    headers: list[str] = []
    month_cols: list[tuple[int, dt.date]] = []  # (col_index, date)

    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            # Cabecera
            headers = [str(c) if c is not None else "" for c in row]
            for col_idx, col_name in enumerate(headers):
                fecha = parse_month_col(col_name)
                if fecha:
                    month_cols.append((col_idx, fecha))
            log.info("Meses encontrados: %s", [str(d) for _, d in month_cols])
            continue

        if not row or row[0] is None:
            continue

        # Columnas fijas: Lugar(0), Estado(1), Gobernador(2)
        abrev = str(row[1]).strip() if row[1] else ""
        gobernador = str(row[2]).strip() if row[2] else ""
        entidad = ESTADO_MAP.get(abrev, abrev)

        if not gobernador or not entidad:
            continue

        for col_idx, fecha in month_cols:
            valor = row[col_idx]
            if valor is None:
                continue
            try:
                valor_pct = float(valor)
            except (ValueError, TypeError):
                continue

            rows_out.append(EncuestaRow(
                fuente=FUENTE,
                fecha_publicacion=fecha,
                ambito="estatal",
                entidad=entidad,
                actor_tipo="gobernador",
                actor_nombre=gobernador,
                actor_partido=None,
                metrica="aprobacion",
                valor_pct=valor_pct,
                url_fuente=str(path),
            ))

    log.info("Rows parseadas: %d (%d gobernadores × %d meses)",
             len(rows_out), len(rows_out) // max(len(month_cols), 1), len(month_cols))
    return rows_out


def ingest_rows(rows: list[EncuestaRow], dry_run: bool = False) -> dict:
    if dry_run:
        for r in rows[:10]:
            log.info("DRY  %s | %s | %s | %s%%", r.entidad, r.actor_nombre, r.fecha_publicacion, r.valor_pct)
        if len(rows) > 10:
            log.info("... +%d rows", len(rows) - 10)
        return {"inserted": 0, "skipped": 0, "dry_run": len(rows)}

    import psycopg2  # noqa: WPS433
    from app.core.config import settings  # noqa: WPS433

    conn = psycopg2.connect(settings.DATABASE_URL_SYNC.replace("postgresql+psycopg2://", "postgresql://"))
    conn.autocommit = False
    cur = conn.cursor()

    inserted = skipped = 0
    for r in rows:
        cur.execute(
            """
            SELECT id FROM encuestas_publicas
            WHERE fuente = %s
              AND fecha_publicacion = %s
              AND COALESCE(entidad, '') = COALESCE(%s, '')
              AND actor_nombre = %s
              AND metrica = %s
            """,
            (r.fuente, r.fecha_publicacion, r.entidad, r.actor_nombre, r.metrica),
        )
        if cur.fetchone():
            skipped += 1
            continue
        cur.execute(
            """
            INSERT INTO encuestas_publicas
                (fuente, fecha_publicacion, ambito, entidad, actor_tipo,
                 actor_nombre, actor_partido, metrica, valor_pct, url_fuente, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
            """,
            (r.fuente, r.fecha_publicacion, r.ambito, r.entidad, r.actor_tipo,
             r.actor_nombre, r.actor_partido, r.metrica, r.valor_pct, r.url_fuente),
        )
        inserted += 1

    conn.commit()
    cur.close()
    conn.close()
    return {"inserted": inserted, "skipped": skipped, "dry_run": 0}


def main() -> int:
    parser = argparse.ArgumentParser(description="Importador Mitofsky — aprobación de gobernadores.")
    parser.add_argument("--file", default="/uploads/Aprobacion_Gobernadores_Historico.xlsx",
                        help="Ruta al Excel (default: /uploads/...)")
    parser.add_argument("--dry-run", action="store_true", help="No inserta a BD.")
    args = parser.parse_args()

    path = Path(args.file)
    if not path.exists():
        log.error("Archivo no encontrado: %s", path)
        return 1

    rows = load_excel(path)
    if not rows:
        log.warning("Sin rows — verifica el formato del Excel")
        return 1

    result = ingest_rows(rows, dry_run=args.dry_run)
    log.info("INGEST: %s", result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
