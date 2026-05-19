"""Ingesta de comments Facebook via Brightdata Scraping Browser.

Conecta Playwright a Brightdata Browser API (IP residencial + anti-bot).
Abre post público FB, parsea comments visibles, upsert a social_comments.

Cap por post: 50 comments (ajustable via env FB_MAX_COMMENTS_PER_POST).
Top-N posts por dirigente: 10 (ajustable via TOP_N_POSTS).
LFPDPPP: author_hash SHA256, NO persist PII crudos.

Uso:
    python scripts/brightdata_facebook_comments.py <dirigente_id|all> [top_n]
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
HASH_SALT = os.environ.get("COMMENT_AUTHOR_SALT")
if not HASH_SALT:
    raise RuntimeError("COMMENT_AUTHOR_SALT env var obligatoria.")

MAX_COMMENTS_PER_POST = int(os.environ.get("FB_MAX_COMMENTS_PER_POST", "50"))
TOP_N_POSTS = int(os.environ.get("TOP_N_POSTS", "10"))
SCROLL_ROUNDS = int(os.environ.get("FB_SCROLL_ROUNDS", "5"))

DATA_SOURCE = "brightdata-fb-browser-v1"

# dirigente_ids con perfil FB conocido en BD (query inicial mostró 1,4,5,6).
SPRINT_B_DIRIGENTES = [1, 4, 5, 6]


# ──────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────


def author_hash(name: str | None) -> str:
    raw = f"FACEBOOK:{name or 'anon'}:{HASH_SALT}"
    return hashlib.sha256(raw.encode()).hexdigest()


RELATIVE_TIME_RE = re.compile(
    r"\b(\d+)\s*(s|m|min|h|hr|d|day|w|sem|mo|mes|y|año)\b", re.IGNORECASE
)


def parse_relative_time(text: str, now: datetime) -> datetime | None:
    """FB timestamps relativos tipo '5w', '3d', '2h'."""
    m = RELATIVE_TIME_RE.search(text or "")
    if not m:
        return None
    n = int(m.group(1))
    unit = m.group(2).lower()
    delta = None
    if unit in {"s"}:
        delta = timedelta(seconds=n)
    elif unit in {"m", "min"}:
        delta = timedelta(minutes=n)
    elif unit in {"h", "hr"}:
        delta = timedelta(hours=n)
    elif unit in {"d", "day"}:
        delta = timedelta(days=n)
    elif unit in {"w", "sem"}:
        delta = timedelta(weeks=n)
    elif unit in {"mo", "mes"}:
        delta = timedelta(days=n * 30)
    elif unit in {"y", "año"}:
        delta = timedelta(days=n * 365)
    return (now - delta) if delta else None


async def extract_comments_from_page(page, post_main_text: str) -> list[dict]:
    """Itera los [role="article"] skippeando el principal y devuelve dicts."""
    articles = await page.locator('[role="article"]').all()
    out: list[dict] = []
    now = datetime.now(UTC)
    for art in articles:
        try:
            txt = await art.inner_text(timeout=2500)
        except Exception:
            continue
        if not txt:
            continue
        # Heurística: el primer article suele ser el post principal.
        # Lo identificamos porque su prefijo coincide con el inner text del post.
        if post_main_text and txt.startswith(post_main_text[:40]):
            continue
        # Primer span/strong del article suele ser el autor (link al perfil).
        author = ""
        try:
            author = await art.locator(
                "h3 a[role='link'], [role='link'] strong, strong"
            ).first.inner_text(timeout=1500)
        except Exception:
            pass
        author = (author or "").strip()
        # Cuerpo: primer div[dir="auto"] después del autor
        body = ""
        try:
            body = await art.locator("div[dir='auto']").first.inner_text(
                timeout=1500
            )
        except Exception:
            pass
        body = (body or "").strip()
        if not body and txt:
            # Fallback: strip author del inner_text completo
            if author and txt.startswith(author):
                body = txt[len(author):].strip()
            else:
                body = txt.strip()
        # Timestamp: busca cadenas relativas en el bloque
        ts = parse_relative_time(txt, now)

        if not author and not body:
            continue
        # Filtro: comentarios con len >= 2 caracteres útiles
        if len(body) < 2:
            continue
        out.append(
            {
                "author": author[:200],
                "text": body[:5000],
                "published_at": ts,
                # FB no expone el comment_id estable sin API. Hash (post_id, author, text)
                # como surrogate. No perfecto pero determinista → ON CONFLICT funciona.
            }
        )
        if len(out) >= MAX_COMMENTS_PER_POST:
            break
    return out


async def try_load_more(page) -> None:
    """FB suele tener botones 'Ver más comentarios' o 'View more comments'."""
    for _ in range(3):
        # Scroll progresivo
        await page.mouse.wheel(0, 3000)
        await page.wait_for_timeout(1800)
        # Intento click en cualquier "Ver más" o "View more"
        selectors = [
            "div[role='button']:has-text('Ver más comentarios')",
            "div[role='button']:has-text('View more comments')",
            "div[role='button']:has-text('Ver respuestas')",
        ]
        for sel in selectors:
            try:
                loc = page.locator(sel).first
                if await loc.count() and await loc.is_visible(timeout=800):
                    await loc.click(timeout=2000)
                    await page.wait_for_timeout(2000)
            except Exception:
                pass


# ──────────────────────────────────────────────────────────────────
# BD helpers
# ──────────────────────────────────────────────────────────────────


def top_posts_for_dirigente(conn, dirigente_id: int, limit: int) -> list[tuple[int, str, str]]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT sp.id, sp.platform_post_id, prof.handle
        FROM social_posts sp
        JOIN social_profiles prof ON prof.id = sp.profile_id
        WHERE prof.platform = 'FACEBOOK'
          AND prof.dirigente_id = %s
          AND sp.platform_post_id IS NOT NULL
        ORDER BY sp.comments DESC NULLS LAST, sp.likes DESC NULLS LAST
        LIMIT %s
        """,
        (dirigente_id, limit),
    )
    out = []
    for row in cur.fetchall():
        raw_pid = str(row[1])
        # platform_post_id en BD viene con prefix bd_fb_ (brightdata dataset).
        clean_pid = raw_pid.removeprefix("bd_fb_")
        out.append((int(row[0]), clean_pid, str(row[2])))
    cur.close()
    return out


def upsert_comments(
    conn, parent_db_id: int, post_platform_id: str, comments: list[dict]
) -> tuple[int, int]:
    cur = conn.cursor()
    inserted = 0
    skipped = 0
    for c in comments:
        author = c["author"]
        body = c["text"]
        if not body:
            skipped += 1
            continue
        surrogate_hash = hashlib.sha256(
            f"{post_platform_id}|{author}|{body[:200]}".encode()
        ).hexdigest()[:32]
        comment_id = f"bdfb-{post_platform_id}-{surrogate_hash}"
        ah = author_hash(author)
        published_at = c.get("published_at")
        try:
            cur.execute(
                """
                INSERT INTO social_comments
                    (parent_post_id, platform_comment_id, content, author_hash,
                     likes, published_at, is_reply_to_comment, data_source)
                VALUES (%s, %s, %s, %s, %s, %s, false, %s)
                ON CONFLICT (platform_comment_id) DO UPDATE SET
                    content = EXCLUDED.content,
                    data_source = EXCLUDED.data_source,
                    updated_at = now()
                """,
                (parent_db_id, comment_id, body, ah, 0, published_at, DATA_SOURCE),
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


# ──────────────────────────────────────────────────────────────────
# Orquestación
# ──────────────────────────────────────────────────────────────────


async def ingest_dirigente(conn, dirigente_id: int, top_n: int) -> dict:
    posts = top_posts_for_dirigente(conn, dirigente_id, top_n)
    if not posts:
        return {"dirigente_id": dirigente_id, "posts": 0, "inserted": 0, "skipped": 0}
    print(f"\n=== dirigente_id={dirigente_id} — {len(posts)} FB posts ===")
    total_inserted = 0
    total_skipped = 0

    async with brightdata_page() as (_br, _ctx, page):
        for post_db_id, post_platform_id, handle in posts:
            url = f"https://www.facebook.com/{handle}/posts/{post_platform_id}"
            print(f"  post {post_platform_id[:12]}... url={url[:60]}...")
            try:
                resp = await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
                if not resp or resp.status >= 400:
                    print(f"    ! HTTP {resp.status if resp else 'None'}, skip")
                    continue
                await page.wait_for_timeout(3500)
                await try_load_more(page)
                # Texto del post principal (primer article)
                post_main_text = ""
                try:
                    post_main_text = await page.locator('[role="article"]').first.inner_text(
                        timeout=2500
                    )
                except Exception:
                    pass
                comments = await extract_comments_from_page(page, post_main_text)
                print(f"    parsed {len(comments)} comments")
                ins, skp = upsert_comments(conn, post_db_id, post_platform_id, comments)
                print(f"    inserted={ins} skipped={skp}")
                total_inserted += ins
                total_skipped += skp
            except Exception as exc:
                print(f"    ! error: {exc!r}")
                continue

    return {
        "dirigente_id": dirigente_id,
        "posts": len(posts),
        "inserted": total_inserted,
        "skipped": total_skipped,
    }


async def main() -> int:
    if len(sys.argv) < 2:
        print(
            "Usage: brightdata_facebook_comments.py <dirigente_id|all> [top_n]\n"
            f"  dirigentes con FB en BD: {SPRINT_B_DIRIGENTES}"
        )
        return 1
    target = sys.argv[1]
    top_n = int(sys.argv[2]) if len(sys.argv) > 2 else TOP_N_POSTS

    conn = psycopg2.connect(DB_DSN)
    conn.autocommit = False
    try:
        if target == "all":
            targets = SPRINT_B_DIRIGENTES
        else:
            targets = [int(target)]
        results = []
        for did in targets:
            res = await ingest_dirigente(conn, did, top_n)
            results.append(res)
            print(f"\n--- checkpoint: {res} ---")
        print(f"\n=== FINAL ({DATA_SOURCE}) ===")
        print(json.dumps({"results": results}, indent=2, default=str))
        total = sum(r["inserted"] for r in results)
        print(f"\nTotal comments inserted: {total}")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
