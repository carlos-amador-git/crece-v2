"""ingest_radar_comments_v2.py · 2026-05-21

Ingest comments del export JSON Hugo formato v2: {export_meta, comments[]}.

Cada comment:
- platform_post_id → resolver a parent_post_id via social_posts (Saymi FB)
- comment_id_surrogate → platform_comment_id (UNIQUE constraint)
- author_hash, author_display_name → CRECE columns
- comment_text → content
- time_iso (puede null) → published_at

Idempotente: INSERT ON CONFLICT (platform_comment_id) DO NOTHING.

Uso:
    docker exec crece-backend python /app/scripts/ingest_radar_comments_v2.py --json /tmp/radar-comments.json --dry-run
    docker exec crece-backend python /app/scripts/ingest_radar_comments_v2.py --json /tmp/radar-comments.json --commit
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import asyncpg

DIRIGENTE_ID = 3
PLATFORM = "FACEBOOK"
DATA_SOURCE = "radar-fb-playwright-v1"  # value pre-existente en BD para consistency


async def main(json_path: Path, commit: bool) -> int:
    with json_path.open() as f:
        data = json.load(f)

    meta = data["export_meta"]
    comments = data["comments"]
    print(
        f"[meta] {meta.get('n_comments')} comments · "
        f"{meta.get('unique_posts')} posts · {meta.get('unique_authors')} authors"
    )

    dsn = os.environ.get(
        "DATABASE_URL_RAW",
        "postgresql://crece:crece_dev@crece-db:5432/crece",
    )
    conn = await asyncpg.connect(dsn)

    # Map platform_post_id → post_id
    pp_ids = sorted({c["platform_post_id"] for c in comments})
    rows = await conn.fetch(
        """
        SELECT sp.platform_post_id, sp.id
        FROM social_posts sp
        JOIN social_profiles sps ON sps.id = sp.profile_id
        WHERE sps.dirigente_id = $1 AND sps.platform = $2
          AND sp.platform_post_id = ANY($3::text[])
        """,
        DIRIGENTE_ID,
        PLATFORM,
        pp_ids,
    )
    pp_to_post = {r["platform_post_id"]: r["id"] for r in rows}
    print(f"[map] {len(pp_to_post)}/{len(pp_ids)} platform_post_ids resueltos a posts CRECE")
    missing = set(pp_ids) - set(pp_to_post.keys())
    if missing:
        print(f"[warn] {len(missing)} platform_post_ids no encontrados (skip)")

    # Count pre-existing for this data_source on target posts
    pre = await conn.fetchval(
        """
        SELECT COUNT(*) FROM social_comments
        WHERE data_source = $1 AND parent_post_id = ANY($2::int[])
        """,
        DATA_SOURCE,
        list(pp_to_post.values()),
    )
    print(f"[pre] comments with data_source={DATA_SOURCE} en posts target: {pre}")

    counters: Counter[str] = Counter()
    batch: list[tuple] = []

    for c in comments:
        pp = c["platform_post_id"]
        post_id = pp_to_post.get(pp)
        if not post_id:
            counters["skipped_no_post"] += 1
            continue

        published_at = None
        time_iso = c.get("time_iso")
        if time_iso:
            try:
                published_at = datetime.fromisoformat(time_iso.replace("Z", "+00:00"))
            except Exception:
                counters["bad_time"] += 1

        batch.append(
            (
                post_id,
                c["comment_id_surrogate"],
                c.get("comment_text") or "",
                c.get("author_hash") or "",
                0,  # likes
                published_at,
                False,  # is_reply_to_comment
                None,  # parent_comment_id
                None,  # es_follower
                DATA_SOURCE,
                "pending",  # review_status
                c.get("author_display_name"),  # commenter_handle (no es handle real, es display)
            )
        )

    counters["resolvable"] = len(batch)

    if not commit:
        print("\n===== DRY-RUN =====")
        for k, v in counters.items():
            print(f"  {k}: {v}")
        print("[dry-run] pasa --commit para escribir")
        await conn.close()
        return 0

    for i in range(0, len(batch), 500):
        chunk = batch[i : i + 500]
        await conn.executemany(
            """
            INSERT INTO social_comments (
                parent_post_id, platform_comment_id, content, author_hash,
                likes, published_at, is_reply_to_comment, parent_comment_id,
                es_follower, data_source, review_status, commenter_handle,
                created_at, updated_at
            )
            VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12,
                NOW(), NOW()
            )
            ON CONFLICT (platform_comment_id) DO NOTHING
            """,
            chunk,
        )
        print(f"  attempted batch {i + len(chunk)}/{len(batch)}")

    post = await conn.fetchval(
        """
        SELECT COUNT(*) FROM social_comments
        WHERE data_source = $1 AND parent_post_id = ANY($2::int[])
        """,
        DATA_SOURCE,
        list(pp_to_post.values()),
    )
    counters["attempted"] = len(batch)
    counters["in_db_target_posts_post"] = post
    counters["delta_inserted"] = post - pre

    await conn.close()
    print("\n===== RESULT =====")
    for k, v in counters.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--json", type=Path, required=True)
    p.add_argument("--commit", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    sys.exit(asyncio.run(main(args.json, args.commit)))
