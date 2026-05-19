"""Scrape Twitter/X posts for a dirigente via twscrape.

Usage:
  python twscrape_profile.py <handle> <profile_id> [--limit 30]

Example:
  python twscrape_profile.py LBallesterosM 28 --limit 30
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg2

# Load .env
env_file = Path(__file__).parent.parent / ".env"
for line in env_file.read_text().splitlines():
    line = line.strip()
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

TWITTER_AUTH_TOKEN = os.environ.get("TWITTER_AUTH_TOKEN", "")
DB_DSN = os.environ.get(
    "DB_DSN", "host=localhost port=5438 dbname=crece user=crece password=crece_dev"
)

handle = sys.argv[1] if len(sys.argv) > 1 else sys.exit("Usage: twscrape_profile.py <handle> <profile_id>")
profile_id = int(sys.argv[2]) if len(sys.argv) > 2 else sys.exit("Usage: twscrape_profile.py <handle> <profile_id>")
limit = 30
for i, arg in enumerate(sys.argv):
    if arg == "--limit" and i + 1 < len(sys.argv):
        limit = int(sys.argv[i + 1])

DRY_RUN = "--dry-run" in sys.argv


async def main():
    import twscrape

    api = twscrape.API()

    if not TWITTER_AUTH_TOKEN:
        sys.exit("TWITTER_AUTH_TOKEN not set in .env")

    print(f"Adding account with auth_token...", flush=True)
    await api.pool.add_account(
        username="crece_scraper",
        password="placeholder",
        email="placeholder@placeholder.com",
        email_password="placeholder",
        cookies=f"auth_token={TWITTER_AUTH_TOKEN}",
    )
    await api.pool.login_all()

    print(f"Fetching user info for @{handle}...", flush=True)
    user = await api.user_by_login(handle)
    if not user:
        sys.exit(f"User @{handle} not found")

    print(f"  id={user.id} name={user.displayname} followers={user.followersCount}", flush=True)

    if DRY_RUN:
        print("[dry-run] skipping tweet fetch")
        return

    print(f"Fetching up to {limit} tweets...", flush=True)
    tweets = []
    async for tweet in api.user_tweets(user.id, limit=limit):
        tweets.append(tweet)
        print(f"  [{len(tweets)}] {tweet.date.isoformat()[:10]} likes={tweet.likeCount} rt={tweet.retweetCount} — {tweet.rawContent[:60]}", flush=True)

    print(f"\nFetched {len(tweets)} tweets. Inserting into DB...", flush=True)

    conn = psycopg2.connect(DB_DSN)
    conn.autocommit = False
    cur = conn.cursor()

    # Update follower count on social_profiles
    cur.execute(
        "UPDATE social_profiles SET followers_count=%s, following_count=%s, posts_count=%s WHERE id=%s",
        (user.followersCount, user.followingCount, user.statusesCount, profile_id),
    )

    inserted = skipped = 0
    for t in tweets:
        post_id = str(t.id)
        cur.execute("SELECT id FROM social_posts WHERE platform_post_id=%s", (post_id,))
        if cur.fetchone():
            skipped += 1
            continue

        content = (t.rawContent or "").strip()
        post_type = "VIDEO" if t.media and any(getattr(m, "type", "") == "video" for m in (t.media or [])) else "TEXT"
        now = datetime.now(timezone.utc)

        try:
            cur.execute(
                """
                INSERT INTO social_posts
                    (profile_id, platform_post_id, content, post_type, published_at,
                     likes, comments, shares, views, engagement_rate,
                     is_political, scraped_at, raw_data)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,0,false,%s,%s)
                """,
                (
                    profile_id,
                    post_id,
                    content[:10_000],
                    post_type,
                    t.date,
                    t.likeCount or 0,
                    t.replyCount or 0,
                    t.retweetCount or 0,
                    t.viewCount or 0,
                    now,
                    json.dumps({
                        "source": "twscrape-v0.17",
                        "tweet_url": f"https://x.com/{handle}/status/{post_id}",
                        "scraped_at": now.isoformat(),
                    }),
                ),
            )
            inserted += 1
        except Exception as e:
            skipped += 1
            print(f"  insert error tweet_id={post_id}: {e}", flush=True)

    conn.commit()
    cur.close()
    conn.close()

    print(f"\n=== DONE: inserted={inserted} skipped={skipped} ===")
    print(f"Profile updated: @{handle} → followers={user.followersCount}")


if __name__ == "__main__":
    asyncio.run(main())
