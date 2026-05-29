#!/usr/bin/env python3
"""Re-scrape comments FB de Saymi (dirigente_id=3) con profundidad completa.

Origen: PLAN-2026-05-14-watchlist-saymi.md · Sprint Fase 1.
El refresh general (apify_refresh_all.py) capó comments FB a 5/post; aquí
levantamos el cap a 200 + replies anidadas para responder la pregunta de
la Lic. Saymi (¿cómo participan estos 13 perfiles?).

Idempotente: UPSERT por platform_comment_id (constraint único).

Usage:
    python3 backend/scripts/apify_fb_deep_saymi.py [--dry-run] [--budget-cap 1.50]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import psycopg2
import psycopg2.extras
import requests
from apify_client import ApifyClient

# ── Cargar .env (mismo patrón que apify_refresh_all.py) ───────────────
PROJECT_ROOT = Path("/Users/marxchavez/Projects/crece-v2")
for env_file in [PROJECT_ROOT / ".env", PROJECT_ROOT / "backend/.env.scraping-keys"]:
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

APIFY_TOKEN = os.environ["APIFY_TOKEN"]
DB_DSN = os.environ.get(
    "DB_DSN",
    "host=localhost port=5438 dbname=crece user=crece password=crece_dev",
)
HASH_SALT = os.environ.get("COMMENT_AUTHOR_SALT", "crece-v2-lfpdppp-salt-2026")

DIRIGENTE_ID = 3  # Saymi Adriana Pineda Velasco
ACTOR_FB_COMMENTS = "apify/facebook-comments-scraper"
DATA_SOURCE = "apify-fb-deep-2026-05-14"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("fb_deep")


def get_apify_usage_usd(token: str) -> float:
    r = requests.get(f"https://api.apify.com/v2/users/me/limits?token={token}", timeout=10)
    r.raise_for_status()
    return float(r.json()["data"]["current"].get("monthlyUsageUsd", 0.0))


def fetch_saymi_fb_posts(conn, since_date: str | None = None) -> list[dict]:
    """URLs canónicas de los posts FB ya capturados de Saymi.

    Si since_date está set (formato YYYY-MM-DD), solo trae posts publicados
    a partir de esa fecha — útil para procesar solo nuevos sin re-spending
    en posts ya cubiertos.
    """
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    where_extra = "AND sp.published_at >= %(since)s::timestamptz" if since_date else ""
    cur.execute(
        f"""
        SELECT sp.id AS post_pk,
               sp.platform_post_id,
               sp.published_at,
               sp.comments AS comments_segun_fb,
               COALESCE(sp.raw_data->>'url',
                        sp.raw_data->>'topLevelUrl',
                        sp.raw_data->>'facebookUrl') AS post_url
        FROM social_posts sp
        JOIN social_profiles spr ON spr.id = sp.profile_id
        WHERE spr.dirigente_id = %(did)s AND spr.platform = 'FACEBOOK'
          {where_extra}
        ORDER BY sp.published_at DESC
        """,
        {"did": DIRIGENTE_ID, "since": since_date},
    )
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    return rows


def author_hash(platform: str, author_id: str | None, fallback: str = "") -> str:
    raw = f"{platform}:{author_id or fallback}:{HASH_SALT}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def parse_date(value):
    if not value:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=UTC)
    if isinstance(value, str):
        # ISO 8601
        for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(value.replace("Z", ""), fmt.replace("Z", "")).replace(tzinfo=UTC)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def upsert_comment(conn, parent_post_id: int, raw: dict) -> bool:
    """UPSERT social_comments. Devuelve True si insertó/actualizó."""
    pcid = str(raw.get("commentId") or raw.get("id") or "").strip()
    text = (raw.get("text") or "").strip()
    if not pcid or not text:
        return False

    author_id = (
        raw.get("profileId")
        or raw.get("profileUrl")
        or (raw.get("user") or {}).get("id")
    )
    ah = author_hash("FACEBOOK", author_id, fallback=pcid)
    pub = parse_date(raw.get("date") or raw.get("publishedTime"))
    is_reply = bool(raw.get("commentId") and raw.get("parentId"))

    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO social_comments
            (parent_post_id, platform_comment_id, content, author_hash,
             likes, published_at, is_reply_to_comment, data_source)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (platform_comment_id) DO UPDATE SET
            likes        = EXCLUDED.likes,
            content      = EXCLUDED.content,
            author_hash  = EXCLUDED.author_hash,
            published_at = COALESCE(EXCLUDED.published_at, social_comments.published_at),
            data_source  = EXCLUDED.data_source,
            updated_at   = now()
        """,
        (
            parent_post_id,
            pcid,
            text[:5000],
            ah,
            int(raw.get("likesCount") or raw.get("likes") or 0),
            pub,
            is_reply,
            DATA_SOURCE,
        ),
    )
    cur.close()
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="No inserta, solo lista cuántos comments capturaríamos.")
    parser.add_argument("--budget-cap", type=float, default=1.50,
                        help="Hard-stop si Apify usage MTD excede esto (USD).")
    parser.add_argument("--limit-per-post", type=int, default=200,
                        help="Cap comments por post (vs 5 del refresh general).")
    parser.add_argument("--since-date", type=str, default=None,
                        help="Solo procesar posts publicados >= esta fecha (YYYY-MM-DD).")
    args = parser.parse_args()

    log.info("=== Apify FB DEEP scrape · Saymi (dirigente_id=%d) ===", DIRIGENTE_ID)
    used_before = get_apify_usage_usd(APIFY_TOKEN)
    log.info("Apify usage MTD before: $%.4f / cap $%.2f", used_before, args.budget_cap)
    if used_before >= args.budget_cap:
        log.error("BUDGET CAP HIT BEFORE START. Aborting.")
        sys.exit(2)

    conn = psycopg2.connect(DB_DSN)
    posts = fetch_saymi_fb_posts(conn, since_date=args.since_date)
    log.info("Saymi FB posts en BD: %d (suma comments segun FB: %d)",
             len(posts), sum(p["comments_segun_fb"] or 0 for p in posts))

    urls = [p["post_url"] for p in posts if p["post_url"]]
    if not urls:
        log.error("Sin URLs en raw_data. Abort.")
        sys.exit(2)
    log.info("URLs útiles: %d", len(urls))

    url_to_post_pk = {p["post_url"]: p["post_pk"] for p in posts if p["post_url"]}

    if args.dry_run:
        log.info("DRY-RUN: would call %s with %d URLs, limit=%d, includeNested=true",
                 ACTOR_FB_COMMENTS, len(urls), args.limit_per_post)
        log.info("Top 5 URLs sample:")
        for u in urls[:5]:
            log.info("  - %s", u)
        conn.close()
        return

    apify = ApifyClient(APIFY_TOKEN)
    run_input = {
        "startUrls": [{"url": u} for u in urls],
        "resultsLimit": args.limit_per_post,
        "includeNestedComments": True,
        "viewOption": "RANKED_THREADED",
    }
    log.info("Calling Apify actor=%s · resultsLimit=%d · nested=True",
             ACTOR_FB_COMMENTS, args.limit_per_post)
    run = apify.actor(ACTOR_FB_COMMENTS).call(run_input=run_input, timeout_secs=900)
    if not run:
        log.error("Apify run failed (None). Abort.")
        sys.exit(3)
    cost = float(run.get("usageTotalUsd") or 0.0)
    log.info("Apify run done · cost=$%.4f · datasetId=%s", cost, run["defaultDatasetId"])

    items = list(apify.dataset(run["defaultDatasetId"]).iterate_items())
    log.info("Comments items recibidos del actor: %d", len(items))

    n_inserted = 0
    n_skipped_no_post = 0
    for raw in items:
        purl = (raw.get("inputUrl") or raw.get("facebookUrl") or "").strip()
        post_pk = url_to_post_pk.get(purl) or url_to_post_pk.get(purl.rstrip("/"))
        if not post_pk:
            n_skipped_no_post += 1
            continue
        if upsert_comment(conn, post_pk, raw):
            n_inserted += 1

    conn.commit()
    conn.close()

    used_after = get_apify_usage_usd(APIFY_TOKEN)
    log.info("=== DONE · inserted/upserted=%d · skipped(no_post_match)=%d · cost=$%.4f · MTD now=$%.4f ===",
             n_inserted, n_skipped_no_post, cost, used_after)


if __name__ == "__main__":
    main()
