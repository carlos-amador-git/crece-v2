"""Cataloga links Google Drive (botón "DESCARGAR RANKING") en posts Mitofsky.

Lee `blog-posts-sitemap.xml`, filtra a 127 posts gobernadores/aprobación/ranking/alcalde,
y por cada uno hace fetch del HTML para extraer el `href` de Google Drive.

Output: `crece-v2/captures/mitofsky-gdrive-catalog.json`

Usage:
    python backend/scripts/mitofsky_catalog_gdrive.py [--limit N] [--out PATH]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import httpx

SITEMAP = "https://www.mitofsky.mx/blog-posts-sitemap.xml"
USER_AGENT = "Mozilla/5.0 (compatible; CRECE-v2-mitofsky-catalog/1.0)"

RELEVANT_PAT = re.compile(r"gober|ranking|aprobacion|aprueb|alcald", re.I)
GDRIVE_HREF = re.compile(
    r'href="(https://drive\.google\.com/file/d/([A-Za-z0-9_-]{20,})/[^"]*)"'
)
TITLE_PAT = re.compile(r"<title>([^<]+)</title>")
PUBDATE_PAT = re.compile(r"<meta\s+property=\"article:published_time\"\s+content=\"([^\"]+)\"")


@dataclass
class CatalogEntry:
    post_url: str
    post_title: str | None
    post_date: str | None  # ISO
    gdrive_id: str | None
    gdrive_url: str | None
    download_label: str | None  # "DESCARGAR RANKING" / "DESCARGAR" / etc.


def fetch_sitemap_urls() -> list[str]:
    r = httpx.get(SITEMAP, headers={"User-Agent": USER_AGENT}, timeout=20.0)
    r.raise_for_status()
    urls = re.findall(r"<loc>(https://www\.mitofsky\.mx/post/[^<]+)</loc>", r.text)
    return [u for u in urls if RELEVANT_PAT.search(u)]


def parse_post(url: str, http: httpx.Client) -> CatalogEntry:
    r = http.get(url, headers={"User-Agent": USER_AGENT}, timeout=20.0)
    if r.status_code != 200:
        return CatalogEntry(url, None, None, None, None, None)
    h = r.text
    title = None
    m = TITLE_PAT.search(h)
    if m:
        title = m.group(1).strip()
    date = None
    m = PUBDATE_PAT.search(h)
    if m:
        date = m.group(1)
    gdrive_url = None
    gdrive_id = None
    m = GDRIVE_HREF.search(h)
    if m:
        gdrive_url = m.group(1)
        gdrive_id = m.group(2)
    label = None
    if gdrive_url:
        # Buscar el texto del botón cerca del href
        ctx = re.search(r"\"" + re.escape(gdrive_url) + r"\".{0,500}?>([A-ZÁÉÍÓÚ ]{4,40})<", h)
        if ctx:
            label = ctx.group(1).strip()
    return CatalogEntry(url, title, date, gdrive_id, gdrive_url, label)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="Procesar solo N posts (0=todos)")
    ap.add_argument(
        "--out",
        default="/tmp/mitofsky-gdrive-catalog.json",
        help="Path absoluto. Default /tmp/... (container-friendly).",
    )
    ap.add_argument("--throttle", type=float, default=0.4, help="Segundos entre requests")
    args = ap.parse_args()

    print("[catalog] descargando sitemap…", flush=True)
    urls = fetch_sitemap_urls()
    print(f"[catalog] {len(urls)} posts relevantes en sitemap", flush=True)
    if args.limit:
        urls = urls[: args.limit]
        print(f"[catalog] limitado a {len(urls)}", flush=True)

    out: list[CatalogEntry] = []
    with httpx.Client() as http:
        for i, u in enumerate(urls, 1):
            try:
                entry = parse_post(u, http)
                out.append(entry)
                marker = "✓" if entry.gdrive_url else "✗"
                short = u.rsplit("/", 1)[-1][:60]
                print(f"  [{i}/{len(urls)}] {marker} {short}", flush=True)
            except Exception as e:
                print(f"  [{i}/{len(urls)}] ERR {u}: {e}", flush=True)
                out.append(CatalogEntry(u, None, None, None, None, None))
            time.sleep(args.throttle)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump([asdict(e) for e in out], f, ensure_ascii=False, indent=2)

    with_gd = sum(1 for e in out if e.gdrive_url)
    print(f"\n[catalog] DONE: {with_gd}/{len(out)} con GDrive PDF link")
    print(f"[catalog] output: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
