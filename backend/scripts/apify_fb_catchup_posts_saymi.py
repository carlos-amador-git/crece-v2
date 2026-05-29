#!/usr/bin/env python3
"""Catchup posts FB de Saymi desde 2026-05-08 hasta hoy.

Llama apify/facebook-posts-scraper con resultsLimit alto para traer todos los
posts nuevos. UPSERT en social_posts (constraint UNIQUE platform_post_id).
Reusa funciones del refresh general.

Usage:
    python3 backend/scripts/apify_fb_catchup_posts_saymi.py [--limit 30] [--budget 1.00]
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg2
import requests
from apify_client import ApifyClient

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

DIRIGENTE_ID = 3
SAYMI_FB_HANDLE = "saymipinedavelasco"
SAYMI_FB_PROFILE_ID = 27  # social_profiles.id (visto en audit anterior)
ACTOR = "apify/facebook-posts-scraper"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("fb_catchup")


def get_apify_usage_usd(token: str) -> float:
    r = requests.get(f"https://api.apify.com/v2/users/me/limits?token={token}", timeout=10)
    r.raise_for_status()
    return float(r.json()["data"]["current"].get("monthlyUsageUsd", 0.0))


def parse_date(value):
    if not value:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=UTC)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=30, help="resultsLimit posts (max).")
    p.add_argument("--budget", type=float, default=1.00, help="Hard-stop USD.")
    args = p.parse_args()

    used_before = get_apify_usage_usd(APIFY_TOKEN)
    log.info("Apify MTD before: $%.4f / cap $%.2f", used_before, args.budget)
    if used_before >= args.budget:
        log.error("BUDGET CAP HIT BEFORE START. Abort.")
        sys.exit(2)

    apify = ApifyClient(APIFY_TOKEN)
    fb_url = f"https://www.facebook.com/{SAYMI_FB_HANDLE}"
    run_input = {
        "startUrls": [{"url": fb_url}],
        "resultsLimit": args.limit,
        "captionText": False,
    }
    log.info("Calling %s · cap=%d · url=%s", ACTOR, args.limit, fb_url)
    t0 = time.time()
    run = apify.actor(ACTOR).call(run_input=run_input, timeout_secs=300)
    cost = float(run.get("usageTotalUsd") or 0.0)
    log.info("Run done in %.1fs · cost=$%.4f · status=%s", time.time()-t0, cost, run["status"])

    items = list(apify.dataset(run["defaultDatasetId"]).iterate_items())
    log.info("Posts items recibidos: %d", len(items))

    conn = psycopg2.connect(DB_DSN)
    cur = conn.cursor()
    n_new, n_updated = 0, 0
    cutoff = datetime(2026, 5, 8, tzinfo=UTC)

    for raw in items:
        ppid = str(raw.get("postId") or "").strip()
        if not ppid:
            continue
        pub = parse_date(raw.get("time") or raw.get("timestamp"))
        if not pub or pub < cutoff:
            continue

        text = raw.get("text") or ""
        likes = int(raw.get("likes") or 0)
        comments_cnt = int(raw.get("comments") or 0)
        shares = int(raw.get("shares") or 0)
        post_url = raw.get("url") or raw.get("topLevelUrl") or raw.get("facebookUrl") or ""
        post_type = "VIDEO" if (raw.get("media") and any("video" in str(m).lower() for m in raw.get("media", []))) else "TEXT"

        # Check si ya existe
        cur.execute("SELECT id FROM social_posts WHERE platform_post_id = %s", (ppid,))
        existing = cur.fetchone()

        raw_data = {
            "postId": ppid,
            "url": post_url,
            "facebookUrl": raw.get("facebookUrl") or "",
            "topLevelUrl": raw.get("topLevelUrl") or "",
            "data_source": "apify-fb-catchup-2026-05-14",
        }

        if existing:
            cur.execute(
                """
                UPDATE social_posts
                SET likes = %s, comments = %s, shares = %s,
                    raw_data = %s, scraped_at = now(),
                    content = COALESCE(NULLIF(%s,''), content)
                WHERE id = %s
                """,
                (likes, comments_cnt, shares, json.dumps(raw_data), text, existing[0]),
            )
            n_updated += 1
        else:
            cur.execute(
                """
                INSERT INTO social_posts
                  (profile_id, platform_post_id, content, post_type, published_at,
                   likes, comments, shares, views, engagement_rate, is_political,
                   raw_data, scraped_at, clasificacion_origen)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0, 0.0, false, %s, now(), 'ai_suggested')
                """,
                (SAYMI_FB_PROFILE_ID, ppid, text, post_type, pub, likes, comments_cnt, shares,
                 json.dumps(raw_data)),
            )
            n_new += 1

    conn.commit()
    conn.close()

    used_after = get_apify_usage_usd(APIFY_TOKEN)
    log.info("=== DONE · new=%d · updated=%d · cost=$%.4f · MTD now=$%.4f ===",
             n_new, n_updated, cost, used_after)


if __name__ == "__main__":
    main()
