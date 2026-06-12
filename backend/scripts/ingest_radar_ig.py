"""ingest_radar_ig.py · 2026-05-26

Ingest IG (posts + comments) desde exports RADAR (Hugo), shape genérico,
parametrizado por dirigente — reusable para Piña/Ballesteros/Solano/Felipe.
NO depende de PROFILE_MAP hardcoded.

Resuelve los 3 gaps de shape detectados en el E2E de Piña:
  1. platform_post_id: RADAR usa `media_id_userid` → normalizo a bare `media_id`
     (formato que ya usa CRECE) para que posts+comments+existentes deduppen.
  2. Campos comments: RADAR `comment_id`/`comment_text`/`platform_post_id` →
     CRECE `platform_comment_id`/`content`/`parent_post_id` (resuelto a id interno).
  3. ER + author_hash: este ingest usa SQL crudo (bypassa el ORM listener), así
     que computa ER (compute_engagement_rate) y pseudonimiza (ensure_author_hash)
     explícitamente — igual que los otros ingest_radar_*.

Orden obligatorio: posts ANTES que comments (FK parent_post_id).

Uso:
    python3 backend/scripts/ingest_radar_ig.py --dirigente-id 1 --profile-id 2 \\
        --posts /path/pina-ig-posts.json --comments /path/pina-ig-comments.json [--commit]
"""
from __future__ import annotations

import argparse
import os
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

import asyncpg

from app.services.author_hash import ensure_author_hash
from app.services.engagement import compute_engagement_rate

DSN = os.environ.get("DATABASE_URL_RAW", "postgresql://crece:crece_dev@localhost:5438/crece")
DATA_SOURCE = "radar-ig-instagrapi-v1"


def bare(ppid: str) -> str:
    """media_id_userid → media_id (formato CRECE)."""
    return (ppid or "").split("_")[0]


def post_type(media_type: str | None, product_type: str | None, url: str | None) -> str:
    pt = (product_type or "").lower()
    if pt == "clips" or (url and "/reel/" in url.lower()):
        return "REEL"
    if str(media_type) == "8":
        return "CAROUSEL"
    if str(media_type) == "2":
        return "VIDEO"
    return "IMAGE"


def parse_dt(s: str | None):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


async def main(profile_id: int, posts_f: Path, comments_f: Path | None, commit: bool) -> int:
    conn = await asyncpg.connect(DSN)
    foll_row = await conn.fetchrow(
        "SELECT followers_count FROM social_profiles WHERE id = $1", profile_id
    )
    if foll_row is None:
        print(f"profile_id {profile_id} no existe", file=sys.stderr)
        return 1
    followers = (foll_row["followers_count"] or 0)

    # ── POSTS ──────────────────────────────────────────────
    posts = json.load(posts_f.open()).get("posts", [])
    seen: set[str] = set()
    n_post_ins = n_post_dup = 0
    for p in posts:
        pp = bare(p.get("platform_post_id"))
        if not pp or pp in seen:
            n_post_dup += 1
            continue
        seen.add(pp)
        likes = int(p.get("like_count") or 0)
        comments_n = int(p.get("comment_count") or 0)
        views = int(p.get("play_count") or 0)
        er = compute_engagement_rate(likes, comments_n, 0, views, followers)
        raw = {"url": p.get("post_url"), "post_code": p.get("post_code"),
               "media_type": p.get("media_type"), "product_type": p.get("product_type"),
               "caption_source": DATA_SOURCE}
        if commit:
            await conn.execute(
                """
                INSERT INTO social_posts
                    (profile_id, platform_post_id, content, post_type, published_at,
                     likes, comments, shares, views, engagement_rate, raw_data,
                     scraped_at, is_political)
                VALUES ($1,$2,$3,$4,$5,$6,$7,0,$8,$9,$10,NOW(),false)
                ON CONFLICT (platform_post_id) DO UPDATE SET
                    likes=EXCLUDED.likes, comments=EXCLUDED.comments,
                    views=EXCLUDED.views, engagement_rate=EXCLUDED.engagement_rate,
                    content=COALESCE(NULLIF(social_posts.content,''), EXCLUDED.content)
                """,
                profile_id, pp, (p.get("caption") or "")[:5000],
                post_type(p.get("media_type"), p.get("product_type"), p.get("post_url")),
                parse_dt(p.get("time_iso")) or datetime.now().astimezone(),
                likes, comments_n, views, er,
                json.dumps(raw, ensure_ascii=False),
            )
        n_post_ins += 1
    print(f"[posts] únicos={n_post_ins} dups_saltados={n_post_dup}")

    # ── COMMENTS ───────────────────────────────────────────
    n_com_ins = n_com_orphan = 0
    if comments_f:
        rows = await conn.fetch(
            "SELECT id, platform_post_id FROM social_posts WHERE profile_id = $1", profile_id
        )
        post_map = {r["platform_post_id"]: r["id"] for r in rows}
        comments = json.load(comments_f.open()).get("comments", [])
        for c in comments:
            parent = post_map.get(bare(c.get("platform_post_id")))
            if not parent:
                n_com_orphan += 1
                continue
            ah = ensure_author_hash(c.get("author_hash") or c.get("author_display_name") or "", "INSTAGRAM")
            if commit:
                await conn.execute(
                    """
                    INSERT INTO social_comments
                        (parent_post_id, platform_comment_id, content, author_hash,
                         likes, published_at, is_reply_to_comment, data_source, commenter_handle)
                    VALUES ($1,$2,$3,$4,0,$5,false,$6,$7)
                    ON CONFLICT (platform_comment_id) DO NOTHING
                    """,
                    parent, str(c.get("comment_id")), c.get("comment_text") or "",
                    ah[:64], parse_dt(c.get("time_iso")),
                    DATA_SOURCE, c.get("author_display_name"),
                )
            n_com_ins += 1
        print(f"[comments] ingestables={n_com_ins} huérfanos(sin post)={n_com_orphan}")

    await conn.close()
    if not commit:
        print("\n[DRY-RUN] nada escrito. --commit para aplicar.")
    else:
        print("\n[APPLY] OK")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dirigente-id", type=int, required=True)
    ap.add_argument("--profile-id", type=int, required=True)
    ap.add_argument("--posts", type=Path, required=True)
    ap.add_argument("--comments", type=Path)
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()
    sys.exit(asyncio.run(main(args.profile_id, args.posts, args.comments, args.commit)))
