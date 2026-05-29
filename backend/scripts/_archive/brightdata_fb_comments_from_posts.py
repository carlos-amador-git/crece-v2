"""Ingest Facebook comments for CRECE posts via Bright Data Dataset API.

Dataset: Facebook Post Comments (gd_lkay758p1eanlolqw8)
Input:   /tmp/crece_fb_post_urls.json  (written by brightdata_fb_posts.py)
         OR pass path as first CLI arg.

Usage:
  python brightdata_fb_comments_from_posts.py [post_urls.json] [--dry-run]
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

DATASET_ID = "gd_lkay758p1eanlolqw8"  # Facebook Post Comments
DB_DSN = os.environ.get(
    "DB_DSN", "host=localhost port=5438 dbname=crece user=crece password=crece_dev"
)

POST_URLS_FILE = Path(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else Path("/tmp/crece_fb_post_urls.json")
DRY_RUN = "--dry-run" in sys.argv

BATCH_SIZE = 20   # Bright Data recommends ≤50 URLs per trigger
MAX_COMMENTS_PER_POST = 20

# ── Bright Data helpers ───────────────────────────────────────────────────────

def _headers() -> dict:
    return {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def trigger_scrape(post_urls: list[str]) -> str:
    payload = [{"url": u} for u in post_urls]
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

def get_post_id_by_url(conn, post_url: str) -> int | None:
    """Resolve social_posts.id from raw_data->post_url or platform_post_id."""
    cur = conn.cursor()
    # Try matching via raw_data JSON field
    cur.execute(
        "SELECT id FROM social_posts WHERE raw_data->>'post_url' = %s LIMIT 1",
        (post_url,),
    )
    row = cur.fetchone()
    cur.close()
    return row[0] if row else None


def _parse_dt(raw) -> datetime:
    if not raw:
        return datetime.now(timezone.utc)
    if isinstance(raw, (int, float)):
        return datetime.fromtimestamp(raw, tz=timezone.utc)
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except Exception:
        return datetime.now(timezone.utc)


def insert_comments(conn, post_db_id: int, comments: list[dict]) -> tuple[int, int]:
    cur = conn.cursor()

    # Ensure post_comments table exists (simple check)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS post_comments (
            id                SERIAL PRIMARY KEY,
            post_id           INTEGER NOT NULL REFERENCES social_posts(id) ON DELETE CASCADE,
            platform_comment_id TEXT,
            author_hash       TEXT,
            content           TEXT,
            likes             INTEGER NOT NULL DEFAULT 0,
            published_at      TIMESTAMPTZ,
            scraped_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            raw_data          JSONB,
            UNIQUE (post_id, platform_comment_id)
        )
    """)

    inserted = skipped = 0
    now = datetime.now(timezone.utc)

    for c in comments:
        raw_id = str(c.get("comment_id") or c.get("id") or "").strip()
        content = (c.get("comment") or c.get("text") or c.get("content") or "").strip()
        if not content:
            skipped += 1
            continue

        if not raw_id:
            raw_id = "fbc_" + hashlib.sha256(f"{post_db_id}|{content[:200]}".encode()).hexdigest()[:20]

        # Author hash for LFPDPPP compliance
        author_raw = str(c.get("author_id") or c.get("user_id") or c.get("author") or "anon")
        salt = os.environ.get("COMMENT_AUTHOR_SALT", "crece-v2-salt")
        author_hash = hashlib.sha256(f"{salt}|{author_raw}".encode()).hexdigest()[:32]

        try:
            cur.execute(
                """
                INSERT INTO post_comments
                    (post_id, platform_comment_id, author_hash, content, likes, published_at, scraped_at, raw_data)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (post_id, platform_comment_id) DO NOTHING
                """,
                (
                    post_db_id,
                    raw_id,
                    author_hash,
                    content[:5000],
                    int(c.get("likes") or c.get("reactions") or 0),
                    _parse_dt(c.get("timestamp") or c.get("date") or c.get("published_at")),
                    now,
                    json.dumps({
                        "source": "brightdata-fb-comments-v1",
                        "scraped_at": now.isoformat(),
                    }),
                ),
            )
            inserted += 1
        except Exception as e:
            skipped += 1
            print(f"    insert error comment_id={raw_id}: {e}", flush=True)

    conn.commit()
    cur.close()
    return inserted, skipped


# ── Main ──────────────────────────────────────────────────────────────────────

def get_post_id_by_platform_id(conn, platform_post_id: str) -> int | None:
    """Resolve social_posts.id from platform_post_id (numeric FB post ID)."""
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM social_posts WHERE platform_post_id=%s LIMIT 1",
        (platform_post_id,),
    )
    row = cur.fetchone()
    cur.close()
    return row[0] if row else None


def main() -> None:
    if not POST_URLS_FILE.exists():
        sys.exit(f"Post URLs file not found: {POST_URLS_FILE}")

    targets: list[dict] = json.loads(POST_URLS_FILE.read_text())
    # Build map: url → platform_post_id for fast lookup
    url_to_post_id: dict[str, str] = {
        t["url"].rstrip("/"): str(t.get("post_id", ""))
        for t in targets if t.get("url")
    }
    post_urls = list(url_to_post_id.keys())

    print(f"=== Facebook Comments Ingestion (dry_run={DRY_RUN}) ===")
    print(f"Post URLs to scrape: {len(post_urls)}")

    if DRY_RUN:
        print("[dry-run] would trigger scrape — exiting")
        return

    conn = psycopg2.connect(DB_DSN)
    conn.autocommit = False

    total_inserted = total_skipped = 0

    # Process in batches to stay within Bright Data limits
    for batch_start in range(0, len(post_urls), BATCH_SIZE):
        batch = post_urls[batch_start:batch_start + BATCH_SIZE]
        batch_num = batch_start // BATCH_SIZE + 1
        total_batches = (len(post_urls) + BATCH_SIZE - 1) // BATCH_SIZE

        print(f"\n[Batch {batch_num}/{total_batches}] Triggering {len(batch)} URLs...", flush=True)
        snap = trigger_scrape(batch)
        print(f"  snapshot_id: {snap}", flush=True)

        print(f"  Waiting for snapshot...", flush=True)
        if not wait_ready(snap):
            print(f"  WARNING: snapshot {snap} timed out — skipping batch", flush=True)
            continue

        rows = download_snapshot(snap)
        print(f"  downloaded {len(rows)} comment rows", flush=True)

        # Group comments by post_url
        comments_by_url: dict[str, list[dict]] = {}
        for row in rows:
            url = (row.get("post_url") or row.get("url") or "").rstrip("/")
            if url:
                comments_by_url.setdefault(url, []).append(row)

        for post_url in batch:
            clean_url = post_url.rstrip("/")
            comments = comments_by_url.get(clean_url, [])
            if not comments:
                print(f"    {clean_url}: 0 comments", flush=True)
                continue

            # Try 1: match by raw_data post_url
            post_db_id = get_post_id_by_url(conn, post_url)
            if not post_db_id:
                post_db_id = get_post_id_by_url(conn, clean_url)
            # Try 2: match by numeric platform_post_id from the targets JSON
            if not post_db_id:
                platform_id = url_to_post_id.get(clean_url, "")
                if platform_id:
                    post_db_id = get_post_id_by_platform_id(conn, platform_id)
            if not post_db_id:
                print(f"    WARNING: post not found in DB for {clean_url}", flush=True)
                continue

            ins, skp = insert_comments(conn, post_db_id, comments)
            print(f"    post_id={post_db_id} → inserted={ins} skipped={skp}", flush=True)
            total_inserted += ins
            total_skipped += skp

    conn.close()
    print(f"\n=== DONE: inserted={total_inserted} skipped={total_skipped} ===")


if __name__ == "__main__":
    main()
