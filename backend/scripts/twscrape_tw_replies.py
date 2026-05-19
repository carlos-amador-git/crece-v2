#!/usr/bin/env python3
"""Fetch Twitter/X replies via twscrape and UPSERT into social_comments.

Sprint: 2026-05-07 (replaces manual chrome-devtools / playwright reply ingest flow)
Branch: feat/phase-b-pesos-editables

Reads recent (≤30d) TWITTER posts with replyCount > 0 from social_posts and
fetches their reply tree using `api.tweet_replies(twid)` from twscrape 0.17.0.

ROOT CAUSE FIXED (2026-05-08, this script):
    twscrape 0.17.0 has an unfixed upstream bug — `XClIdGen.create()` parses
    `https://x.com/tesla` HTML using the hardcoded split pattern
    `'e=>e+"."+'` which X removed from its bundle. The parser raises
    `IndexError: list index out of range`, the queue_client traps generic
    Exception and locks the account 15min — causing the reported 45s hang.
    See: twscrape issues #248 / xclid.py:50.

    Workaround (validated against tweet 2041574638082240765, Ballesteros):
    Monkey-patch `queue_client.XClIdGenStore.get` to return a stub that emits
    an empty `x-client-transaction-id` header. X still serves GraphQL
    TweetDetail / TweetResultsByRestId without the header.

LFPDPPP: author_id is hashed (SHA256) before persistence.
Idempotent: ON CONFLICT (platform_comment_id) DO UPDATE.

Usage:
    # Single dirigente
    docker exec crece-backend python /app/scripts/twscrape_tw_replies.py --dirigente-id 8

    # All piloto dirigentes
    docker exec crece-backend python /app/scripts/twscrape_tw_replies.py --all

    # Smoke test — single tweet (Ballesteros 2041574638082240765)
    docker exec crece-backend python /app/scripts/twscrape_tw_replies.py --tweet-id 2041574638082240765

    # Dry run (no DB writes)
    docker exec crece-backend python /app/scripts/twscrape_tw_replies.py --dirigente-id 8 --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg2
import psycopg2.extras
import twscrape
from twscrape import queue_client

# ── Config ───────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for env_file in [PROJECT_ROOT / ".env", PROJECT_ROOT / ".env.scraping-keys"]:
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

# Default DSN: inside crece-backend container the DB is at `db:5432`.
# From host (Mac), set DB_DSN=host=localhost port=5438 dbname=crece user=crece password=crece_dev
def _default_dsn() -> str:
    if Path("/.dockerenv").exists():
        return "host=db port=5432 dbname=crece user=crece password=crece_dev"
    return "host=localhost port=5438 dbname=crece user=crece password=crece_dev"


DB_DSN = os.environ.get("DB_DSN", _default_dsn())
HASH_SALT = os.environ.get("COMMENT_AUTHOR_SALT", "crece-v2-lfpdppp-salt-2026")

WINDOW_DAYS = 30
_now = datetime.now(UTC)
WINDOW_START = (_now - timedelta(days=WINDOW_DAYS)).replace(
    hour=0, minute=0, second=0, microsecond=0
)

PILOTO_DIRIGENTE_IDS = (1, 2, 3, 4, 5, 6, 8)
DATA_SOURCE = "twscrape-replies-v1"
PLATFORM = "TWITTER"

# Per-tweet caps to avoid runaway pagination on viral threads.
MAX_REPLIES_PER_TWEET = 200
# Per-account budget — lock cooldown is 15min if abused, so we stay conservative.
MAX_TWEETS_PER_RUN = 100
# Pause between tweet calls (seconds) — reduces "Account timeouted" risk.
INTER_TWEET_DELAY = 2.5
# Per-tweet hard timeout — replies endpoint can rarely hang.
TWEET_TIMEOUT_SEC = 45

# ── Logger ───────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(message)s",
    datefmt="%H:%M:%S",
)
# Silence httpx URL spam (twscrape logs every GraphQL request at INFO).
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("twscrape_tw_replies")


# ── XClIdGen workaround (twscrape #248) ──────────────────────────────
class _StubXClIdGen:
    """Returns empty x-client-transaction-id header. X GraphQL still serves
    TweetDetail / TweetResultsByRestId without the signed header in
    2026-05-08 testing. Replace with upstream patched twscrape >0.17.0
    once vladkens/twscrape ships a fix."""

    def calc(self, method: str, path: str) -> str:
        return ""


class _StubXClIdGenStore:
    items: dict = {}

    @classmethod
    async def get(cls, username: str, fresh: bool = False) -> _StubXClIdGen:
        return _StubXClIdGen()


def _apply_xclid_workaround() -> None:
    queue_client.XClIdGenStore = _StubXClIdGenStore
    log.info("Applied XClIdGen workaround (empty x-client-transaction-id header)")


# ── DB helpers ───────────────────────────────────────────────────────
def author_hash(author_id: str | None, fallback: str = "") -> str:
    raw = f"{PLATFORM}:{author_id or fallback}:{HASH_SALT}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def fetch_target_tweets(
    conn, dirigente_id: int | None, single_tweet_id: str | None
) -> list[dict]:
    """Get TWITTER posts in 30d window with replyCount > 0 to fetch replies for."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if single_tweet_id:
        cur.execute(
            """
            SELECT sp.id AS post_id, sp.platform_post_id, sp.comments AS reply_count,
                   spf.dirigente_id, spf.handle, sp.published_at
            FROM social_posts sp
            JOIN social_profiles spf ON spf.id = sp.profile_id
            WHERE spf.platform = 'TWITTER'
              AND sp.platform_post_id = %s
            """,
            (single_tweet_id,),
        )
    elif dirigente_id is not None:
        cur.execute(
            """
            SELECT sp.id AS post_id, sp.platform_post_id, sp.comments AS reply_count,
                   spf.dirigente_id, spf.handle, sp.published_at
            FROM social_posts sp
            JOIN social_profiles spf ON spf.id = sp.profile_id
            WHERE spf.platform = 'TWITTER'
              AND spf.dirigente_id = %s
              AND sp.published_at >= %s
              AND sp.comments > 0
            ORDER BY sp.published_at DESC
            LIMIT %s
            """,
            (dirigente_id, WINDOW_START, MAX_TWEETS_PER_RUN),
        )
    else:
        cur.execute(
            """
            SELECT sp.id AS post_id, sp.platform_post_id, sp.comments AS reply_count,
                   spf.dirigente_id, spf.handle, sp.published_at
            FROM social_posts sp
            JOIN social_profiles spf ON spf.id = sp.profile_id
            WHERE spf.platform = 'TWITTER'
              AND spf.dirigente_id = ANY(%s)
              AND sp.published_at >= %s
              AND sp.comments > 0
            ORDER BY sp.comments DESC, sp.published_at DESC
            LIMIT %s
            """,
            (list(PILOTO_DIRIGENTE_IDS), WINDOW_START, MAX_TWEETS_PER_RUN),
        )
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    return rows


def upsert_reply(conn, parent_post_id: int, reply: twscrape.Tweet) -> str:
    """UPSERT social_comments. Returns 'inserted' | 'updated' | 'skipped'."""
    pcid = str(reply.id)
    text = (reply.rawContent or "").strip()
    if not text:
        return "skipped"

    pub = reply.date
    if pub and pub < WINDOW_START:
        # We DO NOT skip — replies can be older than 30d (the parent post is
        # in window). We persist regardless. Window filter applies to PARENT,
        # not to replies.
        pass

    author_id = str(reply.user.id) if reply.user else ""
    ah = author_hash(author_id, fallback=pcid)

    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO social_comments
            (parent_post_id, platform_comment_id, content, author_hash,
             likes, published_at, is_reply_to_comment, data_source)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (platform_comment_id) DO UPDATE SET
            likes = EXCLUDED.likes,
            content = EXCLUDED.content,
            data_source = EXCLUDED.data_source,
            updated_at = NOW()
        RETURNING (xmax = 0) AS inserted
        """,
        (
            parent_post_id,
            pcid,
            text[:5000],
            ah,
            int(reply.likeCount or 0),
            pub,
            False,  # always reply-to-post (not nested-comment) for this scraper
            DATA_SOURCE,
        ),
    )
    inserted = cur.fetchone()[0]
    cur.close()
    return "inserted" if inserted else "updated"


# ── Core ─────────────────────────────────────────────────────────────
async def fetch_replies_for_tweet(
    api: twscrape.API, twid: int, max_replies: int
) -> list[twscrape.Tweet]:
    out: list[twscrape.Tweet] = []
    # Wrap async-for in a wait_for via collect helper.
    async def _collect() -> None:
        async for r in api.tweet_replies(twid, limit=max_replies):
            out.append(r)
            if len(out) >= max_replies:
                break

    try:
        await asyncio.wait_for(_collect(), timeout=TWEET_TIMEOUT_SEC)
    except asyncio.TimeoutError:
        log.warning(f"  TIMEOUT after {TWEET_TIMEOUT_SEC}s (collected {len(out)})")
    return out


async def run(args: argparse.Namespace) -> int:
    _apply_xclid_workaround()

    api = twscrape.API()
    pool_info = await api.pool.accounts_info()
    active = [a for a in pool_info if a.get("active")]
    if not active:
        log.error("No active twscrape accounts in pool — aborting")
        return 2
    log.info(f"Pool: {len(active)} active account(s): {[a['username'] for a in active]}")

    conn = psycopg2.connect(DB_DSN)
    conn.autocommit = False

    # Fetch target tweets
    tweets = fetch_target_tweets(conn, args.dirigente_id, args.tweet_id)
    log.info(f"Target tweets: {len(tweets)} (dirigente_id={args.dirigente_id} tweet_id={args.tweet_id})")
    if not tweets:
        log.info("Nothing to do — exiting")
        conn.close()
        return 0

    stats = {"tweets_processed": 0, "replies_fetched": 0, "inserted": 0, "updated": 0, "errors": 0}
    per_dirigente: dict[int, dict] = {}

    for idx, t in enumerate(tweets, 1):
        twid = int(t["platform_post_id"])
        post_id = t["post_id"]
        d_id = t["dirigente_id"]
        per_dirigente.setdefault(d_id, {"tweets": 0, "replies": 0, "inserted": 0, "updated": 0})
        per_dirigente[d_id]["tweets"] += 1

        log.info(
            f"[{idx}/{len(tweets)}] @{t['handle']} tw={twid} "
            f"reply_count_meta={t['reply_count']} pub={t['published_at']:%Y-%m-%d}"
        )

        try:
            replies = await fetch_replies_for_tweet(api, twid, MAX_REPLIES_PER_TWEET)
        except Exception as e:
            log.error(f"  ERROR fetch: {type(e).__name__}: {e}")
            stats["errors"] += 1
            continue

        log.info(f"  fetched {len(replies)} replies")
        stats["tweets_processed"] += 1
        stats["replies_fetched"] += len(replies)
        per_dirigente[d_id]["replies"] += len(replies)

        if args.dry_run:
            for r in replies[:3]:
                log.info(f"    [dry] @{r.user.username if r.user else '?'} | {r.rawContent[:80]!r}")
            continue

        # Persist (per-tweet transaction)
        try:
            for r in replies:
                outcome = upsert_reply(conn, post_id, r)
                stats[outcome] += 1
                per_dirigente[d_id][outcome] += 1
            conn.commit()
        except Exception as e:
            conn.rollback()
            log.error(f"  DB ERROR — rollback: {type(e).__name__}: {e}")
            stats["errors"] += 1
            continue

        await asyncio.sleep(INTER_TWEET_DELAY)

    conn.close()

    # ── Report ─────────────────────────────────────────────────────
    log.info("=" * 60)
    log.info(f"DONE. tweets={stats['tweets_processed']}/{len(tweets)} "
             f"replies={stats['replies_fetched']} "
             f"inserted={stats['inserted']} updated={stats['updated']} "
             f"errors={stats['errors']}")
    log.info("By dirigente:")
    for d_id, s in sorted(per_dirigente.items()):
        log.info(f"  dirigente_id={d_id} tweets={s['tweets']} "
                 f"replies={s['replies']} inserted={s['inserted']} updated={s['updated']}")
    return 0 if stats["errors"] == 0 else 1


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--dirigente-id", type=int, help="Run for single dirigente")
    g.add_argument("--all", action="store_true",
                   help=f"Run for piloto roster {PILOTO_DIRIGENTE_IDS}")
    g.add_argument("--tweet-id", type=str,
                   help="Fetch replies for a single tweet id (smoke test)")
    p.add_argument("--dry-run", action="store_true",
                   help="Fetch but do not write to DB")
    args = p.parse_args()
    if args.all:
        args.dirigente_id = None
    return args


if __name__ == "__main__":
    args = parse_args()
    sys.exit(asyncio.run(run(args)))
