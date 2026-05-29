"""Ingest Joy's Laura Ballesteros Twitter replies + engagement updates into DB.

Source files (backend/scripts/data/):
  - laura_ballesteros_twitter_replies.json    → INSERT social_comments
  - laura_ballesteros_twitter_engagement_update.json → UPDATE social_posts

Handles:
  - Re-hashes author_hash with real COMMENT_AUTHOR_SALT
  - Resolves parent_post_id via platform_post_id lookup
  - Idempotent via ON CONFLICT (platform_comment_id) DO NOTHING
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import psycopg2

# ── Config ────────────────────────────────────────────────────────────────────

env_file = Path(__file__).parent.parent / ".env"
for line in env_file.read_text().splitlines():
    line = line.strip()
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

DB_DSN = os.environ.get(
    "DB_DSN", "host=localhost port=5438 dbname=crece user=crece password=crece_dev"
)
COMMENT_AUTHOR_SALT = os.environ.get("COMMENT_AUTHOR_SALT", "crece-v2-salt")

DATA_DIR = Path(__file__).parent / "data"
REPLIES_FILE = DATA_DIR / "laura_ballesteros_twitter_replies.json"
ENGAGEMENT_FILE = DATA_DIR / "laura_ballesteros_twitter_engagement_update.json"


def rehash_author(old_placeholder_hash: str, author_info: str) -> str:
    """Re-hash with real salt. author_info = whatever Joy used to build the old hash."""
    # Joy used SHA256(author_id) with placeholder salt. We re-hash the same input.
    # Since we don't have the original author_id, we re-hash the existing hash+salt
    # to produce a deterministic but salt-keyed value.
    return hashlib.sha256(f"{COMMENT_AUTHOR_SALT}|{old_placeholder_hash}".encode()).hexdigest()[:64]


def get_post_db_id(cur, platform_post_id: str) -> int | None:
    cur.execute(
        "SELECT id FROM social_posts WHERE platform_post_id = %s LIMIT 1",
        (platform_post_id,),
    )
    row = cur.fetchone()
    return row[0] if row else None


def ingest_replies(conn) -> tuple[int, int]:
    data = json.loads(REPLIES_FILE.read_text())
    comments = data["comments"]
    cur = conn.cursor()

    inserted = skipped = 0
    post_cache: dict[str, int | None] = {}

    for c in comments:
        ppost_id = c["parent_platform_post_id"]
        if ppost_id not in post_cache:
            post_cache[ppost_id] = get_post_db_id(cur, ppost_id)
        parent_post_id = post_cache[ppost_id]

        if not parent_post_id:
            print(f"  WARN: parent tweet {ppost_id} not in DB — skipping comment {c['platform_comment_id']}", flush=True)
            skipped += 1
            continue

        # Re-hash with real salt if placeholder
        old_hash = c["author_hash"]
        if c.get("raw_data", {}).get("_salt_placeholder"):
            author_hash = rehash_author(old_hash, old_hash)
        else:
            author_hash = old_hash

        content = (c.get("content") or "").strip()
        if not content:
            skipped += 1
            continue

        try:
            cur.execute(
                """
                INSERT INTO social_comments
                    (parent_post_id, platform_comment_id, content, author_hash,
                     likes, published_at, is_reply_to_comment, data_source)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (platform_comment_id) DO NOTHING
                """,
                (
                    parent_post_id,
                    c["platform_comment_id"],
                    content[:5000],
                    author_hash[:64],
                    int(c.get("likes") or 0),
                    c.get("published_at"),
                    bool(c.get("is_reply_to_comment", False)),
                    "chrome-devtools-tweet-detail-v1",
                ),
            )
            if cur.rowcount:
                inserted += 1
            else:
                skipped += 1
        except Exception as e:
            skipped += 1
            print(f"  INSERT error {c['platform_comment_id']}: {e}", flush=True)

    conn.commit()
    cur.close()
    return inserted, skipped


def ingest_engagement(conn) -> tuple[int, int]:
    data = json.loads(ENGAGEMENT_FILE.read_text())
    updates = data["updates"]
    cur = conn.cursor()

    updated = skipped = 0
    for u in updates:
        pid = u["platform_post_id"]
        try:
            cur.execute(
                """
                UPDATE social_posts
                SET likes    = %s,
                    shares   = %s,
                    comments = %s,
                    views    = COALESCE(%s, views)
                WHERE platform_post_id = %s
                """,
                (
                    int(u.get("likes") or 0),
                    int(u.get("retweets") or 0),
                    int(u.get("comments_count_platform") or 0),
                    u.get("views"),
                    pid,
                ),
            )
            if cur.rowcount:
                updated += 1
                print(f"  Updated {pid}: likes={u.get('likes')} rt={u.get('retweets')} views={u.get('views')}", flush=True)
            else:
                skipped += 1
                print(f"  WARN: post {pid} not found in DB", flush=True)
        except Exception as e:
            skipped += 1
            print(f"  UPDATE error {pid}: {e}", flush=True)

    conn.commit()
    cur.close()
    return updated, skipped


def main() -> None:
    print("=== Laura Ballesteros — Twitter Replies + Engagement Ingest ===", flush=True)
    conn = psycopg2.connect(DB_DSN)
    conn.autocommit = False

    print("\n[1/2] Ingesting replies...", flush=True)
    ins, skp = ingest_replies(conn)
    print(f"  Replies: inserted={ins} skipped={skp}", flush=True)

    print("\n[2/2] Updating engagement on 7 posts...", flush=True)
    upd, skp2 = ingest_engagement(conn)
    print(f"  Posts updated={upd} skipped={skp2}", flush=True)

    conn.close()
    print("\n=== DONE ===", flush=True)


if __name__ == "__main__":
    main()
