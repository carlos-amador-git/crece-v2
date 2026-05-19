#!/usr/bin/env python3
"""Batch reactions scraper usando scraper_one/facebook-reactions-scraper.

A diferencia de apify/facebook-likes-scraper, este actor retorna `reactorId`
(FB user ID estable) en 100% de items → match por hash exacto sin pfbid.

Free accounts limited to 20 results/post.

Usage:
    python3 backend/scripts/apify_fb_reactions_scraper_one.py [--top-posts 10]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
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
            if not line or line.startswith("#") or "=" not in line: continue
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.split("#")[0].strip())

sys.path.insert(0, str(PROJECT_ROOT / "backend"))
from app.services.apify_pool import pick_token, mark_exhausted, status_report

from apify_client import ApifyClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("scraper_one_reactions")

SALT = os.environ.get("COMMENT_AUTHOR_SALT", "crece-v2-lfpdppp-salt-2026")
DB_DSN = "host=localhost port=5438 dbname=crece user=crece password=crece_dev"
DIRIGENTE_ID = 3
ACTOR = "scraper_one/facebook-reactions-scraper"


def H(fbid: str) -> str:
    return hashlib.sha256(f"FACEBOOK:{fbid}:{SALT}".encode()).hexdigest()


def norm(s: str) -> str:
    if not s: return ""
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()


def load_watchlist(cur):
    cur.execute(
        """SELECT id, display_name, profile_external_id, author_hash
           FROM watched_profiles
           WHERE dirigente_observador_id=%s AND is_active=TRUE""",
        (DIRIGENTE_ID,),
    )
    rows = cur.fetchall()
    return {r["author_hash"]: dict(r) for r in rows}, {norm(r["display_name"]): dict(r) for r in rows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top-posts", type=int, default=10)
    ap.add_argument("--offset", type=int, default=0, help="skip primeros N posts")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    log.info("=== Pool status pre-run ===")
    for s in status_report():
        log.info("  %s: $%.2f used · $%.2f disp", s.name, s.used_usd, s.available_usd)

    conn = psycopg2.connect(DB_DSN); conn.autocommit = False
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SET app.current_org_id='2'")
    by_hash, by_name = load_watchlist(cur)
    log.info("Watchlist: %d perfiles", len(by_hash))

    cur.execute(
        """SELECT sp.id, sp.raw_data->>'url' AS url, sp.likes
           FROM social_posts sp JOIN social_profiles spr ON sp.profile_id=spr.id
           WHERE spr.dirigente_id=%s AND spr.platform='FACEBOOK'
             AND sp.raw_data->>'url' IS NOT NULL
             AND sp.raw_data->>'url' NOT LIKE '%%/reel/%%'
             AND sp.published_at > NOW() - INTERVAL '14 days'
           ORDER BY sp.likes DESC, sp.published_at DESC
           OFFSET %s LIMIT %s""",
        (DIRIGENTE_ID, args.offset, args.top_posts),
    )
    posts = [(r["id"], r["url"], r["likes"]) for r in cur.fetchall()]
    log.info("Target posts: %d", len(posts))

    token = pick_token(min_budget_usd=1.0)
    client = ApifyClient(token)
    urls = [u for _, u, _ in posts]

    log.info("Calling %s · %d URLs · free=20 results/post", ACTOR, len(urls))
    t0 = time.time()
    try:
        run = client.actor(ACTOR).call(
            run_input={"postUrls": urls, "resultsLimit": 20},
            timeout_secs=1800,
        )
    except Exception as e:
        log.error("Actor failed: %s", e)
        mark_exhausted(token)
        sys.exit(1)

    elapsed = time.time() - t0
    cost = float(run.get("usageTotalUsd") or 0)
    log.info("Done · %.1fs · status=%s · cost SDK=$%.4f", elapsed, run["status"], cost)
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    log.info("Items retornados: %d", len(items))

    # Match exacto por reactorId (FB user ID) → hash
    hits = []
    seen = set()
    by_post_url = {u: pk for pk, u, _ in posts}
    for it in items:
        rid = str(it.get("reactorId") or "")
        name = it.get("reactorName") or ""
        rtype = it.get("reactionType") or "like"
        purl = it.get("postUrl") or ""
        method = None; match = None
        if rid:
            h = H(rid)
            if h in by_hash:
                match = by_hash[h]; method = "id_hash"
        if not match and norm(name) in by_name:
            match = by_name[norm(name)]; method = "name_norm"
        if match:
            key = (match["id"], purl, rtype)
            if key in seen: continue
            seen.add(key)
            hits.append({
                "watched_profile_id": match["id"],
                "watched_display_name": match["display_name"],
                "reactor_name": name,
                "reactor_id": rid,
                "reaction_type": rtype,
                "post_url": purl,
                "post_id": by_post_url.get(purl),
                "match_method": method,
            })

    log.info("=== Matches: %d ===", len(hits))
    by_watched = {}
    for h in hits:
        by_watched.setdefault(h["watched_display_name"], []).append(h)
    for n, lst in by_watched.items():
        log.info("  ✓ %s · %d reactions · methods=%s", n, len(lst),
                 ",".join(sorted({h["match_method"] for h in lst})))

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    dump = PROJECT_ROOT / f".context/scraper_one_reactions_{timestamp}.json"
    dump.write_text(json.dumps({
        "actor": ACTOR, "token_suffix": token[-8:],
        "posts": [(p[0], p[1], p[2]) for p in posts],
        "elapsed_s": round(elapsed, 1), "cost_sdk_usd": cost,
        "items_count": len(items), "matches": hits, "all_items": items,
    }, ensure_ascii=False, indent=2, default=str))
    log.info("Dump: %s", dump.name)

    if args.dry_run:
        log.info("DRY-RUN: no insert")
    else:
        inserted = 0
        for h in hits:
            if h["post_id"] is None:
                log.warning("post_url no match BD: %s", h["post_url"])
                continue
            cur.execute(
                """INSERT INTO watched_like_events
                     (watched_profile_id, post_id, reaction_type, source)
                   VALUES (%s, %s, %s, 'apify_reactions')
                   ON CONFLICT DO NOTHING RETURNING id""",
                (h["watched_profile_id"], h["post_id"], h["reaction_type"]),
            )
            if cur.fetchone(): inserted += 1
        conn.commit()
        log.info("Insert: %d nuevos like_events", inserted)
    cur.close(); conn.close()

    log.info("=== Pool status post-run ===")
    for s in status_report():
        log.info("  %s: $%.2f used · $%.2f disp", s.name, s.used_usd, s.available_usd)


if __name__ == "__main__":
    main()
