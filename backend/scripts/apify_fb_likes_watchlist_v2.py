#!/usr/bin/env python3
"""Batch likes scraper para watchlist Saymi · v2 con pool de cuentas Apify.

Usa apify/facebook-likes-scraper (el único actor PUBLIC confiable validado).
Match dual: por FB user ID extraído del profileUrl (cuando es numérico) + por
nombre normalizado (fallback para pfbid_ opacos).

Output:
- Insert en watched_like_events con source='apify_reactions'
- JSON dump completo en .context/apify_likes_run_<timestamp>.json

Usage:
    python3 backend/scripts/apify_fb_likes_watchlist_v2.py [--limit 50] [--top-posts 10]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import sys
import time
import unicodedata
from datetime import UTC, datetime
from pathlib import Path

import psycopg2
import psycopg2.extras

PROJECT_ROOT = Path("/Users/marxchavez/Projects/crece-v2")
for env_file in [PROJECT_ROOT / ".env", PROJECT_ROOT / "backend/.env.scraping-keys"]:
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.split("#")[0].strip())

sys.path.insert(0, str(PROJECT_ROOT / "backend"))
from app.services.apify_pool import pick_token, mark_exhausted, status_report  # noqa: E402

from apify_client import ApifyClient  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("apify_fb_likes_v2")

SALT = os.environ.get("COMMENT_AUTHOR_SALT", "crece-v2-lfpdppp-salt-2026")
DB_DSN = "host=localhost port=5438 dbname=crece user=crece password=crece_dev"
DIRIGENTE_ID = 3
ACTOR = "apify/facebook-likes-scraper"


def H(fbid: str) -> str:
    return hashlib.sha256(f"FACEBOOK:{fbid}:{SALT}".encode()).hexdigest()


def norm(s: str) -> str:
    if not s:
        return ""
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()


def load_watchlist(cur) -> tuple[dict[str, dict], dict[str, dict]]:
    """Returns (by_hash, by_name) → cada uno value=watched_profile row."""
    cur.execute(
        """SELECT id, display_name, profile_external_id, author_hash, profile_handle
           FROM watched_profiles
           WHERE dirigente_observador_id = %s AND is_active = TRUE""",
        (DIRIGENTE_ID,),
    )
    rows = cur.fetchall()
    by_hash = {r["author_hash"]: dict(r) for r in rows}
    by_name = {norm(r["display_name"]): dict(r) for r in rows if r["display_name"]}
    return by_hash, by_name


def load_target_posts(cur, top_n: int) -> list[tuple[int, str, int]]:
    """Top N posts FB de Saymi con URL (no reels), por engagement reciente."""
    cur.execute(
        """SELECT sp.id, sp.raw_data->>'url' AS url, sp.likes
           FROM social_posts sp
           JOIN social_profiles spr ON sp.profile_id = spr.id
           WHERE spr.dirigente_id = %s AND spr.platform = 'FACEBOOK'
             AND sp.raw_data->>'url' IS NOT NULL
             AND sp.raw_data->>'url' NOT LIKE '%%/reel/%%'
             AND sp.published_at > NOW() - INTERVAL '14 days'
           ORDER BY sp.likes DESC, sp.published_at DESC
           LIMIT %s""",
        (DIRIGENTE_ID, top_n),
    )
    return [(r["id"], r["url"], r["likes"]) for r in cur.fetchall()]


def extract_fbid(profile_url: str) -> str | None:
    """facebook.com/123456789 → '123456789'. facebook.com/pfbid... → None."""
    if not profile_url:
        return None
    m = re.search(r"facebook\.com/(\d{6,})\b", profile_url)
    return m.group(1) if m else None


def process_items(
    items: list[dict],
    by_hash: dict[str, dict],
    by_name: dict[str, dict],
) -> list[dict]:
    """Match items contra watchlist. Devuelve hits con dedup."""
    seen = set()
    hits = []
    for it in items:
        name = it.get("name") or ""
        purl = it.get("profileUrl") or ""
        reaction = it.get("reaction") or "like"
        post_url = it.get("inputUrl") or it.get("facebookUrl") or ""

        match = None
        match_method = None
        fbid = extract_fbid(purl)
        if fbid:
            h = H(fbid)
            if h in by_hash:
                match = by_hash[h]
                match_method = "id_hash"
        if not match and norm(name) in by_name:
            match = by_name[norm(name)]
            match_method = "name_norm"

        if match:
            key = (match["id"], post_url, reaction)
            if key in seen:
                continue
            seen.add(key)
            hits.append({
                "watched_profile_id": match["id"],
                "watched_display_name": match["display_name"],
                "scraped_name": name,
                "reaction_type": reaction,
                "post_url": post_url,
                "match_method": match_method,
                "profile_url": purl,
            })
    return hits


def get_post_id_by_url(cur, post_url: str) -> int | None:
    cur.execute(
        "SELECT id FROM social_posts WHERE raw_data->>'url' = %s LIMIT 1",
        (post_url,),
    )
    r = cur.fetchone()
    return r["id"] if r else None


def insert_like_events(cur, hits: list[dict]) -> int:
    inserted = 0
    for h in hits:
        post_id = get_post_id_by_url(cur, h["post_url"])
        if not post_id:
            log.warning("post_url no encontrado en BD: %s", h["post_url"])
            continue
        cur.execute(
            """INSERT INTO watched_like_events
                 (watched_profile_id, post_id, reaction_type, source)
               VALUES (%s, %s, %s, 'apify_reactions')
               ON CONFLICT DO NOTHING
               RETURNING id""",
            (h["watched_profile_id"], post_id, h["reaction_type"]),
        )
        if cur.fetchone():
            inserted += 1
    return inserted


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=80, help="resultsLimit per post")
    ap.add_argument("--top-posts", type=int, default=10, help="cuántos posts top procesar")
    ap.add_argument("--dry-run", action="store_true", help="no insertar en BD")
    args = ap.parse_args()

    log.info("=== Pool status pre-run ===")
    for s in status_report():
        log.info("  %s: $%.2f used · $%.2f disp", s.name, s.used_usd, s.available_usd)

    conn = psycopg2.connect(DB_DSN)
    conn.autocommit = False
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SET app.current_org_id = '2'")

    by_hash, by_name = load_watchlist(cur)
    log.info("Watchlist: %d perfiles (hash=%d names=%d)", len(by_hash), len(by_hash), len(by_name))

    posts = load_target_posts(cur, args.top_posts)
    log.info("Target posts: %d", len(posts))
    for pid, url, likes in posts:
        log.info("  [%d] %d likes · %s", pid, likes, url[-60:])

    token = pick_token(min_budget_usd=2.0)
    client = ApifyClient(token)

    urls = [u for _, u, _ in posts]
    log.info("Calling %s · %d URLs · resultsLimit=%d/url", ACTOR, len(urls), args.limit)
    t0 = time.time()
    try:
        run = client.actor(ACTOR).call(
            run_input={"resultsLimit": args.limit, "startUrls": [{"url": u} for u in urls]},
            timeout_secs=1800,
        )
    except Exception as e:
        log.error("Actor call failed: %s", e)
        mark_exhausted(token)
        sys.exit(1)

    elapsed = time.time() - t0
    cost = float(run.get("usageTotalUsd") or 0.0)
    log.info("Run done · %.1fs · status=%s · cost SDK=$%.4f (puede subreportar)",
             elapsed, run["status"], cost)

    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    log.info("Items retornados: %d", len(items))

    hits = process_items(items, by_hash, by_name)
    log.info("=== Matches (dedup): %d ===", len(hits))
    by_watched: dict[str, list[dict]] = {}
    for h in hits:
        by_watched.setdefault(h["watched_display_name"], []).append(h)
    for name, lst in by_watched.items():
        methods = ", ".join(sorted({h["match_method"] for h in lst}))
        log.info("  ✓ %s · %d likes · methods=%s", name, len(lst), methods)

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    dump_path = PROJECT_ROOT / f".context/apify_likes_run_{timestamp}.json"
    dump_path.write_text(json.dumps({
        "timestamp": timestamp,
        "actor": ACTOR,
        "token_suffix": token[-8:],
        "params": {"resultsLimit": args.limit, "urls_count": len(urls)},
        "elapsed_s": round(elapsed, 1),
        "cost_sdk_usd": cost,
        "items_count": len(items),
        "matches": hits,
        "all_items": items,
    }, ensure_ascii=False, indent=2, default=str))
    log.info("Dump: %s", dump_path)

    if args.dry_run:
        log.info("DRY-RUN — no se insertó en BD")
    else:
        inserted = insert_like_events(cur, hits)
        conn.commit()
        log.info("Insert: %d nuevos like_events", inserted)

    cur.close()
    conn.close()

    log.info("=== Pool status post-run ===")
    for s in status_report():
        log.info("  %s: $%.2f used · $%.2f disp", s.name, s.used_usd, s.available_usd)


if __name__ == "__main__":
    main()
