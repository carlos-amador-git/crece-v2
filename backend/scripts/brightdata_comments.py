"""Brightdata-based scraper for social comments → social_comments table.

Uses Brightdata's dataset IDs (no bot detection from Docker):
- TikTok Comments: gd_lkf2st302ap89utw5k
- Facebook Comments: gd_lkay758p1eanlolqw8
- Instagram Comments: gd_ltppn085pokosxh13
- YouTube Comments: gd_lk9q0ew71spt1mxywf

Stores comments with author_hash (SHA256) for LFPDPPP compliance.
Raw author_id is NEVER persisted.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
import requests

# Load keys
ENV_FILE = Path(__file__).parent.parent / ".env.scraping-keys"
for line in ENV_FILE.read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

API_KEY = os.environ["BRIGHTDATA_API_KEY"]
DB_DSN = os.environ.get("DB_DSN", "host=localhost port=5438 dbname=crece user=crece password=crece_dev")

DATASETS = {
    "TIKTOK": "gd_lkf2st302ap89utw5k",
    "FACEBOOK": "gd_lkay758p1eanlolqw8",
    "INSTAGRAM": "gd_ltppn085pokosxh13",
    "YOUTUBE": "gd_lk9q0ew71spt1mxywf",
}

HASH_SALT = os.environ.get("COMMENT_AUTHOR_SALT")
if not HASH_SALT:
    raise RuntimeError(
        "COMMENT_AUTHOR_SALT env var obligatoria — sin fallback hardcoded por seguridad LFPDPPP. "
        "Definir en .env.scraping-keys o pasar explícito."
    )


def author_hash(platform: str, commenter_id: str | None) -> str:
    raw = f"{platform}:{commenter_id or 'anon'}:{HASH_SALT}"
    return hashlib.sha256(raw.encode()).hexdigest()


def trigger_scrape(platform: str, urls: list[str]) -> str:
    dataset_id = DATASETS[platform]
    r = requests.post(
        f"https://api.brightdata.com/datasets/v3/trigger?dataset_id={dataset_id}&include_errors=true",
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        json=[{"url": u} for u in urls],
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["snapshot_id"]


def wait_ready(snapshot_id: str, max_wait: int = 600) -> bool:
    t0 = time.time()
    while time.time() - t0 < max_wait:
        r = requests.get(
            f"https://api.brightdata.com/datasets/v3/progress/{snapshot_id}",
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=30,
        )
        status = r.json().get("status")
        if status == "ready":
            return True
        if status in {"failed", "canceled"}:
            print(f"  ⚠️ snapshot failed: {status}")
            return False
        time.sleep(8)
    return False


def download_snapshot(snapshot_id: str) -> list[dict]:
    r = requests.get(
        f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}?format=json",
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


def insert_comments(rows: list[dict], platform: str) -> tuple[int, int]:
    conn = psycopg2.connect(DB_DSN)
    conn.autocommit = False
    cur = conn.cursor()

    post_id_map = {}  # platform_post_id -> social_posts.id
    for row in rows:
        ppid = str(row.get("post_id") or "").strip()
        if ppid and ppid not in post_id_map:
            cur.execute("SELECT id FROM social_posts WHERE platform_post_id = %s", (ppid,))
            r = cur.fetchone()
            if r:
                post_id_map[ppid] = r[0]

    inserted = 0
    skipped = 0
    for row in rows:
        ppid = str(row.get("post_id") or "").strip()
        parent_db_id = post_id_map.get(ppid)
        if not parent_db_id:
            skipped += 1
            continue

        content = row.get("comment_text") or row.get("text") or ""
        if not content:
            skipped += 1
            continue

        comment_id = str(row.get("comment_id") or row.get("id") or f"auto-{inserted}")
        commenter_id = row.get("commenter_id") or row.get("author_id") or row.get("user_id")
        ah = author_hash(platform, str(commenter_id) if commenter_id else None)

        likes = int(row.get("num_likes") or row.get("likes_count") or 0)
        pub_raw = row.get("date_created") or row.get("comment_date") or row.get("published_at")
        try:
            published_at = datetime.fromisoformat(pub_raw.replace("Z", "+00:00")) if pub_raw else None
        except Exception:
            published_at = None

        try:
            cur.execute(
                """
                INSERT INTO social_comments
                    (parent_post_id, platform_comment_id, content, author_hash,
                     likes, published_at, is_reply_to_comment)
                VALUES (%s, %s, %s, %s, %s, %s, false)
                ON CONFLICT (platform_comment_id) DO UPDATE SET likes = EXCLUDED.likes
                """,
                (parent_db_id, comment_id, content[:5000], ah, likes, published_at),
            )
            inserted += 1
        except Exception as e:
            skipped += 1
            print(f"  skip: {e}")

    conn.commit()
    cur.close()
    conn.close()
    return inserted, skipped


def scrape_platform(platform: str, urls: list[str]) -> dict:
    print(f"\n=== {platform} — {len(urls)} URLs ===")
    snap = trigger_scrape(platform, urls)
    print(f"  snapshot: {snap}")
    if not wait_ready(snap):
        return {"inserted": 0, "snapshot": snap, "status": "timeout"}
    rows = download_snapshot(snap)
    print(f"  rows downloaded: {len(rows)}")
    inserted, skipped = insert_comments(rows, platform)
    print(f"  inserted: {inserted} · skipped: {skipped}")
    return {"inserted": inserted, "skipped": skipped, "snapshot": snap, "status": "ok"}


if __name__ == "__main__":
    platform = sys.argv[1] if len(sys.argv) > 1 else "TIKTOK"
    urls = sys.argv[2:]
    if not urls:
        print("Usage: brightdata_comments.py TIKTOK|FACEBOOK|INSTAGRAM|YOUTUBE <url1> [url2...]")
        sys.exit(1)
    result = scrape_platform(platform, urls)
    print(f"\n{json.dumps(result, indent=2)}")
