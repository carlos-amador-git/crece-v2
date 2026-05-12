"""OpenGraph + Twitter Card meta extraction.

Universal URL enrichment helper for sites where no specific scraper adapter
exists (blogs, news sites, GitHub Pages, etc). Uses httpx (already a dep)
and regex — zero new dependencies.

Usage:
    from app.scrapers.helpers.opengraph import extract_opengraph

    meta = extract_opengraph("https://example.com/article")
    if meta:
        print(meta.title, meta.description, meta.image)

Returns None on fetch failure or when the page has no meta tags at all.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10.0
DEFAULT_USER_AGENT = "Mozilla/5.0 (compatible; CreceBot/2.0; +https://consultoriamd.com/crece)"
MAX_HTML_BYTES = 1_500_000  # 1.5 MB — enough for head section of any real page

# Matches <meta property="og:..." content="..."> and <meta name="twitter:..." content="...">
# Non-greedy, case-insensitive, handles both single and double quotes.
_META_RE = re.compile(
    r"""<meta\s+(?:property|name)\s*=\s*["'](?P<key>(?:og|twitter|article):[^"']+)["']"""
    r"""\s+content\s*=\s*["'](?P<value>[^"']*)["']""",
    re.IGNORECASE,
)
# Reversed order: content="..." before property="..." (some CMS do this)
_META_RE_REVERSED = re.compile(
    r"""<meta\s+content\s*=\s*["'](?P<value>[^"']*)["']\s+"""
    r"""(?:property|name)\s*=\s*["'](?P<key>(?:og|twitter|article):[^"']+)["']""",
    re.IGNORECASE,
)
_TITLE_RE = re.compile(r"<title[^>]*>([^<]+)</title>", re.IGNORECASE)


@dataclass
class OpenGraphMeta:
    url: str
    title: str | None
    description: str | None
    image: str | None
    site_name: str | None
    type: str | None
    raw: dict[str, str]

    def is_empty(self) -> bool:
        return not any([self.title, self.description, self.image, self.site_name])

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "description": self.description,
            "image": self.image,
            "site_name": self.site_name,
            "type": self.type,
            "raw": self.raw,
        }


def _parse_meta(html: str) -> dict[str, str]:
    """Extract og:*, twitter:* and article:* meta tags from HTML head."""
    found: dict[str, str] = {}
    for regex in (_META_RE, _META_RE_REVERSED):
        for match in regex.finditer(html):
            key = match.group("key").lower().strip()
            value = match.group("value").strip()
            if key and value and key not in found:
                found[key] = value
    return found


def _coalesce(meta: dict[str, str], *keys: str) -> str | None:
    for k in keys:
        if meta.get(k):
            return meta[k]
    return None


def parse_opengraph(html: str, url: str) -> OpenGraphMeta:
    """Parse an HTML string into an OpenGraphMeta without doing any network I/O."""
    raw = _parse_meta(html)

    title = _coalesce(raw, "og:title", "twitter:title")
    if not title:
        m = _TITLE_RE.search(html)
        if m:
            title = m.group(1).strip()

    description = _coalesce(raw, "og:description", "twitter:description")
    image = _coalesce(raw, "og:image", "og:image:url", "twitter:image")
    site_name = _coalesce(raw, "og:site_name", "twitter:site")
    og_type = _coalesce(raw, "og:type")

    return OpenGraphMeta(
        url=url,
        title=title,
        description=description,
        image=image,
        site_name=site_name,
        type=og_type,
        raw=raw,
    )


def extract_opengraph(
    url: str,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    user_agent: str = DEFAULT_USER_AGENT,
    max_bytes: int = MAX_HTML_BYTES,
) -> OpenGraphMeta | None:
    """Fetch `url` and extract OpenGraph + Twitter Card meta tags.

    Returns None on any of:
        - network failure (timeout, DNS, connection reset)
        - non-2xx response
        - empty body
        - no meta tags AND no <title>

    The caller is responsible for mapping the result into SocialPost fields
    if needed.
    """
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
    }
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
            response = client.get(url)
    except (httpx.HTTPError, httpx.TimeoutException) as exc:
        logger.warning("opengraph fetch failed for %s: %s", url, exc)
        return None

    if response.status_code >= 400:
        logger.info("opengraph fetch got HTTP %d for %s", response.status_code, url)
        return None

    html = response.text
    if not html:
        return None

    if len(html.encode("utf-8", errors="ignore")) > max_bytes:
        html = html[: max_bytes // 2]  # rough UTF-8 safe cut

    meta = parse_opengraph(html, url=str(response.url))
    if meta.is_empty():
        logger.info("opengraph parse found no meta tags for %s", url)
        return None

    return meta
