"""Ingest Facebook posts for CRECE dirigentes via Bright Data Dataset API.

Dataset: Facebook Pages Posts by Profile URL (gd_lkaxegm826bjpoo9m5)
API key: BRIGHTDATA_API_KEY_FB from backend/.env.scraping-keys

Pipeline:
  1. POST to /datasets/v3/scrape with profile URLs → snapshot_id
  2. Poll /datasets/v3/progress/<snapshot_id> until ready
  3. GET /datasets/v3/snapshot/<snapshot_id> → list of post dicts
  4. Insert new rows into social_posts (dedup by platform_post_id)
  5. Write /tmp/crece_fb_post_urls.json for downstream comments ingestion

Output JSON schema from Bright Data (observed fields):
  post_id, post_url, text, timestamp, likes, comments, shares, views,
  page_name, page_url, post_type (photo/video/text/reel), image_url

Usage:
  python brightdata_fb_posts.py [--dry-run]
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

# ── Config ────────────────────────────────────────────────────────────────────

ENV_FILE = Path(__file__).parent.parent / ".env.scraping-keys"
for line in ENV_FILE.read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

API_KEY = os.environ.get("BRIGHTDATA_API_KEY_FB") or os.environ.get("BRIGHTDATA_API_KEY")
if not API_KEY:
    sys.exit("BRIGHTDATA_API_KEY_FB not set in backend/.env.scraping-keys")

DATASET_ID = "gd_lkaxegm826bjpoo9m5"
DB_DSN = os.environ.get(
    "DB_DSN", "host=localhost port=5438 dbname=crece user=crece password=crece_dev"
)
POST_URLS_OUT = Path("/tmp/crece_fb_post_urls.json")

# dirigente_id → Facebook profile URL
TARGETS = [
    {"dirigente_id": 1, "url": "https://www.facebook.com/alejandropinamedina/"},
    {"dirigente_id": 3, "url": "https://www.facebook.com/saymipinedavelasco/"},
    {"dirigente_id": 5, "url": "https://www.facebook.com/GabyJimenezGo/"},
    {"dirigente_id": 8, "url": "https://www.facebook.com/LauraBallesterosMX/"},
]

DRY_RUN = "--dry-run" in sys.argv

# ── Bright Data helpers ───────────────────────────────────────────────────────

def _headers() -> dict:
    return {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def trigger_scrape(profile_urls: list[str], num_posts: int = 30) -> str:
    payload = [
        {"url": u, "num_of_posts": num_posts, "start_date": "", "end_date": ""}
        for u in profile_urls
    ]
    # Use async /trigger — returns snapshot_id immediately, poll separately
    r = requests.post(
        f"https://api.brightdata.com/datasets/v3/trigger"
        f"?dataset_id={DATASET_ID}&include_errors=true",
        headers=_headers(),
        json=payload,
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()
    snapshot_id = data.get("snapshot_id") or data.get("id")
    if not snapshot_id:
        sys.exit(f"No snapshot_id in response: {data}")
    return snapshot_id


def wait_ready(snapshot_id: str, max_wait: int = 600) -> bool:
    t0 = time.time()
    while time.time() - t0 < max_wait:
        r = requests.get(
            f"https://api.brightdata.com/datasets/v3/progress/{snapshot_id}",
            headers=_headers(),
            timeout=30,
        )
        status = r.json().get("status", "")
        print(f"  [{int(time.time()-t0)}s] status={status}", flush=True)
        if status == "ready":
            return True
        if status in {"failed", "canceled"}:
            print(f"  snapshot {status}", flush=True)
            return False
        time.sleep(10)
    return False


def download_snapshot(snapshot_id: str) -> list[dict]:
    r = requests.get(
        f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}?format=json",
        headers=_headers(),
        timeout=120,
    )
    r.raise_for_status()
    data = r.json()
    return data if isinstance(data, list) else data.get("data", [])


# ── DB helpers ────────────────────────────────────────────────────────────────

def get_profile_id(conn, dirigente_id: int) -> int | None:
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM social_profiles WHERE dirigente_id=%s AND platform='FACEBOOK'",
        (dirigente_id,),
    )
    row = cur.fetchone()
    cur.close()
    return row[0] if row else None


def _parse_published_at(raw) -> datetime:
    if not raw:
        return datetime.now(timezone.utc)
    if isinstance(raw, (int, float)):
        return datetime.fromtimestamp(raw, tz=timezone.utc)
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except Exception:
        return datetime.now(timezone.utc)


def _post_type(row: dict) -> str:
    pt = (row.get("post_type") or "").lower()
    if "video" in pt or "reel" in pt:
        return "VIDEO"
    if "photo" in pt or "image" in pt:
        return "IMAGE"
    return "TEXT"


def insert_posts(conn, profile_id: int, rows: list[dict]) -> tuple[int, int]:
    cur = conn.cursor()
    inserted = 0
    skipped = 0
    for row in rows:
        post_id = str(row.get("post_id") or "").strip()
        if not post_id:
            # Generate a stable ID from URL or content hash
            url = row.get("post_url") or row.get("url") or ""
            content = row.get("text") or row.get("content") or ""
            raw = f"{url}|{content[:200]}"
            post_id = "fb_" + hashlib.sha256(raw.encode()).hexdigest()[:20]

        cur.execute(
            "SELECT id FROM social_posts WHERE platform_post_id=%s", (post_id,)
        )
        if cur.fetchone():
            skipped += 1
            continue

        content = (row.get("text") or row.get("content") or "").strip()
        published_at = _parse_published_at(
            row.get("timestamp") or row.get("date_posted") or row.get("published_at")
        )
        likes = int(row.get("likes") or row.get("reactions") or 0)
        comments_count = int(row.get("comments") or row.get("comments_count") or 0)
        shares = int(row.get("shares") or 0)
        views = int(row.get("views") or row.get("video_views") or 0)
        now = datetime.now(timezone.utc)

        try:
            cur.execute(
                """
                INSERT INTO social_posts
                    (profile_id, platform_post_id, content, post_type, published_at,
                     likes, comments, shares, views, engagement_rate,
                     is_political, scraped_at, raw_data)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,0,false,%s,%s)
                """,
                (
                    profile_id,
                    post_id,
                    content[:10_000],
                    _post_type(row),
                    published_at,
                    likes,
                    comments_count,
                    shares,
                    views,
                    now,
                    json.dumps({
                        "source": "brightdata-fb-posts-v1",
                        "post_url": row.get("post_url") or "",
                        "scraped_at": now.isoformat(),
                    }),
                ),
            )
            inserted += 1
        except Exception as e:
            skipped += 1
            print(f"  insert error post_id={post_id}: {e}", flush=True)

    conn.commit()
    cur.close()
    return inserted, skipped


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    profile_urls = [t["url"] for t in TARGETS]
    url_to_dirigente = {t["url"].rstrip("/"): t["dirigente_id"] for t in TARGETS}

    print(f"=== Facebook Posts Ingestion (dry_run={DRY_RUN}) ===")
    print(f"Targets: {profile_urls}")

    if DRY_RUN:
        print("[dry-run] would trigger scrape — exiting")
        return

    print("\n[1/3] Triggering scrape...", flush=True)
    snap = trigger_scrape(profile_urls, num_posts=30)
    print(f"  snapshot_id: {snap}", flush=True)

    print("\n[2/3] Waiting for snapshot...", flush=True)
    if not wait_ready(snap):
        sys.exit(f"Snapshot {snap} timed out or failed")

    print("\n[3/3] Downloading + inserting posts...", flush=True)
    rows = download_snapshot(snap)
    print(f"  downloaded {len(rows)} rows", flush=True)

    conn = psycopg2.connect(DB_DSN)
    conn.autocommit = False

    # Group rows by page_url to map back to dirigente_id
    post_urls_for_comments: list[dict] = []
    total_inserted = total_skipped = 0

    for target in TARGETS:
        t_url = target["url"].rstrip("/")
        dirigente_id = target["dirigente_id"]
        profile_id = get_profile_id(conn, dirigente_id)
        if not profile_id:
            print(f"  WARNING: no FB profile for dirigente_id={dirigente_id} — skipping")
            continue

        # Filter rows for this profile
        profile_rows = [
            r for r in rows
            if (r.get("page_url") or r.get("profile_url") or "").rstrip("/") == t_url
            or (r.get("page_name") or "").lower() in t_url.lower()
        ]

        if not profile_rows:
            # If we can't match by URL, assign all rows proportionally
            # (single-profile scrape returns no page_url sometimes)
            if len(TARGETS) == 1:
                profile_rows = rows

        print(f"\n  dirigente_id={dirigente_id} → {len(profile_rows)} posts", flush=True)
        ins, skp = insert_posts(conn, profile_id, profile_rows)
        print(f"    inserted={ins} skipped={skp}", flush=True)
        total_inserted += ins
        total_skipped += skp

        # Collect post URLs for comments ingestion
        for r in profile_rows:
            post_url = r.get("post_url") or r.get("url") or ""
            if post_url and "facebook.com" in post_url:
                post_urls_for_comments.append({
                    "dirigente_id": dirigente_id,
                    "url": post_url,
                    "post_id": r.get("post_id", ""),
                })

    conn.close()

    # Write post URLs for comments script
    POST_URLS_OUT.write_text(json.dumps(post_urls_for_comments, indent=2, ensure_ascii=False))
    print(f"\n  post_urls written: {POST_URLS_OUT} ({len(post_urls_for_comments)} URLs)")

    print(f"\n=== DONE: inserted={total_inserted} skipped={total_skipped} ===")
    print(f"\nNext step — run comments ingestion:")
    print(f"  python brightdata_fb_comments_from_posts.py {POST_URLS_OUT}")


if __name__ == "__main__":
    main()
