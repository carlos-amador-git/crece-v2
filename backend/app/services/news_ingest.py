"""S4.7 — RSS ingest de medios MX con cobertura CDMX.

Procesa feeds RSS de fuentes oficiales y medios nacionales, inserta items
nuevos en `social_posts` con `platform='NEWS'` (reusando el schema
existente en vez de crear una tabla news_posts separada, decisión del plan).

Fuentes:
    - Presidencia MX (gob.mx)
    - Gaceta CDMX
    - Congreso CDMX
    - IECM
    - El Universal, Milenio, Animal Político, Aristegui

NOTA sobre idempotencia: cada item RSS tiene un `guid` (o `link` como
fallback). Se usa como `platform_post_id` con prefijo `news:` para evitar
colisiones con otros scrapers.

NOTA sobre platform enum: NEWS debe existir en `platform_enum`. Si no
existe, este task logueara WARNING y descartará items hasta que se agregue
la migración correspondiente.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RssFeed:
    name: str
    url: str
    tipo: str  # "OFICIAL" | "GOBIERNO" | "MEDIO"


RSS_SOURCES: list[RssFeed] = [
    # Oficiales / gobierno
    RssFeed("Presidencia MX", "https://www.gob.mx/presidencia/rss/prensa", "OFICIAL"),
    RssFeed(
        "Gaceta CDMX",
        "https://data.consejeria.cdmx.gob.mx/portal_old/gaceta-oficial-rss.xml",
        "GOBIERNO",
    ),
    RssFeed("Congreso CDMX", "https://www.congresocdmx.gob.mx/feed/", "GOBIERNO"),
    RssFeed("IECM", "https://www.iecm.mx/feed/", "GOBIERNO"),
    # Medios nacionales con cobertura CDMX
    RssFeed("El Universal CDMX", "https://www.eluniversal.com.mx/rss.xml", "MEDIO"),
    RssFeed("Milenio CDMX", "https://www.milenio.com/rss", "MEDIO"),
    RssFeed("Animal Político", "https://www.animalpolitico.com/feed/", "MEDIO"),
    RssFeed("Aristegui Noticias", "https://aristeguinoticias.com/feed/", "MEDIO"),
]


@dataclass
class RssItem:
    guid: str
    title: str
    link: str
    published: datetime | None
    summary: str
    source: str


def _parse_feed(xml_bytes: bytes, source: str) -> list[RssItem]:
    """Parser RSS minimalista sin dep feedparser.

    Solo extrae los campos que necesitamos. No maneja Atom completo, solo
    RSS 2.0 <item>. Suficiente para las fuentes listadas.
    """
    import re
    from html import unescape

    text_content = xml_bytes.decode("utf-8", errors="replace")
    items: list[RssItem] = []
    for item_match in re.finditer(r"<item[^>]*>(.*?)</item>", text_content, re.DOTALL):
        block = item_match.group(1)

        def _field(tag: str, _block: str = block) -> str:
            # Handles both <tag>value</tag> and <tag><![CDATA[value]]></tag>
            m = re.search(
                rf"<{tag}(?:\s[^>]*)?>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</{tag}>",
                _block,
                re.DOTALL,
            )
            return unescape(m.group(1).strip()) if m else ""

        title = _field("title")
        link = _field("link")
        guid = _field("guid") or link
        description = _field("description")
        pub_date_raw = _field("pubDate")

        published: datetime | None = None
        if pub_date_raw:
            try:
                from email.utils import parsedate_to_datetime

                published = parsedate_to_datetime(pub_date_raw)
            except (TypeError, ValueError):
                published = None

        if title and (link or guid):
            # Strip HTML tags from summary briefly
            summary = re.sub(r"<[^>]+>", " ", description)
            summary = re.sub(r"\s+", " ", summary).strip()
            items.append(
                RssItem(
                    guid=guid,
                    title=title,
                    link=link,
                    published=published,
                    summary=summary[:1000],
                    source=source,
                )
            )
    return items


async def fetch_feed(client: httpx.AsyncClient, feed: RssFeed) -> list[RssItem]:
    try:
        resp = await client.get(feed.url, timeout=15.0, follow_redirects=True)
        resp.raise_for_status()
    except Exception as exc:
        logger.warning("RSS fetch failed %s: %s", feed.name, exc)
        return []
    return _parse_feed(resp.content, feed.name)


def _platform_post_id(item: RssItem) -> str:
    raw = item.guid or item.link
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:24]
    return f"news:{digest}"


async def fetch_all_feeds(feeds: list[RssFeed] = RSS_SOURCES) -> list[RssItem]:
    """Fetch + parse all RSS feeds. Pure function, no DB side effects.

    Returns a flat list of items across all feeds. Failed fetches are
    logged and skipped. The caller decides what to persist.
    """
    async with httpx.AsyncClient() as client:
        out: list[RssItem] = []
        for feed in feeds:
            items = await fetch_feed(client, feed)
            out.extend(items)
        return out


# NOTE: persistencia a `social_posts` con `platform='NEWS'` está pendiente
# porque requiere:
#   1. Agregar 'NEWS' a `platform_enum` via migración
#   2. Decidir si `social_posts.profile_id` se hace nullable o si creamos
#      un perfil sintético por fuente RSS (`news:presidencia`, etc.)
# Ambos cambios son fuera de scope S4.7 — se documenta como deuda D-S4-07.
# Por ahora, `detect_trends` (S4.5) consume RSS en memoria vía
# `fetch_all_feeds()` sin persistir.
