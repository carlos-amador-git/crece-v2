"""ingest_radar_yt_x_posts.py · 2026-05-21

INSERT posts YT + X desde dump RADAR. Shape:
  platform_post_id, payload (dict con title/text/likes/views/etc), detected_at, source

Mapping por --platform arg:
  YOUTUBE → profile_id 24 Saymi (saymipinedavelasco)
  TWITTER → profile_id 6 Saymi (@saymipinedav)
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

# Mapping (dirigente_id, platform) → profile_id
PROFILE_MAP = {
    (3, "YOUTUBE"): 24,
    (3, "TWITTER"): 6,
    (3, "TIKTOK"): 22,
}


def detect_post_type_yt(payload: dict) -> str:
    duration = payload.get("duration") or 0
    if isinstance(duration, str):
        try:
            duration = int(duration)
        except Exception:
            duration = 0
    return "REEL" if duration and duration < 60 else "VIDEO"


def detect_post_type_x(payload: dict) -> str:
    if payload.get("media_urls"):
        return "IMAGE"
    return "TEXT"


def to_datetime(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


async def main(json_path: Path, platform: str, dirigente_id: int, commit: bool) -> int:
    with json_path.open() as f:
        data = json.load(f)
    items = data.get("posts") or data.get("videos") or data.get("tweets") or data.get("items") or []

    dsn = os.environ.get("DATABASE_URL_RAW", "postgresql://crece:crece_dev@crece-db:5432/crece")
    conn = await asyncpg.connect(dsn)

    # profile_id por (dirigente_id, platform) desde BD — reusable sin editar
    # PROFILE_MAP por dirigente. PROFILE_MAP queda como fallback legacy.
    profile_id = await conn.fetchval(
        "SELECT id FROM social_profiles WHERE dirigente_id=$1 AND platform=$2",
        dirigente_id, platform,
    ) or PROFILE_MAP.get((dirigente_id, platform))
    if not profile_id:
        print(f"[err] No profile for ({dirigente_id}, {platform})", file=sys.stderr)
        await conn.close()
        return 1
    print(f"[meta] {len(items)} {platform} posts · dirigente={dirigente_id} profile={profile_id}")

    foll_row = await conn.fetchrow(
        "SELECT followers_count FROM social_profiles WHERE id = $1", profile_id
    )
    followers = (foll_row["followers_count"] if foll_row else 0) or 0

    counters: Counter[str] = Counter()
    pp_ids = [str(p["platform_post_id"]) for p in items]
    existing = {
        r["platform_post_id"]
        for r in await conn.fetch(
            "SELECT platform_post_id FROM social_posts WHERE platform_post_id = ANY($1::text[])",
            pp_ids,
        )
    }
    print(f"[map] {len(existing)}/{len(pp_ids)} ya existen en CRECE")

    for p in items:
        pp = str(p["platform_post_id"])
        if pp in existing:
            counters["skip_existing"] += 1
            continue

        payload = p.get("payload") or {}
        # YT: title + view_count + duration · X: text + likes_count + retweets + replies
        if platform == "YOUTUBE":
            content = payload.get("title") or payload.get("description") or ""
            likes = int(payload.get("like_count") or 0)
            comments_n = int(payload.get("comment_count") or 0)
            shares = 0
            views = int(payload.get("view_count") or 0)
            published_at = to_datetime(payload.get("upload_date") or payload.get("timestamp"))
            post_type = detect_post_type_yt(payload)
        elif platform == "TWITTER":
            content = payload.get("text") or payload.get("content") or ""
            likes = int(payload.get("likes_count") or payload.get("favoriteCount") or 0)
            comments_n = int(payload.get("replies_count") or 0)
            shares = int(payload.get("retweets_count") or 0)
            views = int(payload.get("view_count") or 0)
            published_at = to_datetime(payload.get("timestamp"))
            post_type = detect_post_type_x(payload)
        elif platform == "TIKTOK":
            # yt-dlp TT payload (cross-verified with Hugo peer RADAR 2026-05-25):
            # like_count→likes, view_count→views, comment_count→comments,
            # repost_count→shares (TT repost == share). save_count queda en raw_data.
            content = payload.get("description") or payload.get("title") or ""
            likes = int(payload.get("like_count") or 0)
            comments_n = int(payload.get("comment_count") or 0)
            shares = int(payload.get("repost_count") or 0)
            views = int(payload.get("view_count") or 0)
            published_at = to_datetime(payload.get("timestamp"))
            post_type = "VIDEO"
        elif platform == "FACEBOOK":
            content = payload.get("text") or ""
            likes = int(payload.get("likes_count") or 0)
            comments_n = int(payload.get("comments_count") or 0)
            shares = int(payload.get("shares_count") or 0)
            views = 0
            published_at = to_datetime(payload.get("time_iso") or payload.get("timestamp"))
            post_type = "TEXT"
        else:
            content = payload.get("title") or payload.get("text") or ""
            likes = comments_n = shares = views = 0
            published_at = to_datetime(payload.get("timestamp"))
            post_type = "TEXT"

        if not content and not published_at:
            counters["skip_insufficient"] += 1
            continue
        # published_at is NOT NULL en social_posts · fallback a detected_at o NOW
        if not published_at:
            published_at = to_datetime(p.get("detected_at")) or datetime.now(tz=None).astimezone()

        raw_data = {**payload, "caption_source": f"radar-{platform.lower()}-v1"}
        if commit:
            er = compute_engagement_rate(likes, comments_n, shares, views, followers)
            try:
                await conn.execute(
                    """
                    INSERT INTO social_posts (
                        profile_id, platform_post_id, content, post_type,
                        published_at, likes, comments, shares, views,
                        engagement_rate, raw_data, scraped_at, is_political
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, NOW(), false)
                    ON CONFLICT (platform_post_id) DO NOTHING
                    """,
                    profile_id, pp, content[:5000], post_type, published_at,
                    likes, comments_n, shares, views, er,
                    json.dumps(raw_data, ensure_ascii=False, default=str),
                )
            except Exception as e:
                print(f"  [err] {e}", file=sys.stderr)
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
    p.add_argument("--platform", required=True, choices=["YOUTUBE", "TWITTER", "TIKTOK", "FACEBOOK"])
    p.add_argument("--dirigente-id", type=int, default=3)
    p.add_argument("--commit", action="store_true")
    args = p.parse_args()
    sys.exit(asyncio.run(main(args.json, args.platform, args.dirigente_id, args.commit)))
