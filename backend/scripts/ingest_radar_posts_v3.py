"""ingest_radar_posts_v3.py · 2026-05-21

INSERT + UPDATE de posts FB desde dump RADAR (Hugo) para dirigentes nuevos.
Para Pepe Monroy (dirigente_id=57): Hugo descubrió 228 posts adicionales,
shape JSON con content_caption + totales agregados (likes/comments/shares).

Idempotente:
- INSERT ON CONFLICT (platform_post_id) DO NOTHING
- UPDATE content + raw_data solo si content actual está vacío
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

DIRIGENTE_ID = int(os.environ.get("DIRIGENTE_ID", "57"))
PROFILE_ID = int(os.environ.get("PROFILE_ID", "47"))


def detect_post_type(caption: str, url: str | None) -> str:
    if url and "/reel/" in url.lower():
        return "REEL"
    if not caption or len(caption.strip()) < 10:
        return "IMAGE"
    return "TEXT"


async def main(json_path: Path, commit: bool) -> int:
    with json_path.open() as f:
        data = json.load(f)

    posts = data.get("posts", [])
    print(f"[meta] {len(posts)} posts · dirigente_id={DIRIGENTE_ID} profile_id={PROFILE_ID}")

    dsn = os.environ.get(
        "DATABASE_URL_RAW",
        "postgresql://crece:crece_dev@crece-db:5432/crece",
    )
    conn = await asyncpg.connect(dsn)

    counters: Counter[str] = Counter()
    pp_ids = [p["platform_post_id"] for p in posts]
    rows = await conn.fetch(
        "SELECT platform_post_id, id, content FROM social_posts WHERE platform_post_id = ANY($1::text[])",
        pp_ids,
    )
    existing = {r["platform_post_id"]: (r["id"], r["content"] or "") for r in rows}
    print(f"[map] {len(existing)}/{len(pp_ids)} ya existen en CRECE")

    for p in posts:
        pp = p["platform_post_id"]
        caption = (p.get("content_caption") or "").strip()
        url = p.get("post_url") or ""
        likes = int(p.get("likes_aggregate") or 0)
        comments_count = int(p.get("comments_aggregate") or 0)
        shares = int(p.get("shares_aggregate") or 0)
        time_iso = p.get("time_iso")
        published_at = None
        if time_iso:
            try:
                published_at = datetime.fromisoformat(time_iso.replace("Z", "+00:00"))
            except Exception:
                counters["bad_time"] += 1

        raw_data = {
            "url": url,
            "caption_source": "radar-fb-text-backfill-v1",
            "caption_radar_backfill": caption,
        }
        post_type = detect_post_type(caption, url)

        if pp in existing:
            post_id, existing_content = existing[pp]
            if len(existing_content.strip()) > 10:
                counters["skip_already_had_text"] += 1
                continue
            if commit:
                await conn.execute(
                    "UPDATE social_posts SET content = $1, raw_data = $2 WHERE id = $3",
                    caption or existing_content,
                    json.dumps(raw_data, ensure_ascii=False),
                    post_id,
                )
            counters["updated"] += 1
        else:
            if not caption and not published_at:
                counters["skip_insufficient_data"] += 1
                continue
            if commit:
                try:
                    await conn.execute(
                        """
                        INSERT INTO social_posts (
                            profile_id, platform_post_id, content, post_type,
                            published_at, likes, comments, shares, views,
                            engagement_rate, raw_data, scraped_at, is_political
                        )
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 0, 0, $9, NOW(), false)
                        ON CONFLICT (platform_post_id) DO NOTHING
                        """,
                        PROFILE_ID, pp, caption, post_type, published_at,
                        likes, comments_count, shares,
                        json.dumps(raw_data, ensure_ascii=False),
                    )
                except Exception as e:
                    print(f"  [insert err] pp={pp} {e}", file=sys.stderr)
                    counters["insert_err"] += 1
                    continue
            counters["inserted"] += 1

    await conn.close()
    print("\n===== RESULT =====")
    for k, v in counters.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--json", type=Path, required=True)
    p.add_argument("--commit", action="store_true")
    args = p.parse_args()
    sys.exit(asyncio.run(main(args.json, args.commit)))
