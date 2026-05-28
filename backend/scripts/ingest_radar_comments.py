"""ingest_radar_comments.py · 2026-05-20 (post dump v2 Marx)

Ingresa los comments de Saymi + Pepe del dump RADAR v2 a social_comments.

Idempotente: UPSERT por platform_comment_id (que ya es UNIQUE en BD).
Mapeo parent_post_id (RADAR base64) → social_posts.id (BD integer) via
índice construido al inicio.

Caveat Marx: comments.published_at = null para todos (engine no captura
timestamp del comment). Schema NULLABLE permite.

Uso:
    docker exec -e DUMP_ROOT=/tmp/radar_dump_v2 crece-backend python /app/scripts/ingest_radar_comments.py --commit
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import asyncpg

from app.services.author_hash import ensure_author_hash

DUMP_ROOT = Path(
    os.environ.get("DUMP_ROOT", "/Users/marxchavez/Projects/radar/exports/linda_handoff_20260520_0608")
)

TENANTS = [
    {"slug": "saymi-adriana-pineda-velasco", "dirigente_id": 3, "fb_profile_id": 27},
    {"slug": "pepe-monroy", "dirigente_id": 57, "fb_profile_id": 47},
]


async def main(*, dry_run: bool) -> int:
    print(f"\n=== INGEST RADAR COMMENTS · dry_run={dry_run} ===\n")

    host = os.environ.get("DB_HOST", "db")
    port = int(os.environ.get("DB_PORT", "5432"))
    conn = await asyncpg.connect(host=host, port=port, user="crece", password="crece_dev", database="crece")

    try:
        for tenant in TENANTS:
            print(f"\n── {tenant['slug']} (dirigente_id={tenant['dirigente_id']}) ──")

            comments_path = DUMP_ROOT / tenant["slug"] / "comments.json"
            with open(comments_path) as f:
                comments = json.load(f)
            print(f"  loaded comments={len(comments)}")

            # Build index platform_post_id → social_posts.id
            rows = await conn.fetch(
                "SELECT id, platform_post_id FROM social_posts WHERE profile_id = $1",
                tenant["fb_profile_id"],
            )
            post_map: dict[str, int] = {r["platform_post_id"]: r["id"] for r in rows}
            print(f"  indexed BD posts: {len(post_map)}")

            stats = {
                "comments_inserted": 0,
                "comments_updated": 0,
                "skipped_no_parent_post": 0,
                "skipped_empty_content": 0,
            }

            for c in comments:
                content = (c.get("content") or "").strip()
                if not content:
                    stats["skipped_empty_content"] += 1
                    continue

                parent_radar_id = c.get("parent_post_id")
                bd_post_id = post_map.get(parent_radar_id)
                if not bd_post_id:
                    stats["skipped_no_parent_post"] += 1
                    continue

                platform_comment_id = c["platform_comment_id"]
                # Guard PII: si RADAR mandó nombre crudo en vez de hash, hashear
                author_hash = ensure_author_hash(c.get("author_hash") or "", "FACEBOOK")
                commenter_handle = c.get("author_display_name")
                is_reply = bool(c.get("is_reply_to_comment", False))
                likes = int(c.get("likes") or 0)
                data_source = (c.get("data_source") or "radar-fb-playwright-v1")[:80]

                if dry_run:
                    existing = await conn.fetchval(
                        "SELECT id FROM social_comments WHERE platform_comment_id = $1",
                        platform_comment_id,
                    )
                    if existing:
                        stats["comments_updated"] += 1
                    else:
                        stats["comments_inserted"] += 1
                    continue

                result = await conn.fetchrow(
                    """
                    INSERT INTO social_comments (
                        parent_post_id, platform_comment_id, content, author_hash,
                        likes, published_at, is_reply_to_comment, data_source,
                        commenter_handle
                    ) VALUES (
                        $1, $2, $3, $4,
                        $5, NULL, $6, $7,
                        $8
                    )
                    ON CONFLICT (platform_comment_id) DO UPDATE SET
                        content = EXCLUDED.content,
                        likes = EXCLUDED.likes,
                        commenter_handle = COALESCE(EXCLUDED.commenter_handle, social_comments.commenter_handle),
                        updated_at = now()
                    RETURNING (xmax = 0) AS inserted_now
                    """,
                    bd_post_id, platform_comment_id, content, author_hash[:64],
                    likes, is_reply, data_source, commenter_handle,
                )
                if result and result["inserted_now"]:
                    stats["comments_inserted"] += 1
                else:
                    stats["comments_updated"] += 1

            for k, v in stats.items():
                print(f"  {k}: {v}")

    finally:
        await conn.close()
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit", action="store_true")
    args = parser.parse_args()
    sys.exit(asyncio.run(main(dry_run=not args.commit)))
