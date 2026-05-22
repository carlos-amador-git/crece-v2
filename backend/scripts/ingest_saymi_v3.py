"""ingest_saymi_v3.py · 2026-05-22

Ingest del shape RADAR v3 (entrega Hugo 2026-05-22):
  {export_meta, items[]} con cada item: {platform_entity_id, entity_type,
  payload{...}, detected_at, source_engine}

Procesa 3 archivos en orden:
1) saymi-yt-posts-v2-2026-05-22.json · BACKFILL UPDATE social_posts YT
2) saymi-tt-comments-v2-2026-05-22.json · INSERT social_comments TT
3) saymi-x-comments-v2-2026-05-22.json · INSERT social_comments X

YT comments file = 0 items · skip explícito.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import asyncpg

DIRIGENTE_ID = 3  # Saymi
EXPORTS_DIR = Path("/Users/marxchavez/Projects/radar/exports")

DSN = os.environ.get("DATABASE_URL_RAW", "postgresql://crece:crece_dev@localhost:5438/crece")

# Profile mapping en CRECE (verificado en sesiones anteriores)
PROFILE_IDS = {"YOUTUBE": 24, "TIKTOK": 22, "TWITTER": 6}


def author_hash(platform: str, username: str) -> str:
    """SHA256(platform + username + radar_salt) · LFPDPPP-compliant."""
    salt = os.environ.get("AUTHOR_SALT", "radar_v3_2026")
    return hashlib.sha256(f"{platform}_{username}_{salt}".encode()).hexdigest()


async def backfill_yt_stats(conn: asyncpg.Connection) -> Counter:
    path = EXPORTS_DIR / "saymi-yt-posts-v2-2026-05-22.json"
    with path.open() as f:
        data = json.load(f)
    items = data.get("items", [])
    print(f"\n[1/3] YT BACKFILL · {len(items)} items")
    c = Counter()
    for it in items:
        pid = str(it["platform_entity_id"])
        p = it.get("payload") or {}
        likes = int(p.get("like_count") or 0)
        comments_n = int(p.get("comment_count") or 0)
        views = int(p.get("view_count") or 0)

        r = await conn.execute(
            """
            UPDATE social_posts
            SET likes = $1, comments = $2, views = $3, scraped_at = NOW()
            WHERE platform_post_id = $4
              AND profile_id = $5
            """,
            likes, comments_n, views, pid, PROFILE_IDS["YOUTUBE"],
        )
        if r.endswith("UPDATE 1"):
            c["updated"] += 1
        else:
            c["not_found"] += 1
    return c


async def ingest_tt_comments(conn: asyncpg.Connection) -> Counter:
    path = EXPORTS_DIR / "saymi-tt-comments-v2-2026-05-22.json"
    with path.open() as f:
        data = json.load(f)
    items = data.get("items", [])
    print(f"\n[2/3] TT COMMENTS · {len(items)} items")

    # Map platform_post_id → post_id en CRECE
    post_ids_distinct = sorted({str(it["payload"]["post_id"]) for it in items if it.get("payload", {}).get("post_id")})
    rows = await conn.fetch(
        """
        SELECT sp.platform_post_id, sp.id
        FROM social_posts sp
        WHERE sp.profile_id = $1 AND sp.platform_post_id = ANY($2::text[])
        """,
        PROFILE_IDS["TIKTOK"], post_ids_distinct,
    )
    pp_to_post = {r["platform_post_id"]: r["id"] for r in rows}
    print(f"   [map] {len(pp_to_post)}/{len(post_ids_distinct)} posts TT resueltos")

    batch: list[tuple] = []
    c = Counter()
    for it in items:
        p = it.get("payload") or {}
        post_id_str = str(p.get("post_id") or "")
        post_id = pp_to_post.get(post_id_str)
        if not post_id:
            c["skipped_no_post"] += 1
            continue

        comment_id = str(p.get("comment_id") or "")
        if not comment_id:
            c["skipped_no_id"] += 1
            continue

        text = (p.get("text") or "").strip()
        username = p.get("author_username") or "anon"
        display = p.get("author_display_name") or username
        likes = int(p.get("digg_count") or 0)

        time_iso = p.get("create_time_iso")
        published_at = None
        if time_iso:
            try:
                published_at = datetime.fromisoformat(time_iso.replace("Z", "+00:00"))
            except Exception:
                c["bad_time"] += 1

        batch.append((
            post_id, comment_id, text, author_hash("TIKTOK", username),
            likes, published_at, False, None, None,
            "radar-tt-browser-v1", "pending", display,
        ))

    c["resolvable"] = len(batch)
    if not batch:
        return c

    for i in range(0, len(batch), 500):
        chunk = batch[i:i + 500]
        await conn.executemany(
            """
            INSERT INTO social_comments (
                parent_post_id, platform_comment_id, content, author_hash,
                likes, published_at, is_reply_to_comment, parent_comment_id,
                es_follower, data_source, review_status, commenter_handle,
                created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, NOW(), NOW())
            ON CONFLICT (platform_comment_id) DO NOTHING
            """,
            chunk,
        )
        c["inserted_attempted"] += len(chunk)
    return c


async def ingest_x_comments(conn: asyncpg.Connection) -> Counter:
    path = EXPORTS_DIR / "saymi-x-comments-v2-2026-05-22.json"
    with path.open() as f:
        data = json.load(f)
    items = data.get("items", [])
    print(f"\n[3/3] X COMMENTS · {len(items)} items")

    post_ids_distinct = sorted({str(it["payload"]["in_reply_to_post_id"]) for it in items if it.get("payload", {}).get("in_reply_to_post_id")})
    rows = await conn.fetch(
        """
        SELECT sp.platform_post_id, sp.id
        FROM social_posts sp
        WHERE sp.profile_id = $1 AND sp.platform_post_id = ANY($2::text[])
        """,
        PROFILE_IDS["TWITTER"], post_ids_distinct,
    )
    pp_to_post = {r["platform_post_id"]: r["id"] for r in rows}
    print(f"   [map] {len(pp_to_post)}/{len(post_ids_distinct)} tweets X resueltos")

    batch: list[tuple] = []
    c = Counter()
    for it in items:
        p = it.get("payload") or {}
        post_id_str = str(p.get("in_reply_to_post_id") or "")
        post_id = pp_to_post.get(post_id_str)
        if not post_id:
            c["skipped_no_post"] += 1
            continue

        comment_id = str(it.get("platform_entity_id") or "")
        if not comment_id:
            c["skipped_no_id"] += 1
            continue

        text = (p.get("text") or "").strip()
        username = p.get("author_username") or "anon"
        ts = p.get("timestamp")
        published_at = None
        if ts:
            try:
                published_at = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                c["bad_time"] += 1

        batch.append((
            post_id, comment_id, text, author_hash("TWITTER", username),
            0, published_at, False, None, None,
            "radar-x-scweet-v1", "pending", username,
        ))

    c["resolvable"] = len(batch)
    if not batch:
        return c

    await conn.executemany(
        """
        INSERT INTO social_comments (
            parent_post_id, platform_comment_id, content, author_hash,
            likes, published_at, is_reply_to_comment, parent_comment_id,
            es_follower, data_source, review_status, commenter_handle,
            created_at, updated_at
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, NOW(), NOW())
        ON CONFLICT (platform_comment_id) DO NOTHING
        """,
        batch,
    )
    c["inserted_attempted"] = len(batch)
    return c


async def main() -> int:
    conn = await asyncpg.connect(DSN)
    print(f"Saymi dirigente_id={DIRIGENTE_ID} · DSN local :5438")

    results = {}
    results["yt_backfill"] = await backfill_yt_stats(conn)
    results["tt_comments"] = await ingest_tt_comments(conn)
    results["x_comments"] = await ingest_x_comments(conn)

    await conn.close()

    print("\n===== RESULT =====")
    for k, v in results.items():
        print(f"  {k}: {dict(v)}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
