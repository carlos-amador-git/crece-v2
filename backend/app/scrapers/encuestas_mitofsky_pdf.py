"""Mitofsky PDF parser — extrae aprobación de gobernadores de PDFs publicados en Wix.

Cada post Mitofsky de "Ranking Gobernadores" tiene un botón "DESCARGAR RANKING"
que linkea a Google Drive con un PDF estructurado de ~37 páginas. El PDF contiene
texto seleccionable (NO scanned) — pdfplumber extrae todo determinísticamente.

Páginas relevantes:
- p4 — `PROMEDIO NACIONAL DE APROBACIÓN DE GOBERNADORES` con tabla 12 meses × 6 años
- p5 — Ranking actual con 32 gobernadores (LUGAR_NOV LUGAR_DIC ESTADO NOMBRE %_NOV %_DIC)

Output rows shape `encuestas_publicas`.
"""
from __future__ import annotations

import io
import logging
import re
import unicodedata
from dataclasses import dataclass
from datetime import date

import httpx
import pdfplumber

log = logging.getLogger("encuestas_mitofsky_pdf")

FUENTE = "Mitofsky"

# Map abreviatura INE → nombre completo
ESTADO_MAP: dict[str, str] = {
    "AGS": "Aguascalientes", "BC": "Baja California", "BCS": "Baja California Sur",
    "CAMP": "Campeche", "CHIS": "Chiapas", "CHIH": "Chihuahua",
    "COAH": "Coahuila", "COL": "Colima", "CDMX": "Ciudad de México",
    "DGO": "Durango", "GTO": "Guanajuato", "GRO": "Guerrero",
    "HGO": "Hidalgo", "JAL": "Jalisco", "MÉX": "Estado de México",
    "MEX": "Estado de México", "MICH": "Michoacán", "MOR": "Morelos",
    "NAY": "Nayarit", "NL": "Nuevo León", "OAX": "Oaxaca",
    "PUE": "Puebla", "QRO": "Querétaro", "QR": "Quintana Roo",
    "QROO": "Quintana Roo", "SLP": "San Luis Potosí", "SIN": "Sinaloa",
    "SON": "Sonora", "TAB": "Tabasco", "TAM": "Tamaulipas",
    "TLAX": "Tlaxcala", "VER": "Veracruz", "YUC": "Yucatán", "ZAC": "Zacatecas",
}

# Abreviatura mes ES → número
MES_NUM = {
    "ene": 1, "enero": 1, "feb": 2, "febrero": 2,
    "mar": 3, "marzo": 3, "abr": 4, "abril": 4,
    "may": 5, "mayo": 5, "jun": 6, "junio": 6,
    "jul": 7, "julio": 7, "ago": 8, "agosto": 8,
    "sep": 9, "septiembre": 9, "oct": 10, "octubre": 10,
    "nov": 11, "noviembre": 11, "dic": 12, "diciembre": 12,
}


@dataclass(frozen=True)
class EncuestaRow:
    fuente: str
    fecha_publicacion: date
    ambito: str
    entidad: str | None
    actor_tipo: str
    actor_nombre: str
    actor_partido: str | None
    metrica: str
    valor_pct: float
    url_fuente: str


def _normalize(s: str) -> str:
    """Normaliza string: minúsculas, sin acentos, sin espacios extra."""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", s.strip().lower())


def download_gdrive_pdf(file_id: str, http: httpx.Client | None = None) -> bytes:
    """Descarga PDF de Google Drive vía URL pública uc?export=download."""
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    client = http or httpx.Client(follow_redirects=True, timeout=60.0)
    try:
        r = client.get(url)
        r.raise_for_status()
        if not r.content.startswith(b"%PDF"):
            raise ValueError(f"Respuesta no es PDF (primeros bytes: {r.content[:20]!r})")
        return r.content
    finally:
        if not http:
            client.close()


# Page 4: serie histórica nacional ----------------------------------------------

_RE_HEADER_YEARS = re.compile(r"(\b20\d{2}\b)")
# Token: número como 34.2, 47.6, +0.8, -2.4, 0.0
_RE_NUMERIC = re.compile(r"^[+\-]?\d{1,3}\.\d$")
_MESES_NAMES = (
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
)


def parse_page4_serie_nacional(text: str, url_fuente: str) -> list[EncuestaRow]:
    """Page 4: 'PROMEDIO NACIONAL DE APROBACIÓN DE GOBERNADORES' tabla 12 meses × N años.

    Layout texto (después de header "Promedio Variación ..."):
        Enero    34.2 47.6 +0.8 51.3 -0.5 49.6 +1.9 52.4 -0.5 48.7 -2.5
        Febrero  31.8 -2.4 47.9 +0.3 50.0 -1.3 50.5 +0.9 52.5 +0.1 48.4 -0.3
        ...

    Particularidad: Enero del primer año reportado NO tiene variación (es el ancla
    inicial), por eso esa fila tiene 1 token menos. Resto de meses + años tienen
    par (Promedio, Variación).

    Algoritmo robusto: para cada línea que empieza con nombre de mes:
    - tokenize numéricos
    - si len == 1 + 2*(years-1): caso Enero año-base
    - si len == 2*years - 1: caso Enero año-base (sin variación primer mes)
    - si len == 2*years: caso normal (todos con var)
    """
    rows: list[EncuestaRow] = []
    if "PROMEDIO NACIONAL DE APROBACIÓN DE GOBERNADORES" not in text:
        return rows

    # Identificar años en cabecera
    header = re.search(r"PROMEDIO NACIONAL DE APROBACIÓN DE GOBERNADORES\s*\n([^\n]+)", text)
    if not header:
        return rows
    years = sorted({int(m.group(1)) for m in _RE_HEADER_YEARS.finditer(header.group(1))})
    if not years:
        return rows
    n_years = len(years)

    for line in text.splitlines():
        parts = line.strip().split()
        if not parts or parts[0] not in _MESES_NAMES:
            continue
        mes_name = parts[0]
        mes_num = MES_NUM[_normalize(mes_name)]
        toks = [t for t in parts[1:] if _RE_NUMERIC.match(t)]
        if not toks:
            continue

        # Build (year → valor) map según len(toks):
        values_per_year: dict[int, float] = {}
        if len(toks) == 2 * n_years - 1:
            # Primer año solo Promedio (sin var). Resto con par (P, V).
            try:
                values_per_year[years[0]] = float(toks[0])
                for i in range(1, n_years):
                    values_per_year[years[i]] = float(toks[1 + 2 * (i - 1)])
            except (ValueError, IndexError):
                continue
        elif len(toks) == 2 * n_years:
            # Todos los años con (Promedio, Variación). Tomar token par (idx 0,2,4...).
            try:
                for i in range(n_years):
                    values_per_year[years[i]] = float(toks[2 * i])
            except (ValueError, IndexError):
                continue
        elif len(toks) == n_years:
            # Solo promedios sin variaciones (caso degenerado). Tomar todo.
            try:
                for i in range(n_years):
                    values_per_year[years[i]] = float(toks[i])
            except (ValueError, IndexError):
                continue
        else:
            log.debug("p4 mes=%s len(toks)=%d toks=%s — skip", mes_name, len(toks), toks)
            continue

        for year, val in values_per_year.items():
            rows.append(EncuestaRow(
                fuente=FUENTE,
                fecha_publicacion=date(year, mes_num, 1),
                ambito="federal",
                entidad="México",
                actor_tipo="promedio_gobernadores",
                actor_nombre="Promedio nacional gobernadores",
                actor_partido=None,
                metrica="aprobacion",
                valor_pct=val,
                url_fuente=url_fuente,
            ))
    return rows


# Page 5: ranking actual 32 gobernadores ---------------------------------------

# Layout: "{lugar_prev}{?.} {lugar_actual}{?.} {ESTADO_ABREV} {Nombre} {%_prev} {%_actual}"
# Ej recientes: "1. 1. QR Mara Lezama 57.0 57.4"
# Ej antiguos:  "1 1 QR Mara Lezama 55.2 54.2"
# Letras de scroll vertical "A T L A" se filtran previamente.
_RE_RANKING_LINE = re.compile(
    r"""
    ^                                # inicio línea
    (?:[A-Z]\s+)?                    # opcional letra de scroll vertical (ej "A ")
    \d{1,2}\.?\s+                    # lugar previo (con o sin punto)
    (?P<lugar>\d{1,2})\.?\s+         # lugar actual (con o sin punto)
    (?P<abrev>[A-ZÁÉÍÓÚ]{2,5})\s+    # abrev estado
    (?P<nombre>[A-ZÁÉÍÓÚÑa-záéíóúñ' ]+?)
    \s+(?P<val_prev>\d{1,2}\.\d)\s+  # valor mes previo
    (?P<val>\d{1,2}\.\d)\s*$         # valor mes actual
    """,
    re.VERBOSE | re.MULTILINE,
)


def parse_ranking_page(text: str, fecha_pub: date, url_fuente: str) -> list[EncuestaRow]:
    """Extrae ranking 32 gobernadores de la página que tenga formato LUGAR ESTADO NOMBRE % %."""
    rows: list[EncuestaRow] = []
    seen_entidades: set[str] = set()
    for m in _RE_RANKING_LINE.finditer(text):
        abrev_raw = m.group("abrev").strip()
        entidad = ESTADO_MAP.get(abrev_raw.upper()) or ESTADO_MAP.get(_normalize(abrev_raw).upper())
        if not entidad:
            continue
        if entidad in seen_entidades:
            # Tablas regionales pueden repetir gobernadores — tomar solo primer match
            continue
        seen_entidades.add(entidad)
        nombre = m.group("nombre").strip()
        # Limpia partículas tipo "Marina del Pilar" partidas en multilínea — el nombre
        # quedaría con espacio extra; aquí no podemos reparar fragmentación post-line.
        try:
            val = float(m.group("val"))
        except ValueError:
            continue
        rows.append(EncuestaRow(
            fuente=FUENTE,
            fecha_publicacion=fecha_pub,
            ambito="estatal",
            entidad=entidad,
            actor_tipo="gobernador",
            actor_nombre=nombre,
            actor_partido=None,
            metrica="aprobacion",
            valor_pct=val,
            url_fuente=url_fuente,
        ))
    return rows


# Period detection ------------------------------------------------------------

_RE_DICIEMBRE = re.compile(r"\b(Enero|Febrero|Marzo|Abril|Mayo|Junio|Julio|Agosto|Septiembre|Octubre|Noviembre|Diciembre)\s+(20\d{2})\b", re.I)


def detect_pdf_period(text_p1: str, fallback_post_date: str | None = None) -> date | None:
    """Detecta mes+año del PDF a partir de la portada (page 1).

    Ejemplo: 'GOBERNADORES Y GOBERNADORAS DE MÉXICO\nAPROBACIÓN CIUDADANA\nDICIEMBRE 2025'

    Boletines pre-2023 a veces vienen sin año en portada ('DICIEMBRE BOLETIN 51').
    En ese caso usar `fallback_post_date` (ISO 'YYYY-MM-DD...' del catalog) para
    completar el año, asumiendo que el post se publicó dentro del mes/año del PDF.
    """
    m = _RE_DICIEMBRE.search(text_p1)
    if m:
        mes = MES_NUM.get(_normalize(m.group(1)))
        year = int(m.group(2))
        if mes:
            return date(year, mes, 1)

    # Fallback: detectar solo MES sin año, usar año del post_date del catalog
    if fallback_post_date:
        m_mes = re.search(
            r"\b(Enero|Febrero|Marzo|Abril|Mayo|Junio|Julio|Agosto|Septiembre|Octubre|Noviembre|Diciembre)\b",
            text_p1, re.I,
        )
        if m_mes:
            mes = MES_NUM.get(_normalize(m_mes.group(1)))
            try:
                # post_date es 'YYYY-MM-DD...' ISO
                year = int(fallback_post_date[:4])
                if mes:
                    return date(year, mes, 1)
            except (ValueError, IndexError):
                pass
    return None


# Top-level parser ------------------------------------------------------------

def _find_page_with(pages_text: list[str], substring: str) -> int | None:
    """Devuelve el índice (0-based) de la primera página que contiene el substring."""
    for i, t in enumerate(pages_text):
        if substring in (t or ""):
            return i
    return None


# ============================================================================
# ALCALDES — historico nacional 150 alcaldes
# ============================================================================
# Layout p3 alcaldes: "Feb26 46.5 / Dic 25 47.7 / Oct 25 50.7 ..."
# Mes con/sin espacio + valor flotante
_RE_ALCALDES_HIST = re.compile(
    r"\b(?P<mes>Ene|Feb|Mar|Abr|May|Jun|Jul|Ago|Sep|Oct|Nov|Dic)\s*(?P<yy>\d{2})\s+(?P<val>\d{1,2}\.\d)\b"
)


# ============================================================================
# ALCALDES — ranking individual 150 alcaldes (E.3 implementación 2026-05-08)
# ============================================================================
# Layout p4-p13 de PDFs alcaldes (hojas 1-10):
#   [Letra categoría vertical 1-char/línea opcional]  ej "S/o/b/r/e/s/a/l/i/e/n/t/e"
#   {Nombre Apellido(s)}
#   {posición} {valor}
#   {Municipio}, {Estado}.
#
# Estrategia: state machine de 3 fases. Acumula líneas, identifica nombre
# (alfabético sin números), busca línea "N V.V" con posición + valor, luego
# captura "Municipio, Estado.".


def parse_pdf_alcaldes_ranking(pages_text: list[str], fecha_pub: date, url_fuente: str) -> list[EncuestaRow]:
    """Parser ranking individual 150 alcaldes (pages 4-13 con hojas 1-10)."""
    rows: list[EncuestaRow] = []
    seen_alcaldes: set[str] = set()

    # State machine
    pos_val_re = re.compile(r"^(\d{1,3})\s+(\d{1,2}\.\d)\s*$")
    municipio_re = re.compile(r"^([A-ZÁÉÍÓÚ][a-zA-ZáéíóúñÑ\.\s]+),\s*([A-ZÁÉÍÓÚa-z]+)\.?\s*$")
    nombre_re = re.compile(r"^[A-ZÁÉÍÓÚÑ][a-zA-ZÁÉÍÓÚáéíóúñÑ\.\-' ]{2,40}$")

    for page_text in pages_text:
        if "150 alcaldes" not in page_text and "150 ALCALDES" not in page_text \
           and "Posición Municipio" not in page_text and "% de aprobación" not in page_text:
            continue
        if "Capítulo 1:" not in page_text:
            continue

        lines = [l.strip() for l in page_text.split("\n") if l.strip()]
        # Buscar tripletes (nombre, pos+val, municipio)
        i = 0
        while i < len(lines) - 2:
            line = lines[i]
            # Skip headers / 1-char vertical category labels
            if len(line) <= 2 or line.startswith("Capítulo") or "RankingMITOFSKY" in line \
               or "DE 10)" in line or "Posición" in line or "Alcaldes de México" in line \
               or line.endswith("2026") or line.endswith("2025") or line.endswith("2024"):
                i += 1
                continue

            # Found possible nombre
            if not nombre_re.match(line):
                i += 1
                continue
            nombre = line

            # Look for next line with pos+val (may skip 1-2 lines of vertical labels)
            pv = None
            j = i + 1
            for offset in range(1, 5):
                if i + offset >= len(lines):
                    break
                m = pos_val_re.match(lines[i + offset])
                if m:
                    pv = m
                    j = i + offset
                    break

            if not pv:
                i += 1
                continue

            try:
                val = float(pv.group(2))
            except ValueError:
                i = j + 1
                continue
            if not (10.0 <= val <= 99.0):
                i = j + 1
                continue

            # Look for municipio in next 1-3 lines
            municipio_full = None
            for offset in range(1, 4):
                if j + offset >= len(lines):
                    break
                mun_m = municipio_re.match(lines[j + offset])
                if mun_m:
                    municipio_full = lines[j + offset].rstrip(".").strip()
                    break

            if not municipio_full or nombre in seen_alcaldes:
                i = j + 1
                continue
            seen_alcaldes.add(nombre)

            # Extract entidad from municipio "Municipio, Estado."
            entidad = None
            mun_parts = municipio_full.split(",")
            if len(mun_parts) >= 2:
                ent_abrev = mun_parts[-1].strip().rstrip(".")
                # Map abreviaturas comunes → estado canónico
                abrev_map = {
                    "Mich": "Michoacán", "Qroo": "Quintana Roo", "Son": "Sonora",
                    "Tamps": "Tamaulipas", "Méx": "Estado de México", "Mex": "Estado de México",
                    "Coah": "Coahuila", "Ags": "Aguascalientes", "Chih": "Chihuahua",
                    "Qro": "Querétaro", "CDMX": "Ciudad de México", "Jal": "Jalisco",
                    "Pue": "Puebla", "BC": "Baja California", "BCS": "Baja California Sur",
                    "Yuc": "Yucatán", "Tlax": "Tlaxcala", "SLP": "San Luis Potosí",
                    "NL": "Nuevo León", "Sin": "Sinaloa", "Mor": "Morelos", "Gro": "Guerrero",
                    "Ver": "Veracruz", "Hgo": "Hidalgo", "Chis": "Chiapas",
                    "Camp": "Campeche", "Col": "Colima", "Gto": "Guanajuato",
                    "Nay": "Nayarit", "Oax": "Oaxaca", "Tab": "Tabasco",
                    "Zac": "Zacatecas", "Dgo": "Durango",
                }
                entidad = abrev_map.get(ent_abrev) or ent_abrev

            rows.append(EncuestaRow(
                fuente=FUENTE,
                fecha_publicacion=fecha_pub,
                ambito="municipal",
                entidad=entidad,
                actor_tipo="alcalde",
                actor_nombre=nombre,
                actor_partido=None,
                metrica="aprobacion",
                valor_pct=val,
                url_fuente=url_fuente,
            ))
            i = j + 1
    return rows


def parse_pdf_alcaldes_historico(text: str, url_fuente: str) -> list[EncuestaRow]:
    """Page 3 alcaldes: histórico mensual del promedio nacional de 150 alcaldes."""
    rows: list[EncuestaRow] = []
    if "150 alcaldes" not in text and "150 ALCALDES" not in text:
        return rows
    seen: set[date] = set()
    for m in _RE_ALCALDES_HIST.finditer(text):
        mes_num = MES_NUM.get(_normalize(m.group("mes")))
        if not mes_num:
            continue
        year = 2000 + int(m.group("yy"))
        try:
            val = float(m.group("val"))
        except ValueError:
            continue
        if not (20.0 <= val <= 100.0):
            continue
        d = date(year, mes_num, 1)
        if d in seen:
            continue
        seen.add(d)
        rows.append(EncuestaRow(
            fuente=FUENTE,
            fecha_publicacion=d,
            ambito="federal",
            entidad="México",
            actor_tipo="promedio_alcaldes",
            actor_nombre="Promedio nacional 150 alcaldes",
            actor_partido=None,
            metrica="aprobacion",
            valor_pct=val,
            url_fuente=url_fuente,
        ))
    return rows


# ============================================================================
# PRESIDENTE — historico mensual + ranking 32 estados
# ============================================================================
# Page 2 presidente: serie temporal con valores juntos sin label
# Buscar bloque que tenga 12 valores flotantes seguidos en orden Oct→Sep o similar
_RE_PRES_PERIOD_LABEL = re.compile(
    r"(Oct|Nov|Dic|Ene|Feb|Mar|Abr|May|Jun|Jul|Ago|Sep)\s+(\d{2})", re.I
)


def parse_pdf_presidente_historico(
    text: str, periodo_pdf: date, url_fuente: str, actor_nombre: str
) -> list[EncuestaRow]:
    """Page 2 presidente: serie 12 meses 'Oct 24 Nov 24 ... Sep 25' con valores arriba.

    Layout (simplificado):
        ACUERDO PROM. DESACUERDO PROM.
        69.8 70.2 70.4 70.1 69.2 71.4 71.6
        67.8
        63.4 64.0 64.5
        61.5
        35.9 35.5 34.8
        ...
        Oct 24 Nov 24 Dic 24 Ene 25 Feb 25 Mar 25 Abr 25 May 25 Jun 25 Jul 25 Ago 25 Sep 25

    Estrategia: localizar la línea de meses, contar 12 labels, y luego extraer
    todos los floats del bloque previo en orden, asumiendo que los primeros 12
    son los valores de aprobación (ACUERDO PROM).
    """
    rows: list[EncuestaRow] = []
    # Buscar línea de meses con 12 labels
    months_line = None
    for line in text.splitlines():
        labels = _RE_PRES_PERIOD_LABEL.findall(line)
        if len(labels) == 12:
            months_line = line
            months_labels = labels
            break
    if not months_line:
        return rows

    # Convertir labels a fechas
    months_dates: list[date] = []
    for lbl_mes, lbl_yy in months_labels:
        mn = MES_NUM.get(_normalize(lbl_mes))
        if mn:
            months_dates.append(date(2000 + int(lbl_yy), mn, 1))
    if len(months_dates) != 12:
        return rows

    # Extraer todos los floats del texto previo a la línea meses
    pre_text = text.split(months_line)[0]
    # Tomar todos los XX.X
    floats = [float(x) for x in re.findall(r"\b(\d{2,3}\.\d)\b", pre_text)
              if 30.0 <= float(x) <= 100.0]
    if len(floats) < 12:
        return rows
    # Los primeros 12 floats en orden suelen ser la línea ACUERDO PROM
    aprueba_vals = floats[:12]

    for d, v in zip(months_dates, aprueba_vals):
        rows.append(EncuestaRow(
            fuente=FUENTE,
            fecha_publicacion=d,
            ambito="federal",
            entidad="México",
            actor_tipo="presidente",
            actor_nombre=actor_nombre,
            actor_partido=None,
            metrica="aprobacion",
            valor_pct=v,
            url_fuente=url_fuente,
        ))
    return rows


# Ranking estados aprobación presidencial (page 5 presidente)
# Layout: "Tamaulipas 1 83.4 3.1" — Estado / posición / valor / variación
_RE_PRES_RANKING_ESTADO = re.compile(
    r"^(?P<estado>[A-ZÁÉÍÓÚ][a-záéíóúñ ]+?(?:\s+(?:de|del|la|las)\s+[A-Z][a-záéíóúñ ]+)?)\s+"
    r"(?P<pos>\d{1,2})\s+(?P<val>\d{1,2}\.\d)\s+",
    re.MULTILINE,
)

# Mapa nombre canónico de estados (variantes que aparecen en PDFs)
_ESTADO_VARIANTS = {
    "México": "México", "Edo. México": "Estado de México",
    "Estado De Mexico": "Estado de México", "Estado de México": "Estado de México",
    "Distrito Federal": "Ciudad de México", "Ciudad de México": "Ciudad de México",
    "CDMX": "Ciudad de México",
}

_VALID_ESTADOS = set(ESTADO_MAP.values())


def _canonicalize_estado(name: str) -> str | None:
    name = name.strip()
    if name in _VALID_ESTADOS:
        return name
    if name in _ESTADO_VARIANTS:
        return _ESTADO_VARIANTS[name]
    n = _normalize(name)
    for canon in _VALID_ESTADOS:
        if _normalize(canon) == n:
            return canon
    for variant, canon in _ESTADO_VARIANTS.items():
        if _normalize(variant) == n:
            return canon
    return None


def parse_pdf_presidente_ranking_estados(
    text: str, fecha_pub: date, url_fuente: str, actor_nombre: str
) -> list[EncuestaRow]:
    """Page 5 presidente: ranking 32 estados con aprobación CSP."""
    rows: list[EncuestaRow] = []
    seen: set[str] = set()
    for m in _RE_PRES_RANKING_ESTADO.finditer(text):
        canon = _canonicalize_estado(m.group("estado"))
        if not canon or canon in seen:
            continue
        try:
            val = float(m.group("val"))
        except ValueError:
            continue
        if not (20.0 <= val <= 100.0):
            continue
        seen.add(canon)
        rows.append(EncuestaRow(
            fuente=FUENTE,
            fecha_publicacion=fecha_pub,
            ambito="estatal",
            entidad=canon,
            actor_tipo="presidente_aprobacion_estatal",
            actor_nombre=actor_nombre,
            actor_partido=None,
            metrica="aprobacion",
            valor_pct=val,
            url_fuente=url_fuente,
        ))
    return rows


# Detector de tipo de PDF
def detect_pdf_type(pages_text: list[str]) -> str:
    """Detecta tipo de PDF: 'gobernadores' | 'alcaldes' | 'presidente' | 'unknown'."""
    p1 = pages_text[0] if pages_text else ""
    if "GOBERNADORES" in p1 and "GOBERNADORAS" in p1:
        return "gobernadores"
    if "150" in p1 and ("alcaldes" in p1.lower() or "presidentes y presidentas" in p1.lower()
                       or "municipales" in p1.lower()):
        return "alcaldes"
    if "PRESIDENTA" in p1 or "PRESIDENTE" in p1 or "Sheinbaum" in p1 or "OBRADOR" in p1.upper():
        return "presidente"
    # Fallback: scan all pages
    full = "\n".join(pages_text[:3])
    if "150 alcaldes" in full or "150 ALCALDES" in full:
        return "alcaldes"
    if "presidenta Claudia Sheinbaum" in full or "presidente López Obrador" in full:
        return "presidente"
    return "unknown"


def detect_actor_presidente(pages_text: list[str], periodo: date) -> str:
    """Determina si es Sheinbaum (post oct-2024) o AMLO (anterior)."""
    full = " ".join(pages_text[:5])
    if "Sheinbaum" in full or "SHEINBAUM" in full:
        return "Claudia Sheinbaum Pardo"
    if "OBRADOR" in full.upper() or "AMLO" in full:
        return "Andrés Manuel López Obrador"
    return "Sheinbaum" if periodo >= date(2024, 10, 1) else "López Obrador"


def parse_pdf_alcaldes(pdf_bytes: bytes, url_fuente: str, fallback_post_date: str | None = None) -> list[EncuestaRow]:
    """Parser PDFs alcaldes (boletines '150 alcaldes' Mitofsky).

    v2 (2026-05-08): extrae histórico nacional (p2/p3) + ranking individual de
    los 150 alcaldes (p4-p13). Layout fragmentado de 3 líneas por alcalde
    (nombre / pos+val / municipio,estado) manejado con state machine.
    """
    rows: list[EncuestaRow] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        pages_text = [(p.extract_text() or "") for p in pdf.pages]
        if len(pages_text) < 3:
            return rows
        # Periodo del PDF
        period = detect_pdf_period(pages_text[0], fallback_post_date)
        # Histórico nacional puede estar en p3 o p2
        for idx in [2, 1, 3]:
            if idx >= len(pages_text):
                continue
            sub = parse_pdf_alcaldes_historico(pages_text[idx], url_fuente)
            if sub:
                rows.extend(sub)
                log.info("p%d alcaldes histórico: %d datapoints", idx + 1, len(sub))
                break
        # Ranking individual 150 alcaldes (p4-p13)
        if period:
            individual = parse_pdf_alcaldes_ranking(pages_text, period, url_fuente)
            if individual:
                rows.extend(individual)
                log.info("alcaldes ranking individual %s: %d", period.isoformat(), len(individual))
    return rows


def parse_pdf_presidente(pdf_bytes: bytes, url_fuente: str, fallback_post_date: str | None = None) -> list[EncuestaRow]:
    """Parser PDFs aprobación presidencial Mitofsky (Sheinbaum o AMLO).

    Extrae:
    - p2: serie histórica 12 meses del trimestre/año reciente
    - p5: ranking aprobación CSP por estado (32 estados)
    """
    rows: list[EncuestaRow] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        pages_text = [(p.extract_text() or "") for p in pdf.pages]
        if len(pages_text) < 2:
            return rows
        period = detect_pdf_period(pages_text[0], fallback_post_date)
        if not period:
            log.warning("PDF presidente sin periodo detectable")
            return rows
        actor = detect_actor_presidente(pages_text, period)
        log.info("PDF presidente periodo=%s actor=%s", period.isoformat(), actor)

        # Page 2: histórico mensual
        if len(pages_text) >= 2:
            hist = parse_pdf_presidente_historico(pages_text[1], period, url_fuente, actor)
            rows.extend(hist)
            log.info("p2 presidente histórico: %d datapoints", len(hist))

        # Page 5 (o 4-6): ranking estados
        for idx in [4, 3, 5, 6]:
            if idx >= len(pages_text):
                continue
            t = pages_text[idx]
            if "RANKING" in t.upper() and ("ESTADO" in t.upper() or "% ACUERDO POR" in t):
                estado_rows = parse_pdf_presidente_ranking_estados(
                    t, period, url_fuente, actor
                )
                if estado_rows:
                    rows.extend(estado_rows)
                    log.info("p%d ranking estados: %d", idx + 1, len(estado_rows))
                    break
    return rows


def parse_pdf_gobernadores(pdf_bytes: bytes, url_fuente: str, fallback_post_date: str | None = None) -> list[EncuestaRow]:
    """Parser completo PDF gobernadores Mitofsky.

    Maneja 2 formatos detectados:
    - Boletines recientes (≥ ~boletín 76, dic-2025+): p4 = serie nacional histórica,
      p5 = ranking del mes.
    - Boletines antiguos (≤ ~boletín 70): no hay serie histórica, p4 = ranking del mes.

    Idempotencia delegada al ingester.
    """
    rows: list[EncuestaRow] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        pages_text = [(p.extract_text() or "") for p in pdf.pages]
        if len(pages_text) < 4:
            log.warning("PDF inesperado: solo %d páginas", len(pages_text))
            return rows

        period = detect_pdf_period(pages_text[0], fallback_post_date)
        if not period:
            log.warning("No detecté periodo del PDF")
            return rows
        log.info("PDF periodo: %s  (%d páginas)", period.isoformat(), len(pages_text))

        # Serie histórica nacional (si existe)
        idx_nacional = _find_page_with(pages_text, "PROMEDIO NACIONAL DE APROBACIÓN DE GOBERNADORES")
        if idx_nacional is not None:
            nacional = parse_page4_serie_nacional(pages_text[idx_nacional], url_fuente)
            rows.extend(nacional)
            log.info("p%d serie nacional: %d datapoints", idx_nacional + 1, len(nacional))
        else:
            log.info("PDF sin sección 'PROMEDIO NACIONAL' (boletín antiguo)")

        # Ranking del mes — buscar página con "LUGAR % DE ACUERDO" o "% DE ACUERDO"
        idx_ranking = _find_page_with(pages_text, "LUGAR % DE ACUERDO")
        if idx_ranking is None:
            idx_ranking = _find_page_with(pages_text, "% DE ACUERDO")
        if idx_ranking is not None:
            ranking = parse_ranking_page(pages_text[idx_ranking], period, url_fuente)
            rows.extend(ranking)
            log.info("p%d ranking %s: %d gobernadores", idx_ranking + 1, period.isoformat(), len(ranking))
        else:
            log.warning("PDF sin sección de ranking detectable")

    return rows
