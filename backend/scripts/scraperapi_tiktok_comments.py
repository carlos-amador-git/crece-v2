"""ScraperAPI-based TikTok comments scraper → social_comments.

Ruta: TikTok API interna `/api/comment/list/` proxyeada por ScraperAPI.
Endpoint funciona desde container (sin bloqueo Docker IP vs libs Playwright).

Paginación: cursor ++20 hasta ``has_more=0`` o hasta cap de ``MAX_COMMENTS_PER_VIDEO``.
Autor persistido como SHA256(platform+commenter_id+SALT) — LFPDPPP compliant.

Uso:
    python scripts/scraperapi_tiktok_comments.py <dirigente_id> [top_n]
    python scripts/scraperapi_tiktok_comments.py all [top_n]   # los 5 pendientes

``data_source`` lógico: 'scraperapi-tiktok-api-v1'. La tabla social_comments no
tiene columna data_source todavía — queda registrado en el log + en este docstring.
Si Carlos decide añadirla como migration futura, se puede backfill por author_hash
pattern o por created_at window.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import urllib.parse
from datetime import UTC, datetime
from pathlib import Path

import psycopg2
import requests

ENV_FILE = Path(__file__).parent.parent / ".env.scraping-keys"
if ENV_FILE.exists():
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

API_KEY = os.environ["SCRAPERAPI_KEY"]
DB_DSN = os.environ.get(
    "DB_DSN",
    "host=localhost port=5438 dbname=crece user=crece password=crece_dev",
)
HASH_SALT = os.environ.get("COMMENT_AUTHOR_SALT")
if not HASH_SALT:
    raise RuntimeError("COMMENT_AUTHOR_SALT env var obligatoria (LFPDPPP).")

MAX_COMMENTS_PER_VIDEO = int(os.environ.get("MAX_COMMENTS_PER_VIDEO", "200"))
DEFAULT_TOP_N = int(os.environ.get("TOP_N_VIDEOS", "10"))
COMMENTS_PER_PAGE = 20
REQUEST_TIMEOUT = 90
SLEEP_BETWEEN = 1.5  # ser amables con el rate limit

# Dirigentes objetivo del Sprint B (por ID en BD crece)
SPRINT_B_DIRIGENTES = [2, 3, 4, 5, 6]  # Solano, Pineda, Nolasco, Jiménez, Cravioto

DATA_SOURCE = "scraperapi-tiktok-api-v1"


def author_hash(commenter_id: str | None) -> str:
    raw = f"TIKTOK:{commenter_id or 'anon'}:{HASH_SALT}"
    return hashlib.sha256(raw.encode()).hexdigest()


def fetch_comments_page(aweme_id: str, cursor: int) -> dict | None:
    api_url = (
        "https://www.tiktok.com/api/comment/list/"
        f"?aweme_id={aweme_id}&cursor={cursor}&count={COMMENTS_PER_PAGE}&aid=1988"
    )
    proxied = (
        "https://api.scraperapi.com/"
        f"?api_key={API_KEY}&url={urllib.parse.quote(api_url, safe='')}"
    )
    try:
        resp = requests.get(proxied, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        print(f"    ! request failure cursor={cursor}: {exc}")
        return None
    if resp.status_code != 200:
        print(f"    ! HTTP {resp.status_code} cursor={cursor} body[:120]={resp.text[:120]!r}")
        return None
    try:
        return resp.json()
    except ValueError:
        print(f"    ! non-JSON cursor={cursor} body[:120]={resp.text[:120]!r}")
        return None


def fetch_all_comments(aweme_id: str) -> list[dict]:
    collected: list[dict] = []
    cursor = 0
    while len(collected) < MAX_COMMENTS_PER_VIDEO:
        page = fetch_comments_page(aweme_id, cursor)
        if not page:
            break
        items = page.get("comments") or []
        if not items:
            break
        collected.extend(items)
        if page.get("has_more") != 1:
            break
        next_cursor = page.get("cursor")
        if not isinstance(next_cursor, int) or next_cursor <= cursor:
            break
        cursor = next_cursor
        time.sleep(SLEEP_BETWEEN)
    return collected[:MAX_COMMENTS_PER_VIDEO]


def upsert_comments(
    conn, parent_db_id: int, raw_comments: list[dict]
) -> tuple[int, int]:
    cur = conn.cursor()
    inserted = 0
    skipped = 0
    for item in raw_comments:
        cid = str(item.get("cid") or "").strip()
        text = (item.get("text") or "").strip()
        if not cid or not text:
            skipped += 1
            continue
        commenter_id = (item.get("user") or {}).get("uid") or item.get("user_id")
        ah = author_hash(str(commenter_id) if commenter_id else None)
        likes = int(item.get("digg_count") or 0)
        ts = item.get("create_time")
        published_at = (
            datetime.fromtimestamp(int(ts), tz=UTC) if isinstance(ts, int) and ts > 0 else None
        )
        is_reply = bool(item.get("reply_id")) and item.get("reply_id") != "0"
        try:
            cur.execute(
                """
                INSERT INTO social_comments
                    (parent_post_id, platform_comment_id, content, author_hash,
                     likes, published_at, is_reply_to_comment)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (platform_comment_id) DO UPDATE SET
                    likes = EXCLUDED.likes,
                    content = EXCLUDED.content,
                    updated_at = now()
                """,
                (parent_db_id, cid, text[:5000], ah, likes, published_at, is_reply),
            )
            inserted += 1
        except psycopg2.Error as exc:
            conn.rollback()
            skipped += 1
            print(f"    ! DB error cid={cid}: {exc}")
            cur = conn.cursor()
    conn.commit()
    cur.close()
    return inserted, skipped


def top_videos(conn, dirigente_id: int, top_n: int) -> list[tuple[int, str]]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT sp.id, sp.platform_post_id
        FROM social_posts sp
        JOIN social_profiles prof ON prof.id = sp.profile_id
        WHERE prof.platform = 'TIKTOK'
          AND prof.dirigente_id = %s
          AND sp.platform_post_id IS NOT NULL
          AND sp.platform_post_id != ''
        ORDER BY sp.engagement_rate DESC NULLS LAST, sp.likes DESC NULLS LAST
        LIMIT %s
        """,
        (dirigente_id, top_n),
    )
    rows = cur.fetchall()
    cur.close()
    return [(int(r[0]), str(r[1])) for r in rows]


def run_for_dirigente(conn, dirigente_id: int, top_n: int) -> dict:
    videos = top_videos(conn, dirigente_id, top_n)
    if not videos:
        return {"dirigente_id": dirigente_id, "videos": 0, "inserted": 0, "skipped": 0}
    print(f"\n=== dirigente_id={dirigente_id} — top {len(videos)} TikTok videos ===")
    total_inserted = 0
    total_skipped = 0
    for post_db_id, aweme_id in videos:
        print(f"  video aweme_id={aweme_id} post_db_id={post_db_id}")
        comments = fetch_all_comments(aweme_id)
        print(f"    fetched {len(comments)} comments")
        ins, skp = upsert_comments(conn, post_db_id, comments)
        print(f"    inserted={ins} skipped={skp}")
        total_inserted += ins
        total_skipped += skp
    return {
        "dirigente_id": dirigente_id,
        "videos": len(videos),
        "inserted": total_inserted,
        "skipped": total_skipped,
    }


def main() -> int:
    if len(sys.argv) < 2:
        print(
            "Usage: scraperapi_tiktok_comments.py <dirigente_id|all> [top_n]\n"
            f"  SPRINT_B_DIRIGENTES = {SPRINT_B_DIRIGENTES}\n"
            f"  MAX_COMMENTS_PER_VIDEO = {MAX_COMMENTS_PER_VIDEO}\n"
            f"  default top_n = {DEFAULT_TOP_N}"
        )
        return 1
    target = sys.argv[1]
    top_n = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_TOP_N

    conn = psycopg2.connect(DB_DSN)
    try:
        if target == "all":
            targets = SPRINT_B_DIRIGENTES
        else:
            targets = [int(target)]
        results = [run_for_dirigente(conn, did, top_n) for did in targets]
        print(f"\n=== FINAL ({DATA_SOURCE}) ===")
        print(json.dumps({"results": results}, indent=2))
        total = sum(r["inserted"] for r in results)
        print(f"\nTotal comments inserted: {total}")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
