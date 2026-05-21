"""ingest_radar_captions_v2.py · 2026-05-21

Ingest UPDATE de captions FB rescatadas por Hugo (RADAR fb_text_backfill).
Formato JSON v2: {export_meta, posts[]} con platform_post_id + content_caption.

Idempotente: UPDATE social_posts.content + raw_data si platform_post_id match.
Solo escribe si content actual está vacío (no sobreescribe caption existente).

Uso:
    docker exec crece-backend python /app/scripts/ingest_radar_captions_v2.py --json /tmp/captions.json --commit
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections import Counter
from pathlib import Path

import asyncpg


async def main(json_path: Path, commit: bool) -> int:
    with json_path.open() as f:
        data = json.load(f)

    meta = data["export_meta"]
    posts = data["posts"]
    print(f"[meta] {meta.get('n_posts')} posts · engine={meta.get('filter')}")

    dsn = os.environ.get(
        "DATABASE_URL_RAW",
        "postgresql://crece:crece_dev@crece-db:5432/crece",
    )
    conn = await asyncpg.connect(dsn)

    counters: Counter[str] = Counter()
    for p in posts:
        pp = p["platform_post_id"]
        caption = (p.get("content_caption") or "").strip()
        if not caption:
            counters["skipped_empty_caption"] += 1
            continue
        # Match por platform_post_id · solo update si content vacío
        row = await conn.fetchrow(
            """
            SELECT sp.id, sp.content, sp.raw_data
            FROM social_posts sp
            JOIN social_profiles sps ON sps.id = sp.profile_id
            WHERE sps.platform = 'FACEBOOK' AND sp.platform_post_id = $1
            """,
            pp,
        )
        if not row:
            counters["not_found_in_crece"] += 1
            continue
        existing_content = (row["content"] or "").strip()
        if len(existing_content) > 10:
            counters["already_had_text"] += 1
            continue
        # Update content + merge caption into raw_data
        raw = row["raw_data"] or {}
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except json.JSONDecodeError:
                raw = {}
        raw["caption_radar_backfill"] = caption
        raw["caption_source"] = "radar-fb-text-backfill-v1"
        if commit:
            await conn.execute(
                """
                UPDATE social_posts
                SET content = $1, raw_data = $2
                WHERE id = $3
                """,
                caption,
                json.dumps(raw, ensure_ascii=False),
                row["id"],
            )
        counters["updated"] += 1

    await conn.close()
    print("\n===== RESULT =====")
    for k, v in counters.items():
        print(f"  {k}: {v}")
    if not commit:
        print("[dry-run] pasa --commit para escribir")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--json", type=Path, required=True)
    p.add_argument("--commit", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    sys.exit(asyncio.run(main(args.json, args.commit)))
