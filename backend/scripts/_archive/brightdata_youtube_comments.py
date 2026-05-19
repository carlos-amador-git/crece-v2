"""Ingesta de comments YouTube via Brightdata Scraping Browser.

Parse DOM (ytd-comment-thread-renderer). YouTube carga comments via scroll
infinito — disparamos 10-15 rondas de scroll antes de parsear.

Consent bypass para sesiones nuevas: cookie CONSENT=YES+cb antes del goto
+ URL param ?hl=es&gl=MX.

LFPDPPP: author_hash SHA256(platform+channel_id|name+SALT).
data_source='brightdata-yt-browser-v1'.

Uso:
    python scripts/brightdata_youtube_comments.py <dirigente_id|all> [top_n]

Dirigentes con YT en BD: 1 (Piña, 18 vids), 3 (Pineda, 30 vids), 6 (Cravioto, 8 vids).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg2

from app.services.brightdata_browser import brightdata_page

ENV_FILE = Path(__file__).resolve().parents[1] / ".env.scraping-keys"
if ENV_FILE.exists():
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

DB_DSN = os.environ.get(
    "DB_DSN", "host=localhost port=5438 dbname=crece user=crece password=crece_dev"
)
HASH_SALT = os.environ["COMMENT_AUTHOR_SALT"]

MAX_COMMENTS_PER_VIDEO = int(os.environ.get("YT_MAX_COMMENTS_PER_VIDEO", "50"))
TOP_N_VIDEOS = int(os.environ.get("TOP_N_VIDEOS", "8"))
SCROLL_ROUNDS = int(os.environ.get("YT_SCROLL_ROUNDS", "12"))

DATA_SOURCE = "brightdata-yt-browser-v1"
SPRINT_B_DIRIGENTES = [1, 3, 6]


def author_hash(ident: str | None) -> str:
    raw = f"YOUTUBE:{ident or 'anon'}:{HASH_SALT}"
    return hashlib.sha256(raw.encode()).hexdigest()


REL_RE = re.compile(r"\b(?:hace\s+)?(\d+)\s*(segundo|minuto|min|hora|día|dia|semana|mes|año)s?\b", re.IGNORECASE)


def parse_relative_es(text: str, now: datetime) -> datetime | None:
    m = REL_RE.search(text or "")
    if not m:
        return None
    n = int(m.group(1))
    unit = m.group(2).lower()
    if unit.startswith("seg"):
        delta = timedelta(seconds=n)
    elif unit.startswith("min"):
        delta = timedelta(minutes=n)
    elif unit.startswith("hora"):
        delta = timedelta(hours=n)
    elif unit.startswith("d"):
        delta = timedelta(days=n)
    elif unit.startswith("sem"):
        delta = timedelta(weeks=n)
    elif unit.startswith("mes"):
        delta = timedelta(days=30 * n)
    elif unit.startswith("añ"):
        delta = timedelta(days=365 * n)
    else:
        return None
    return now - delta


async def scroll_until_end(page, max_rounds: int) -> int:
    """Scrollea el documento para cargar comments lazy. YT usa virtual scroll."""
    last_count = 0
    stable_rounds = 0
    for i in range(max_rounds):
        await page.evaluate("window.scrollBy(0, 2500)")
        await page.wait_for_timeout(1500)
        count = await page.locator("ytd-comment-thread-renderer").count()
        if count == last_count:
            stable_rounds += 1
            if stable_rounds >= 3:
                break
        else:
            stable_rounds = 0
            last_count = count
    return last_count


async def extract_comments(page) -> list[dict]:
    threads = await page.locator("ytd-comment-thread-renderer").all()
    out: list[dict] = []
    now = datetime.now(UTC)
    for t in threads[:MAX_COMMENTS_PER_VIDEO]:
        try:
            author = ""
            try:
                author = (await t.locator("a#author-text").first.inner_text(timeout=1500)).strip()
            except Exception:
                pass
            text = ""
            try:
                text = (await t.locator("#content-text").first.inner_text(timeout=1500)).strip()
            except Exception:
                pass
            likes_str = ""
            try:
                likes_str = (await t.locator("span#vote-count-middle").first.inner_text(timeout=1000)).strip()
            except Exception:
                pass
            # channel id (href) for stable hash
            channel_href = ""
            try:
                channel_href = (await t.locator("a#author-text").first.get_attribute("href", timeout=1000)) or ""
            except Exception:
                pass
            # Published relative
            pub_rel = ""
            try:
                pub_rel = (await t.locator("a.yt-simple-endpoint.style-scope.yt-formatted-string").first.inner_text(timeout=1000)).strip()
            except Exception:
                pass

            if not text:
                continue
            author_ident = channel_href or author or ""
            out.append(
                {
                    "author": author,
                    "author_ident": author_ident.strip(),
                    "text": text[:5000],
                    "likes_str": likes_str,
                    "published_at": parse_relative_es(pub_rel, now),
                }
            )
        except Exception:
            continue
    return out


def _parse_likes(s: str) -> int:
    s = (s or "").strip().replace(",", "")
    if not s:
        return 0
    mult = 1
    if s.endswith("K"):
        mult = 1000
        s = s[:-1]
    elif s.endswith("M"):
        mult = 1_000_000
        s = s[:-1]
    try:
        return int(float(s) * mult)
    except ValueError:
        return 0


def top_videos(conn, dirigente_id: int, top_n: int) -> list[tuple[int, str]]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT sp.id, sp.platform_post_id
        FROM social_posts sp
        JOIN social_profiles prof ON prof.id = sp.profile_id
        WHERE prof.platform = 'YOUTUBE'
          AND prof.dirigente_id = %s
          AND sp.platform_post_id IS NOT NULL
          AND sp.platform_post_id != ''
        ORDER BY sp.comments DESC NULLS LAST, sp.views DESC NULLS LAST
        LIMIT %s
        """,
        (dirigente_id, top_n),
    )
    out = [(int(r[0]), str(r[1])) for r in cur.fetchall()]
    cur.close()
    return out


def upsert_comments(conn, parent_db_id: int, video_id: str, comments: list[dict]) -> tuple[int, int]:
    cur = conn.cursor()
    inserted = 0
    skipped = 0
    for c in comments:
        body = c["text"]
        if not body:
            skipped += 1
            continue
        ident = c["author_ident"] or c["author"] or "anon"
        surrogate = hashlib.sha256(f"{video_id}|{ident}|{body[:200]}".encode()).hexdigest()[:32]
        platform_comment_id = f"bdyt-{video_id}-{surrogate}"
        ah = author_hash(ident)
        likes = _parse_likes(c["likes_str"])
        try:
            cur.execute(
                """
                INSERT INTO social_comments
                    (parent_post_id, platform_comment_id, content, author_hash,
                     likes, published_at, is_reply_to_comment, data_source)
                VALUES (%s, %s, %s, %s, %s, %s, false, %s)
                ON CONFLICT (platform_comment_id) DO UPDATE SET
                    content = EXCLUDED.content,
                    likes = EXCLUDED.likes,
                    data_source = EXCLUDED.data_source,
                    updated_at = now()
                """,
                (parent_db_id, platform_comment_id, body, ah, likes, c["published_at"], DATA_SOURCE),
            )
            inserted += 1
        except psycopg2.Error as exc:
            conn.rollback()
            skipped += 1
            print(f"    ! DB error: {exc}")
            cur = conn.cursor()
    conn.commit()
    cur.close()
    return inserted, skipped


async def ingest_dirigente(conn, dirigente_id: int, top_n: int) -> dict:
    vids = top_videos(conn, dirigente_id, top_n)
    if not vids:
        return {"dirigente_id": dirigente_id, "videos": 0, "inserted": 0}
    print(f"\n=== dirigente_id={dirigente_id} — {len(vids)} YT videos ===")
    total_in = 0
    total_sk = 0

    async with brightdata_page() as (_br, ctx, page):
        try:
            await ctx.add_cookies(
                [
                    {
                        "name": "CONSENT",
                        "value": "YES+1",
                        "domain": ".youtube.com",
                        "path": "/",
                    }
                ]
            )
        except Exception as exc:
            print(f"  ! cookie set warn: {exc}")

        for post_db_id, video_id in vids:
            url = f"https://www.youtube.com/watch?v={video_id}&hl=es&gl=MX"
            print(f"  video {video_id}")
            try:
                resp = await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
                if not resp or resp.status >= 400:
                    print(f"    ! HTTP {resp.status if resp else 'None'}, skip")
                    continue
                await page.wait_for_timeout(3500)
                threads = await scroll_until_end(page, SCROLL_ROUNDS)
                print(f"    threads rendered: {threads}")
                comments = await extract_comments(page)
                print(f"    parsed {len(comments)} comments")
                ins, skp = upsert_comments(conn, post_db_id, video_id, comments)
                print(f"    inserted={ins} skipped={skp}")
                total_in += ins
                total_sk += skp
            except Exception as exc:
                print(f"    ! error: {exc!r}")
                continue
    return {
        "dirigente_id": dirigente_id,
        "videos": len(vids),
        "inserted": total_in,
        "skipped": total_sk,
    }


async def main() -> int:
    if len(sys.argv) < 2:
        print(
            "Usage: brightdata_youtube_comments.py <dirigente_id|all> [top_n]\n"
            f"  dirigentes con YT en BD: {SPRINT_B_DIRIGENTES}"
        )
        return 1
    target = sys.argv[1]
    top_n = int(sys.argv[2]) if len(sys.argv) > 2 else TOP_N_VIDEOS

    conn = psycopg2.connect(DB_DSN)
    conn.autocommit = False
    try:
        if target == "all":
            targets = SPRINT_B_DIRIGENTES
        else:
            targets = [int(target)]
        results = [await ingest_dirigente(conn, did, top_n) for did in targets]
        print(f"\n=== FINAL ({DATA_SOURCE}) ===")
        print(json.dumps({"results": results}, indent=2, default=str))
        print(f"Total inserted: {sum(r['inserted'] for r in results)}")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
