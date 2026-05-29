"""Scraper Demoscopía Digital — aprobación gubernamental Federal/CDMX/Oaxaca.

https://demoscopiadigital.com publica mensualmente aprobación presidencial y
gubernamental (por estado). La data NO vive en PDFs ni en dashboards Flourish
públicos como suponía el research inicial — está embebida en el HTML como
Angular Universal transfer-state JSON.

Patrón descubierto 2026-04-14:
- URL con año/mes: `/aprobacionEstado/{slug}/{YYYY}/{M}` para gobernadores.
- URL presidencial: `/presidencial/{YYYY}/{M}` para presidente.
- Respuesta: HTML 200KB con `<script id="ng-state" type="application/json">...</script>`
  embebido. Las claves numéricas dentro del JSON son hashes de Angular, pero
  tienen un `b` con campos `presidenteEstado` / `presidente` / `gobernador`
  que contienen el objeto con `aprueba` / `desaprueba` / `periodo` / `partido`
  / `servidor_publico` / `estado`.

Uso:
    python -m app.scrapers.encuestas_demoscopia           # scrape default
    python -m app.scrapers.encuestas_demoscopia --dry-run # imprime sin insertar
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import re
import sys
import time
from dataclasses import dataclass
from typing import Iterator

import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("encuestas_demoscopia")

BASE = "https://demoscopiadigital.com"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Safari/605.1.15"
)
NG_STATE_RE = re.compile(
    r'<script[^>]*id="ng-state"[^>]*>([^<]+)</script>',
    re.DOTALL,
)

FUENTE = "Demoscopía Digital"

# ============================================================================
# ⚠️ BUG ESTRUCTURAL DETECTADO 2026-05-08 (Linda · auditoría E.5)
# ============================================================================
# Demoscopía Digital cambió arquitectura del sitio:
#
# - Federal `/presidencial`: SIGUE FUNCIONANDO pero ng-state ya solo expone el
#   mes actual (NO histórico mensual completo como antes). Captura 2 datapoints
#   por scrape (aprobacion + desaprobacion). Re-correr mensual para acumular.
#
# - Gubernatura `/aprobacion/gobernadores/<slug>`: **ROTO**. Páginas individuales
#   son shells sin datos personales. Los datos están ahora en una tabla central
#   (`estados_rumbo_al` 2027) cuyos histories viven dentro de flourish.studio
#   embeds (`flourish_partidos`, `flourish_historico` URLs). Requiere
#   re-engineering completo: flourish.studio embed scraper + parsing JSON
#   embebido en SVG/Canvas.
#
# Estado actual del corpus encuestas_publicas Demoscopía: 13 rows
#   - 9 CDMX Brugada legacy (capturados antes del cambio, oct 2024 → mar 2025)
#   - 2 federal CSP abril 2026
#   - 2 federal CSP marzo 2026 (recuperados en auditoría 2026-05-08)
#   - 0 Oaxaca (Jara) — nunca capturados, paginación gubernatura ya estaba rota
#
# Pendiente E.5b (~3-4h): scraper flourish.studio embeds para recuperar
# gubernaturas. Documentado en docs/SCRAPERS-ENCUESTAS.md §7.
# ============================================================================

# Mapeo scope CRECE → URL pattern Demoscopía.
# ``actor_key`` es la llave dentro del body ng-state donde vive la métrica.
# ``actor_info_key`` es la llave donde está el nombre/partido del actor.
# Federal: actor_info_key="presidente"; Estado: actor_info_key="gobernador".
# Todos tienen historicoAprobacion en su ng-state — no se necesita scrape mensual.
TARGETS = [
    {
        "ambito": "federal", "entidad": None,
        "path": "/presidencial",
        "actor_key": "aprobacion", "actor_tipo": "presidente",
        "actor_info_key": "presidente",
    },
    {
        "ambito": "estatal", "entidad": "Ciudad de México",
        "path": "/aprobacion/gobernadores/clara-brugada",
        "actor_key": "gobernador", "actor_tipo": "gobernador",
        "actor_info_key": "gobernador",
    },
    {
        "ambito": "estatal", "entidad": "Oaxaca",
        "path": "/aprobacion/gobernadores/salomon-jara",
        "actor_key": "gobernador", "actor_tipo": "gobernador",
        "actor_info_key": "gobernador",
    },
]


@dataclass
class EncuestaRow:
    fuente: str
    fecha_publicacion: dt.date
    ambito: str
    entidad: str | None
    actor_tipo: str
    actor_nombre: str
    actor_partido: str | None
    metrica: str
    valor_pct: float
    url_fuente: str


def fetch_page(url: str, timeout: int = 30) -> str:
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def extract_ng_state(html: str) -> dict:
    m = NG_STATE_RE.search(html)
    if not m:
        raise RuntimeError("No se encontró bloque ng-state en el HTML.")
    # Angular escapa '<' y '>' dentro del JSON como \u003c y \u003e;
    # json.loads los resuelve nativamente.
    return json.loads(m.group(1))


def find_state_payload(state: dict, actor_key: str) -> dict | None:
    """Busca el primer dict que contenga el actor_key esperado dentro del transfer-state.

    Claves numéricas son hashes Angular HTTP state; iteramos hasta encontrar
    uno cuyo ``.b`` (body) traiga el payload de interés.
    """
    for key, value in state.items():
        if not isinstance(value, dict):
            continue
        body = value.get("b")
        if isinstance(body, dict) and actor_key in body:
            return body
    return None


def periodo_to_date(periodo: dict) -> dt.date:
    anio = int(periodo["anio"])
    mes = int(periodo["mes"])
    return dt.date(anio, mes, 1)


def extract_rows(target: dict, state: dict, url: str) -> list[EncuestaRow]:
    body = find_state_payload(state, target["actor_key"])
    if body is None:
        log.warning("  sin payload para %s (%s)", target["actor_key"], url)
        return []

    # Algunos entries (gobernador) no traen periodo propio — se hereda del body.
    body_periodo = body.get("periodo")
    # En /presidencial el servidor_publico del entry 'aprobacion' suele venir None;
    # el nombre del presidente está en body.presidente.
    body_presidente = body.get("presidente") or {}

    rows: list[EncuestaRow] = []
    raw_actor = body[target["actor_key"]]

    # gobernador a veces viene como lista (múltiples períodos/estados), a veces dict.
    candidates = raw_actor if isinstance(raw_actor, list) else [raw_actor]

    for entry in candidates:
        if not isinstance(entry, dict):
            continue
        periodo = entry.get("periodo") or body_periodo
        servidor = entry.get("servidor_publico") or {}
        partido = entry.get("partido") or {}
        estado = entry.get("estado") or {}
        # Fallback al body.presidente cuando el entry trae servidor_publico
        # parcial (sólo id, sin nombre) como pasa en /presidencial.
        actor_nombre_val = servidor.get("nombre") or body_presidente.get("nombre")

        if not periodo or not actor_nombre_val:
            continue

        # Si el body vino desde `/aprobacionEstado/{slug}/...` validamos que el
        # nombre del estado coincida con el target (hay rankings con muchas entries).
        if target["entidad"] and estado.get("estado") and target["entidad"].lower() not in estado["estado"].lower():
            # No es el estado objetivo — skip.
            continue

        fecha = periodo_to_date(periodo)
        actor_nombre = actor_nombre_val
        actor_partido = partido.get("nombre") or None

        for metrica_key, metrica_nombre in (("aprueba", "aprobacion"), ("desaprueba", "desaprobacion")):
            valor = entry.get(metrica_key)
            if valor is None:
                continue
            rows.append(
                EncuestaRow(
                    fuente=FUENTE,
                    fecha_publicacion=fecha,
                    ambito=target["ambito"],
                    entidad=target["entidad"],
                    actor_tipo=target.get("actor_tipo", target["actor_key"]),
                    actor_nombre=actor_nombre,
                    actor_partido=actor_partido,
                    metrica=metrica_nombre,
                    valor_pct=float(valor),
                    url_fuente=url,
                )
            )
    return rows


def extract_historico_rows(target: dict, state: dict, url: str) -> list[EncuestaRow]:
    """Extrae historicoAprobacion del ng-state.

    Disponible en /presidencial y en /aprobacion/gobernadores/{slug}.
    El nombre del actor viene de body[actor_info_key].nombre.
    """
    rows: list[EncuestaRow] = []
    actor_info_key = target.get("actor_info_key", "presidente")
    for v in state.values():
        if not isinstance(v, dict):
            continue
        body = v.get("b")
        if not isinstance(body, dict):
            continue
        hist = body.get("historicoAprobacion")
        if not hist or not isinstance(hist, list):
            continue
        # Nombre del actor desde body.<actor_info_key>
        actor_info = body.get(actor_info_key) or {}
        actor_nombre = actor_info.get("nombre")
        actor_partido = (actor_info.get("partido") or {}).get("nombre")
        if not actor_nombre:
            continue
        log.info("  historicoAprobacion: %d puntos para %s", len(hist), actor_nombre)
        for punto in hist:
            periodo = punto.get("periodo")
            if not periodo:
                continue
            fecha = periodo_to_date(periodo)
            for metrica_key, metrica_nombre in (("aprueba", "aprobacion"), ("desaprueba", "desaprobacion")):
                valor = punto.get(metrica_key)
                if valor is None or valor == 0:
                    continue
                rows.append(EncuestaRow(
                    fuente=FUENTE,
                    fecha_publicacion=fecha,
                    ambito=target["ambito"],
                    entidad=target["entidad"],
                    actor_tipo=target["actor_tipo"],
                    actor_nombre=actor_nombre,
                    actor_partido=actor_partido,
                    metrica=metrica_nombre,
                    valor_pct=float(valor),
                    url_fuente=url,
                ))
        return rows  # primer body con hist es suficiente
    return rows


def scrape_target(target: dict, year: int, month: int) -> list[EncuestaRow]:
    url = f"{BASE}{target['path']}/{year}/{month}"
    log.info("GET %s", url)
    html = fetch_page(url)
    state = extract_ng_state(html)
    rows = extract_rows(target, state, url)
    log.info("  rows extraídas: %d", len(rows))
    return rows


def iter_months(back_months: int, start: dt.date | None = None) -> Iterator[tuple[int, int]]:
    today = start or dt.date.today()
    for i in range(back_months):
        y = today.year
        m = today.month - i
        while m <= 0:
            m += 12
            y -= 1
        yield (y, m)


# ──────────────────────────────────────────────────────────────────
# Ingest
# ──────────────────────────────────────────────────────────────────


def ingest_rows(rows: list[EncuestaRow], dry_run: bool = False) -> dict:
    """Upsert-like via SELECT existencia + INSERT — no hay UNIQUE constraint."""
    if dry_run:
        for r in rows[:20]:
            log.info("DRY  %s", r)
        if len(rows) > 20:
            log.info("... +%d rows", len(rows) - 20)
        return {"inserted": 0, "skipped": 0, "dry_run": len(rows)}

    import psycopg2  # noqa: WPS433

    from app.core.config import settings  # noqa: WPS433

    conn = psycopg2.connect(settings.DATABASE_URL_SYNC.replace("postgresql+psycopg2://", "postgresql://"))
    conn.autocommit = False
    cur = conn.cursor()

    inserted = 0
    skipped = 0
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
                 actor_nombre, actor_partido, metrica, valor_pct, url_fuente,
                 created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
            """,
            (
                r.fuente,
                r.fecha_publicacion,
                r.ambito,
                r.entidad,
                r.actor_tipo,
                r.actor_nombre,
                r.actor_partido,
                r.metrica,
                r.valor_pct,
                r.url_fuente,
            ),
        )
        inserted += 1
    conn.commit()
    cur.close()
    conn.close()
    return {"inserted": inserted, "skipped": skipped, "dry_run": 0}


# ──────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="Scraper Demoscopía Digital (Federal + CDMX + Oaxaca).")
    parser.add_argument("--months", type=int, default=6, help="Cuántos meses hacia atrás (default: 6).")
    parser.add_argument("--dry-run", action="store_true", help="No inserta a BD, solo imprime.")
    parser.add_argument("--sleep", type=float, default=1.0, help="Segundos entre requests (politeness).")
    args = parser.parse_args()

    all_rows: list[EncuestaRow] = []

    today = dt.date.today()

    # Todos los targets tienen historicoAprobacion en su ng-state.
    # Federal: la URL base ya lo incluye.
    # Estatales: requieren /{year}/{month} para activar el SSR del historico.
    for target in TARGETS:
        if target["ambito"] == "federal":
            url = f"{BASE}{target['path']}"
        else:
            url = f"{BASE}{target['path']}/{today.year}/{today.month}"
        try:
            log.info("GET %s (historico completo)", url)
            html = fetch_page(url)
            state = extract_ng_state(html)
            hist_rows = extract_historico_rows(target, state, url)
            if hist_rows:
                log.info("  %s histórico: %d rows", target["entidad"] or "Federal", len(hist_rows))
                all_rows.extend(hist_rows)
                time.sleep(args.sleep)
                continue
            log.warning("  historicoAprobacion vacío para %s — fallback a scrape mensual", url)
        except Exception as exc:
            log.exception("Error historico %s: %s", target["path"], exc)

        # Fallback mensual (no debería necesitarse con los paths correctos)
        for year, month in iter_months(args.months):
            try:
                all_rows.extend(scrape_target(target, year, month))
            except Exception as exc:
                log.warning("Error mensual %s %d-%d: %s", target["path"], year, month, exc)
            time.sleep(args.sleep)

    log.info("TOTAL rows extraídas: %d", len(all_rows))
    result = ingest_rows(all_rows, dry_run=args.dry_run)
    log.info("INGEST: %s", result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
