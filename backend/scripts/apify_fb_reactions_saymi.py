#!/usr/bin/env python3
"""Scrape FB reactions (likers) de los 10 posts FB de Saymi con URL.

Origen: PLAN-2026-05-14-watchlist-saymi.md · Fase 1 Opción B.
Sin tabla `social_reactions` aún → guardamos dump JSON + report inline de matches.

Usage:
    python3 backend/scripts/apify_fb_reactions_saymi.py [--cap 25] [--budget 5]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import psycopg2
import psycopg2.extras
import requests
from apify_client import ApifyClient

# ── Config ─────────────────────────────────────────────────────────────
PROJECT_ROOT = Path("/Users/marxchavez/Projects/crece-v2")
for env_file in [PROJECT_ROOT / ".env", PROJECT_ROOT / "backend/.env.scraping-keys"]:
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

APIFY_TOKEN = os.environ["APIFY_TOKEN"]
DB_DSN = os.environ.get("DB_DSN", "host=localhost port=5438 dbname=crece user=crece password=crece_dev")
HASH_SALT = os.environ.get("COMMENT_AUTHOR_SALT", "crece-v2-lfpdppp-salt-2026")

DIRIGENTE_ID = 3
ACTOR = "scraper_one/facebook-reactions-scraper"

WATCHLIST = [
    (1, "Misael Gómez", "61578398601244", "cliente_seed"),
    (2, "Guadalupe Ibañez", "621614073", "cliente_seed"),
    (3, "Marvin Hilario", "100004319923368", "cliente_seed"),
    (4, "Carlos David", "100001559109790", "cliente_seed"),
    (5, "Adelaida Leyva", "100033760573920", "cliente_seed"),
    (6, "Angel Osorio", "100008056865504", "cliente_seed"),
    (7, "Zuaily Rasgado", "100002291782613", "cliente_seed"),
    (8, "Ana Maldonado", "1651455004", "cliente_seed"),
    (9, "Mariel Villatoro", "600740387", "cliente_seed"),
    (10, "José Cárdenas", "100033470691742", "cliente_seed"),
    (11, "Itzel Cuevas", "1275134998", "cliente_seed"),
    (12, "Alberto Aparicio", "100001153826629", "cliente_seed"),
    (13, "Mueller Ramírez", "100000861757055", "cliente_seed"),
    (14, "Ivette Moran de Murat", "100044541091866", "competidora"),
    (15, "Susana Harpi Turribarría", "100044338034044", "competidora"),
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("fb_reactions")


def get_apify_usage_usd(token: str) -> float:
    r = requests.get(f"https://api.apify.com/v2/users/me/limits?token={token}", timeout=10)
    r.raise_for_status()
    return float(r.json()["data"]["current"].get("monthlyUsageUsd", 0.0))


def hash_fb_user(fb_id: str) -> str:
    return hashlib.sha256(f"FACEBOOK:{fb_id}:{HASH_SALT}".encode()).hexdigest()


def fetch_post_urls() -> list[tuple[int, str]]:
    """Posts FB de Saymi que tienen URL canónica."""
    conn = psycopg2.connect(DB_DSN)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """
        SELECT sp.id AS post_pk, sp.platform_post_id,
               COALESCE(sp.raw_data->>'url', sp.raw_data->>'topLevelUrl') AS url
        FROM social_posts sp JOIN social_profiles spr ON spr.id = sp.profile_id
        WHERE spr.dirigente_id = %s AND spr.platform = 'FACEBOOK'
          AND COALESCE(sp.raw_data->>'url', sp.raw_data->>'topLevelUrl') IS NOT NULL
        ORDER BY sp.published_at DESC
        """,
        (DIRIGENTE_ID,),
    )
    rows = [(r["post_pk"], r["url"]) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cap", type=int, default=25, help="resultsLimit per post (soft).")
    p.add_argument("--budget", type=float, default=5.00, help="Hard-stop USD.")
    args = p.parse_args()

    used_before = get_apify_usage_usd(APIFY_TOKEN)
    log.info("Apify MTD before: $%.4f / cap $%.2f", used_before, args.budget)
    if used_before >= args.budget:
        log.error("BUDGET CAP HIT BEFORE START. Abort.")
        sys.exit(2)

    posts = fetch_post_urls()
    log.info("Posts FB Saymi con URL: %d", len(posts))
    if not posts:
        log.error("No posts to scrape. Abort.")
        sys.exit(2)

    urls = [u for _, u in posts]
    url_to_post_pk = {u: pk for pk, u in posts}

    # Pre-hash watchlist
    wl_hashes = {hash_fb_user(fb_id): (no, name, tipo) for no, name, fb_id, tipo in WATCHLIST}
    log.info("Watchlist pre-hashed: %d perfiles", len(wl_hashes))

    apify = ApifyClient(APIFY_TOKEN)
    BATCH_SIZE = 5  # actor hard-limit en free tier
    batches = [urls[i:i + BATCH_SIZE] for i in range(0, len(urls), BATCH_SIZE)]
    log.info("Calling %s · cap=%d · %d URLs en %d batches de %d",
             ACTOR, args.cap, len(urls), len(batches), BATCH_SIZE)

    items: list[dict] = []
    cost = 0.0
    for bi, batch in enumerate(batches, 1):
        log.info("Batch %d/%d (%d URLs)", bi, len(batches), len(batch))
        t0 = time.time()
        run = apify.actor(ACTOR).call(
            run_input={"postUrls": batch, "resultsLimit": args.cap},
            timeout_secs=900,
        )
        elapsed = time.time() - t0
        bcost = float(run.get("usageTotalUsd") or 0.0)
        cost += bcost
        log.info("  done in %.1fs · cost=$%.4f · status=%s", elapsed, bcost, run["status"])
        items.extend(apify.dataset(run["defaultDatasetId"]).iterate_items())

    log.info("Reactions items recibidos total: %d · cost total=$%.4f", len(items), cost)

    # Match contra watchlist
    matches = []
    by_post: dict[str, list[dict]] = {}
    by_type: dict[str, int] = {}
    for it in items:
        rid = str(it.get("reactorId") or "")
        rtype = it.get("reactionType") or "?"
        rurl = it.get("postUrl") or ""
        by_type[rtype] = by_type.get(rtype, 0) + 1
        by_post.setdefault(rurl, []).append({
            "reactor_id": rid,
            "reactor_name": it.get("reactorName"),
            "reaction_type": rtype,
        })
        ah = hash_fb_user(rid)
        if ah in wl_hashes:
            no, name, tipo = wl_hashes[ah]
            matches.append({
                "no": no, "name": name, "tipo": tipo,
                "reactorName": it.get("reactorName"),
                "reactionType": rtype,
                "postUrl": rurl,
            })
            log.info("🎯 MATCH: #%d %s (%s) → %s", no, name, tipo, rtype)

    # Dump completo
    out_path = PROJECT_ROOT / ".context" / f"apify-fb-reactions-saymi-{datetime.now(UTC).strftime('%Y%m%d-%H%M')}.json"
    out_path.write_text(json.dumps({
        "ran_at": datetime.now(UTC).isoformat(),
        "actor": ACTOR,
        "cap": args.cap,
        "cost_usd": cost,
        "items_received": len(items),
        "by_post_count": {url: len(reacts) for url, reacts in by_post.items()},
        "by_reaction_type": by_type,
        "matches_watchlist": matches,
        "all_reactors": [
            {"reactor_id": it.get("reactorId"), "reactor_name": it.get("reactorName"),
             "reaction_type": it.get("reactionType"), "post_url": it.get("postUrl")}
            for it in items
        ],
    }, indent=2, ensure_ascii=False))
    log.info("Dump saved: %s", out_path)

    used_after = get_apify_usage_usd(APIFY_TOKEN)
    log.info("=== DONE · matches=%d/15 · items=%d · cost=$%.4f · MTD now=$%.4f ===",
             len(matches), len(items), cost, used_after)


if __name__ == "__main__":
    main()
