"""PollsMX (polls.politico.mx) scraper — extrae datapoints de artículos en texto plano.

Sitio Arc XP-based. Páginas listing (homepage, /noticias, /aprobacion,
/power-ranking) son shells SPA sin datos. Pero los **artículos individuales**
publican % en texto plano dentro del body — parseable con regex.

Estrategia v1:
1. Crawl homepage + /noticias para descubrir URLs de artículos.
2. Por cada artículo: extract title + body text.
3. Regex sobre body para capturar tuplas (actor, valor_pct).
4. Inferir ámbito + métrica + fecha desde URL slug + título.

Limitaciones conocidas:
- Solo captura ~20 artículos visibles en homepage (no histórico completo)
- Regex captura partidos/políticos comunes; misses casos custom
- Fecha = fecha de publicación del artículo (no fecha de campo de la encuesta)
"""
from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from datetime import date

import httpx

log = logging.getLogger("encuestas_pollsmx")

FUENTE = "PollsMX"
BASE = "https://polls.politico.mx"

USER_AGENT = "Mozilla/5.0 (compatible; CRECE-v2-pollsmx/1.0)"

# Listing pages to crawl for article URLs
LISTING_PAGES = [
    "/",
    "/noticias",
    "/aprobacion",
    "/power-ranking/gobernadores/2027",
]

# Article URL pattern: /YYYY/MM/DD/slug/
_RE_ARTICLE_URL = re.compile(r'href="(/(20\d{2})/(\d{2})/(\d{2})/[^"#?]+/)"')

# Title from <h1> or og:title
_RE_TITLE = re.compile(r'<meta\s+property="og:title"\s+content="([^"]+)"')

# Partidos políticos canónicos (para extracción de intención voto)
PARTIDO_PATTERNS = {
    "MORENA": r"\bMorena\b",
    "PAN": r"\bPAN\b|Partido Acci[oó]n Nacional",
    "PRI": r"\bPRI\b|Partido Revolucionario Institucional",
    "MC": r"Movimiento Ciudadano|\bMC\b",
    "PT": r"\bPT\b|Partido del Trabajo",
    "PVEM": r"\bPVEM\b|Partido Verde",
}

# Aproximación: políticos relevantes con expresión común en encuestas
POLITICO_PATTERNS = {
    "Claudia Sheinbaum Pardo": r"Sheinbaum|presidenta Claudia",
    "Andrés Manuel López Obrador": r"L[oó]pez Obrador|\bAMLO\b",
    "Lilly Téllez": r"Lilly T[eé]llez",
    "Omar García Harfuch": r"Harfuch|Garc[ií]a Harfuch",
    "Marcelo Ebrard": r"Ebrard",
    "Adán Augusto López": r"Ad[aá]n Augusto",
    "Rubén Rocha Moya": r"Rocha Moya|Rocha",
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


def _strip_html(html: str) -> str:
    text = re.sub(r"<script.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;|&#160;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&quot;", '"', text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _normalize(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", s.strip().lower())


def discover_articles(http: httpx.Client) -> dict[str, dict]:
    """Crawl listing pages para descubrir URLs de artículos.

    Returns dict {article_url: {"date": date, "slug": str}}.
    """
    found: dict[str, dict] = {}
    for path in LISTING_PAGES:
        url = BASE + path
        try:
            r = http.get(url, headers={"User-Agent": USER_AGENT}, timeout=20.0)
            if r.status_code != 200:
                continue
            for m in _RE_ARTICLE_URL.finditer(r.text):
                rel = m.group(1)
                full = BASE + rel
                if full in found:
                    continue
                year, month, day = int(m.group(2)), int(m.group(3)), int(m.group(4))
                try:
                    d = date(year, month, day)
                except ValueError:
                    continue
                slug = rel.rstrip("/").rsplit("/", 1)[-1]
                found[full] = {"date": d, "slug": slug}
        except Exception as e:
            log.warning("listing %s failed: %s", url, e)
    return found


def detect_metric_ambito(title: str, body: str) -> tuple[str, str, str | None, str]:
    """Inferir (ámbito, metrica, entidad, actor_tipo) del título.

    Returns (ambito, metrica, entidad, actor_tipo).
    """
    t = _normalize(title + " " + body[:500])

    # Detectar entidad (estado mexicano nombrado)
    entidades = {
        "sinaloa": "Sinaloa", "campeche": "Campeche", "aguascalientes": "Aguascalientes",
        "baja california": "Baja California", "chihuahua": "Chihuahua",
        "guerrero": "Guerrero", "michoacan": "Michoacán", "nayarit": "Nayarit",
        "nuevo leon": "Nuevo León", "queretaro": "Querétaro",
        "quintana roo": "Quintana Roo", "zacatecas": "Zacatecas",
        "ciudad de mexico": "Ciudad de México", "cdmx": "Ciudad de México",
        "estado de mexico": "Estado de México", "edomex": "Estado de México",
    }
    entidad = None
    for needle, canon in entidades.items():
        if needle in t:
            entidad = canon
            break

    # Detectar ámbito + métrica
    if "intencion" in t.replace("ó", "o") or "votaria" in t.replace("í", "i") or "votar" in t \
       or "preferencia" in t or "elecciones 2027" in t or "rumbo a 2027" in t:
        metrica = "intencion_voto"
        ambito = "estatal" if entidad else "federal"
        actor_tipo = "candidato" if "lidera" in t or "puntero" in t or "preferencias" in t else "partido"
    elif "aprobacion" in t.replace("ó", "o") or "aprueb" in t:
        metrica = "aprobacion"
        ambito = "estatal" if entidad else "federal"
        actor_tipo = "presidente" if ("sheinbaum" in t or "obrador" in t or "presidenta" in t or "amlo" in t) else "gobernador"
    elif "inseguridad" in t or "seguridad" in t:
        metrica = "percepcion_inseguridad"
        ambito = "estatal" if entidad else "federal"
        actor_tipo = "tema"
    else:
        metrica = "tema"
        ambito = "estatal" if entidad else "federal"
        actor_tipo = "tema"

    return ambito, metrica, entidad, actor_tipo


def extract_datapoints(
    body: str, metrica: str, actor_tipo: str
) -> list[tuple[str, str | None, float]]:
    """Extrae tuplas (actor_nombre, partido, valor_pct) del body de un artículo.

    Estrategia: para cada partido/político conocido, busca el primer % cercano
    en una ventana de ~150 chars desde la mención.
    """
    rows: list[tuple[str, str | None, float]] = []
    seen: set[str] = set()

    if actor_tipo in ("partido",):
        # Buscar partidos
        for partido_canon, pat in PARTIDO_PATTERNS.items():
            for m in re.finditer(pat, body, re.IGNORECASE):
                # Tomar ventana de 150 chars después de mención
                window = body[m.end(): m.end() + 200]
                pm = re.search(r"\b(\d{1,2}(?:\.\d)?)\s*%", window)
                if not pm:
                    continue
                try:
                    val = float(pm.group(1))
                except ValueError:
                    continue
                if not (0.5 <= val <= 70.0):
                    continue
                if partido_canon in seen:
                    continue
                seen.add(partido_canon)
                rows.append((partido_canon, partido_canon, val))
                break  # solo primer match por partido
    elif actor_tipo in ("presidente", "candidato", "gobernador"):
        # Buscar políticos conocidos
        for nombre_canon, pat in POLITICO_PATTERNS.items():
            for m in re.finditer(pat, body, re.IGNORECASE):
                window = body[m.end(): m.end() + 200]
                pm = re.search(r"\b(\d{1,2}(?:\.\d)?)\s*%", window)
                if not pm:
                    continue
                try:
                    val = float(pm.group(1))
                except ValueError:
                    continue
                if not (5.0 <= val <= 99.0):
                    continue
                if nombre_canon in seen:
                    continue
                seen.add(nombre_canon)
                rows.append((nombre_canon, None, val))
                break
    elif actor_tipo == "tema":
        # Buscar primer % prominente
        m = re.search(r"\b(\d{1,2}(?:\.\d)?)\s*%", body)
        if m:
            try:
                val = float(m.group(1))
                if 1.0 <= val <= 99.0:
                    rows.append(("Tema", None, val))
            except ValueError:
                pass

    return rows


def parse_article(url: str, http: httpx.Client) -> tuple[date | None, str, list[EncuestaRow]]:
    """Descarga un artículo, extrae datapoints. Returns (date, title, rows)."""
    r = http.get(url, headers={"User-Agent": USER_AGENT}, timeout=20.0)
    if r.status_code != 200:
        return None, "", []
    h = r.text
    title_m = _RE_TITLE.search(h)
    title = title_m.group(1) if title_m else ""

    # Date from URL
    date_m = re.search(r"/(\d{4})/(\d{2})/(\d{2})/", url)
    if not date_m:
        return None, title, []
    try:
        fecha = date(int(date_m.group(1)), int(date_m.group(2)), int(date_m.group(3)))
    except ValueError:
        return None, title, []

    body = _strip_html(h)
    ambito, metrica, entidad, actor_tipo = detect_metric_ambito(title, body)
    datapoints = extract_datapoints(body, metrica, actor_tipo)

    rows = []
    for nombre, partido, val in datapoints:
        rows.append(EncuestaRow(
            fuente=FUENTE,
            fecha_publicacion=fecha,
            ambito=ambito,
            entidad=entidad,
            actor_tipo=actor_tipo,
            actor_nombre=nombre,
            actor_partido=partido,
            metrica=metrica,
            valor_pct=val,
            url_fuente=url,
        ))
    return fecha, title, rows


def scrape_pollsmx(http: httpx.Client | None = None) -> list[EncuestaRow]:
    """Top-level scraper: discover articles → parse each → return rows."""
    client = http or httpx.Client(follow_redirects=True, timeout=30.0)
    try:
        articles = discover_articles(client)
        log.info("PollsMX: %d artículos descubiertos", len(articles))
        all_rows: list[EncuestaRow] = []
        for url in articles:
            try:
                fecha, title, rows = parse_article(url, client)
                if rows:
                    log.info("  ✓ %s — %d datapoints", title[:55], len(rows))
                    all_rows.extend(rows)
                else:
                    log.debug("  ✗ %s — 0 datapoints", title[:55])
            except Exception as e:
                log.warning("  parse failed %s: %s", url, e)
        return all_rows
    finally:
        if not http:
            client.close()
