"""Scraper Oraculus (oraculus.mx) — encuestas poll-of-polls + individuales.

Oraculus publica JSON inline en el HTML de /aprobacion-presidencial/.
Contiene:
- estimates.aprueba.{CSP,AMLO,EPN,...}: serie temporal del poll-of-polls bayesiano
- polls.Aprueba.{CSP,...}: encuestas individuales con pollster + fecha + valor

Este scraper:
1. Descarga HTML
2. Extrae JSON inline con regex
3. Mapea cada punto a row de `encuestas_publicas`
4. Inserta idempotente (skip si (fuente, fecha, actor, metrica) existe)

No requiere auth. Validado 2026-04-13 por peer md-research.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Iterable

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

URL_APROBACION = "https://oraculus.mx/aprobacion-presidencial/"
USER_AGENT = "Mozilla/5.0 (compatible; CRECE-v2-scraper/1.0)"

# Map Oraculus keys → nombre actor canónico
PRESIDENT_MAP = {
    "CSP": ("Claudia Sheinbaum Pardo", "MORENA"),
    "AMLO": ("Andrés Manuel López Obrador", "MORENA"),
    "EPN": ("Enrique Peña Nieto", "PRI"),
    "FCH": ("Felipe Calderón Hinojosa", "PAN"),
    "VFQ": ("Vicente Fox Quesada", "PAN"),
    "EZPL": ("Ernesto Zedillo Ponce de León", "PRI"),
}


@dataclass
class EncuestaRow:
    fuente: str
    fecha_publicacion: date
    ambito: str  # federal, estatal, municipal
    entidad: str | None
    actor_tipo: str  # presidente, gobernador, alcalde, candidato
    actor_nombre: str
    actor_partido: str | None
    metrica: str  # aprueba, desaprueba, intencion_voto
    valor_pct: float
    valor_delta_vs_anterior: float | None
    tamano_muestra: int | None
    margen_error: float | None
    url_fuente: str


def fetch_html(url: str = URL_APROBACION) -> str:
    resp = httpx.get(url, headers={"User-Agent": USER_AGENT}, timeout=20.0)
    resp.raise_for_status()
    return resp.text


def parse_inline_json(html: str) -> dict:
    match = re.search(r"var\s+data\s*=\s*(\{.*?\});\s*</script>", html, re.DOTALL)
    if not match:
        raise ValueError("No se encontró 'var data = {...}' inline en HTML")
    return json.loads(match.group(1))


def _ts_to_date(ts_ms: int) -> date:
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).date()


def rows_from_poll_of_polls(data: dict, active_only: bool = True) -> Iterable[EncuestaRow]:
    """Genera rows del poll-of-polls (estimates) para cada presidente."""
    estimates = data.get("estimates", {})
    for metrica_key in ("aprueba", "desaprueba"):
        series = estimates.get(metrica_key, {})
        for pres_key, puntos in series.items():
            if pres_key not in PRESIDENT_MAP:
                continue
            nombre, partido = PRESIDENT_MAP[pres_key]
            # Si active_only, solo CSP (presidente en funciones)
            if active_only and pres_key != "CSP":
                continue
            for punto in puntos:
                ts_ms, mid, lo95, hi95, *_ = punto
                margen = (hi95 - lo95) / 2 if hi95 and lo95 else None
                yield EncuestaRow(
                    fuente="Oraculus poll-of-polls",
                    fecha_publicacion=_ts_to_date(ts_ms),
                    ambito="federal",
                    entidad="México",
                    actor_tipo="presidente",
                    actor_nombre=nombre,
                    actor_partido=partido,
                    metrica=metrica_key,
                    valor_pct=float(mid),
                    valor_delta_vs_anterior=None,
                    tamano_muestra=None,
                    margen_error=margen,
                    url_fuente=URL_APROBACION,
                )


def rows_from_individual_polls(data: dict, active_only: bool = True) -> Iterable[EncuestaRow]:
    """Genera rows de encuestas individuales agregadas por Oraculus."""
    polls = data.get("polls", {})
    metrica_map = {"Aprueba": "aprueba", "Desaprueba": "desaprueba"}
    for metrica_label, series in polls.items():
        metrica = metrica_map.get(metrica_label, metrica_label.lower())
        for pres_key, individual in series.items():
            if pres_key not in PRESIDENT_MAP:
                continue
            if active_only and pres_key != "CSP":
                continue
            nombre, partido = PRESIDENT_MAP[pres_key]
            for item in individual:
                if len(item) < 3:
                    continue
                pollster, ts_ms, valor = item[0], item[1], item[2]
                yield EncuestaRow(
                    fuente=str(pollster),
                    fecha_publicacion=_ts_to_date(ts_ms),
                    ambito="federal",
                    entidad="México",
                    actor_tipo="presidente",
                    actor_nombre=nombre,
                    actor_partido=partido,
                    metrica=metrica,
                    valor_pct=float(valor),
                    valor_delta_vs_anterior=None,
                    tamano_muestra=None,
                    margen_error=None,
                    url_fuente=URL_APROBACION,
                )


async def ingest_rows(db: AsyncSession, rows: Iterable[EncuestaRow]) -> tuple[int, int]:
    """Inserta idempotente. Dedup por (fuente, fecha_publicacion, actor_nombre, metrica)."""
    inserted = skipped = 0
    for r in rows:
        existing = (await db.execute(
            text("""
                SELECT 1 FROM encuestas_publicas
                WHERE fuente = :fuente
                  AND fecha_publicacion = :fecha
                  AND actor_nombre = :actor
                  AND metrica = :metrica
                LIMIT 1
            """),
            {"fuente": r.fuente, "fecha": r.fecha_publicacion,
             "actor": r.actor_nombre, "metrica": r.metrica},
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
                    :metrica, :valor, :delta,
                    :muestra, :error, :url, NOW()
                )
            """),
            {
                "fuente": r.fuente, "fecha": r.fecha_publicacion,
                "ambito": r.ambito, "entidad": r.entidad,
                "actor_tipo": r.actor_tipo, "actor": r.actor_nombre, "partido": r.actor_partido,
                "metrica": r.metrica, "valor": r.valor_pct, "delta": r.valor_delta_vs_anterior,
                "muestra": r.tamano_muestra, "error": r.margen_error, "url": r.url_fuente,
            },
        )
        inserted += 1
    await db.commit()
    return inserted, skipped


async def scrape_oraculus(db: AsyncSession, active_only: bool = True) -> dict:
    html = fetch_html()
    data = parse_inline_json(html)
    all_rows = list(rows_from_poll_of_polls(data, active_only)) + \
               list(rows_from_individual_polls(data, active_only))
    inserted, skipped = await ingest_rows(db, all_rows)
    return {
        "source": "oraculus",
        "url": URL_APROBACION,
        "rows_parsed": len(all_rows),
        "rows_inserted": inserted,
        "rows_skipped_duplicate": skipped,
        "update_time": data.get("update"),
    }
