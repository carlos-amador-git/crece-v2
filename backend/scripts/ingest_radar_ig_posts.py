"""ingest_radar_ig_posts.py · 2026-05-21

INSERT posts IG desde dump RADAR (Hugo) · Saymi + Pepe.
JSON con shape: dirigente, platform_post_id, post_url, post_code, media_type,
product_type (clips=reels), time_iso, caption, like_count, comment_count,
play_count, author_username.

Mapping:
- "Saymi Adriana Pineda Velasco" → dirigente_id=3, profile_id=7
- "Pepe Monroy" → dirigente_id=57, profile_id=46
- media_type "8" o product_type carousel_container → ALBUM
- media_type "2" o product_type clips → REEL/VIDEO
- media_type "1" → IMAGE
- caption present → TEXT (default)

Idempotente: ON CONFLICT (platform_post_id) DO NOTHING.

Uso:
    docker exec crece-backend python /app/scripts/ingest_radar_ig_posts.py --json /tmp/ig.json --commit
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

from app.services.engagement import compute_engagement_rate

# dirigente name → (dirigente_id, profile_id IG)
PROFILE_MAP = {
    "Saymi Adriana Pineda Velasco": (3, 7),
    "Pepe Monroy": (57, 46),
}


def detect_post_type(media_type: str, product_type: str, caption: str) -> str:
    """Mapea IG media_type a CRECE post_type."""
    if product_type == "clips":
        return "REEL"
    if media_type == "2":
        return "VIDEO"
    if media_type == "8" or product_type == "carousel_container":
        return "CAROUSEL"
    if media_type == "1":
        return "IMAGE"
    return "TEXT"


async def main(json_path: Path, commit: bool) -> int:
    with json_path.open() as f:
        data = json.load(f)

    posts = data.get("posts", [])
    print(f"[meta] {len(posts)} posts IG · Saymi + Pepe")

    dsn = os.environ.get(
        "DATABASE_URL_RAW",
        "postgresql://crece:crece_dev@crece-db:5432/crece",
    )
    conn = await asyncpg.connect(dsn)

    counters: Counter[str] = Counter()
    foll_cache: dict[int, int] = {}

    async def _followers(pid: int) -> int:
        if pid not in foll_cache:
            r = await conn.fetchrow(
                "SELECT followers_count FROM social_profiles WHERE id = $1", pid
            )
            foll_cache[pid] = (r["followers_count"] if r else 0) or 0
        return foll_cache[pid]

    pp_ids = [p["platform_post_id"] for p in posts]
    rows = await conn.fetch(
        "SELECT platform_post_id FROM social_posts WHERE platform_post_id = ANY($1::text[])",
        pp_ids,
    )
    existing = {r["platform_post_id"] for r in rows}
    print(f"[map] {len(existing)}/{len(pp_ids)} ya existen en CRECE")

    for p in posts:
        dirigente_name = p.get("dirigente", "")
        if dirigente_name not in PROFILE_MAP:
            counters["skip_unknown_dirigente"] += 1
            continue
        _, profile_id = PROFILE_MAP[dirigente_name]

        pp = p["platform_post_id"]
        if pp in existing:
            counters["skip_existing"] += 1
            continue

        caption = (p.get("caption") or "").strip()
        url = p.get("post_url") or ""
        likes = int(p.get("like_count") or 0)
        comments = int(p.get("comment_count") or 0)
        views = int(p.get("play_count") or 0)
        time_iso = p.get("time_iso")
        published_at = None
        if time_iso:
            try:
                published_at = datetime.fromisoformat(time_iso.replace("Z", "+00:00"))
            except Exception:
                counters["bad_time"] += 1

        raw_data = {
            "url": url,
            "post_code": p.get("post_code"),
            "media_type": p.get("media_type"),
            "product_type": p.get("product_type"),
            "author_username": p.get("author_username"),
            "caption_source": "radar-ig-instagrapi-v1",
        }
        post_type = detect_post_type(
            str(p.get("media_type", "")), str(p.get("product_type", "")), caption
        )

        if commit:
            er = compute_engagement_rate(likes, comments, 0, views, await _followers(profile_id))
            try:
                await conn.execute(
                    """
                    INSERT INTO social_posts (
                        profile_id, platform_post_id, content, post_type,
                        published_at, likes, comments, shares, views,
                        engagement_rate, raw_data, scraped_at, is_political
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, 0, $8, $9, $10, NOW(), false)
                    ON CONFLICT (platform_post_id) DO NOTHING
                    """,
                    profile_id, pp, caption, post_type, published_at,
                    likes, comments, views, er,
                    json.dumps(raw_data, ensure_ascii=False),
                )
            except Exception as e:
                print(f"  [err] {e}", file=sys.stderr)
                counters["insert_err"] += 1
                continue
        counters[f"inserted_{dirigente_name.split()[0].lower()}"] += 1

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
