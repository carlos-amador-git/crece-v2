"""ingest_competencia_saymi.py · 2026-05-22

Ingest FB competencia Saymi (Ivette + Susana) · shape RADAR v3.
Hugo entregó hoy ~14:10 UTC en /Users/marxchavez/Projects/radar/exports/saymi_competencia_2026-05-22/

Mapping CRECE:
- IvetteMoranDeMurat → social_profile id=48, dirigente id=58
- susanaharpiturribarria → social_profile id=49, dirigente id=59
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import asyncpg

EXPORTS = Path("/Users/marxchavez/Projects/radar/exports/saymi_competencia_2026-05-22")
DSN = os.environ.get("DATABASE_URL_RAW", "postgresql://crece:crece_dev@localhost:5438/crece")

PROFILES = {
    "susanaharpiturribarria": {"profile_id": 49, "dirigente_id": 59},
    "IvetteMoranDeMurat": {"profile_id": 48, "dirigente_id": 58},
}


def author_hash(platform: str, key: str) -> str:
    salt = os.environ.get("AUTHOR_SALT", "radar_v3_2026")
    return hashlib.sha256(f"{platform}_{key}_{salt}".encode()).hexdigest()


def to_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


async def ingest_posts(conn: asyncpg.Connection, handle: str) -> Counter:
    path = EXPORTS / f"{handle}_posts.json"
    with path.open() as f:
        data = json.load(f)
    items = data.get("items", [])
    mapping = PROFILES[handle]
    profile_id = mapping["profile_id"]

    c = Counter()
    for it in items:
        pp = str(it["platform_entity_id"])
        p = it.get("payload") or {}
        content = (p.get("text") or p.get("content") or p.get("caption") or "").strip()
        url = p.get("url") or p.get("post_url") or ""
        # Hugo emite likes_count/comments_count/shares_count (plural con guión bajo)
        # · NO like_count/comment_count/share_count (singular). Aceptar ambos.
        likes = int(p.get("likes_count") or p.get("reaction_count") or p.get("like_count") or 0)
        comments_n = int(p.get("comments_count") or p.get("comment_count") or 0)
        shares = int(p.get("shares_count") or p.get("share_count") or p.get("shares") or 0)
        views = int(p.get("views") or p.get("view_count") or 0)
        time_iso = p.get("time_iso") or p.get("published_at") or p.get("timestamp")
        published_at = to_dt(time_iso) or to_dt(it.get("detected_at"))

        raw_data = {**p, "url": url, "caption_source": "radar-fb-claude-extension-v1"}
        try:
            r = await conn.execute(
                """
                INSERT INTO social_posts (
                    profile_id, platform_post_id, content, post_type,
                    published_at, likes, comments, shares, views,
                    engagement_rate, raw_data, scraped_at, is_political
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 0, $10, NOW(), false)
                ON CONFLICT (platform_post_id) DO UPDATE SET
                  likes = EXCLUDED.likes,
                  comments = EXCLUDED.comments,
                  shares = EXCLUDED.shares,
                  views = EXCLUDED.views,
                  scraped_at = NOW()
                """,
                profile_id, pp, content[:5000], "TEXT", published_at,
                likes, comments_n, shares, views,
                json.dumps(raw_data, ensure_ascii=False, default=str),
            )
            if "INSERT" in r:
                c["inserted"] += 1
            else:
                c["updated"] += 1
        except Exception as e:
            print(f"  [err post {pp}] {e}", file=sys.stderr)
            c["err"] += 1
    return c


async def ingest_reactors(conn: asyncpg.Connection, handle: str) -> Counter:
    path = EXPORTS / f"{handle}_reactors.json"
    with path.open() as f:
        data = json.load(f)
    items = data.get("items", [])
    mapping = PROFILES[handle]
    dirigente_id = mapping["dirigente_id"]

    if not items:
        return Counter({"empty": 1})

    # Get org_id of dirigente
    org_row = await conn.fetchrow("SELECT org_id FROM dirigentes WHERE id = $1", dirigente_id)
    org_id = org_row["org_id"]

    # Reactor post_id es numérico FB · platform_post_id en BD es base64 RADAR.
    # Decodifico el base64 para extraer numérico (último segmento de "S:_I{uid}:{pid}:{pid}").
    import base64
    c = Counter()
    all_posts_rows = await conn.fetch(
        """
        SELECT sp.platform_post_id, sp.id FROM social_posts sp
        JOIN social_profiles sps ON sps.id = sp.profile_id
        WHERE sps.dirigente_id = $1
        """,
        dirigente_id,
    )
    numeric_to_post: dict[str, int] = {}
    for r in all_posts_rows:
        pp = r["platform_post_id"]
        try:
            decoded = base64.b64decode(pp).decode()
            numeric = decoded.split(":")[-1]
            numeric_to_post[numeric] = r["id"]
        except Exception:
            numeric_to_post[pp] = r["id"]  # fallback raw
    pp_ids = sorted({str(it["payload"].get("post_id") or "") for it in items})
    pp_ids = [p for p in pp_ids if p]
    matched = [p for p in pp_ids if p in numeric_to_post]
    print(f"  [reactors {handle}] {len(matched)}/{len(pp_ids)} posts resueltos (decode b64)")
    pp_to_post = {p: numeric_to_post[p] for p in matched}

    # WP map (author_hash → watched_profile_id)
    # Reactores competencia tienen reactor_id/reactor_username (no author_*) · adaptar.
    unique_authors: dict[str, str] = {}
    for it in items:
        p = it.get("payload") or {}
        key = (
            p.get("reactor_id") or p.get("reactor_username")
            or p.get("author_username") or p.get("author_id") or "anon"
        )
        ah = p.get("author_hash") or author_hash("FACEBOOK", str(key))
        unique_authors[ah] = p.get("reactor_display_name") or p.get("author_display_name") or str(key)

    for ah, display in unique_authors.items():
        await conn.execute(
            """
            INSERT INTO watched_profiles (
                dirigente_observador_id, org_id, platform, profile_external_id,
                display_name, source, tags, is_active, author_hash, created_at, updated_at
            )
            VALUES ($1, $2, 'FACEBOOK', $3, $4, 'auto_suggested', '[]'::jsonb, true, $5, NOW(), NOW())
            ON CONFLICT (dirigente_observador_id, platform, profile_external_id) DO UPDATE SET
              author_hash = EXCLUDED.author_hash, updated_at = NOW()
            """,
            dirigente_id, org_id, ah, display, ah,
        )
        c["wp_upsert"] += 1

    wp_rows = await conn.fetch(
        "SELECT id, author_hash FROM watched_profiles WHERE dirigente_observador_id=$1 AND author_hash=ANY($2::text[])",
        dirigente_id, list(unique_authors.keys()),
    )
    ah_to_wp = {r["author_hash"]: r["id"] for r in wp_rows}

    batch = []
    for it in items:
        p = it.get("payload") or {}
        pp = str(p.get("post_id") or it.get("platform_entity_id") or "")
        post_id = pp_to_post.get(pp)
        if not post_id:
            c["skip_no_post"] += 1
            continue
        key = (
            p.get("reactor_id") or p.get("reactor_username")
            or p.get("author_username") or p.get("author_id") or "anon"
        )
        ah = p.get("author_hash") or author_hash("FACEBOOK", str(key))
        wp_id = ah_to_wp.get(ah)
        if not wp_id:
            c["skip_no_wp"] += 1
            continue
        reaction = p.get("reaction_type", "like")
        if reaction not in ("like", "love", "wow", "haha", "sad", "angry", "support", "care"):
            reaction = "like"
        detected_at = to_dt(it.get("detected_at")) or datetime.now()
        batch.append((wp_id, post_id, reaction, detected_at, "other_scraper"))

    for i in range(0, len(batch), 500):
        chunk = batch[i:i + 500]
        await conn.executemany(
            """
            INSERT INTO watched_like_events (watched_profile_id, post_id, reaction_type, detected_at, source)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (watched_profile_id, post_id, reaction_type) DO NOTHING
            """,
            chunk,
        )
        c["events_attempted"] += len(chunk)
    return c


async def update_profile_counts(conn: asyncpg.Connection, profile_id: int):
    """Update social_profiles.posts_count desde social_posts real."""
    await conn.execute(
        """
        UPDATE social_profiles
        SET posts_count = (SELECT COUNT(*) FROM social_posts WHERE profile_id = $1)
        WHERE id = $1
        """,
        profile_id,
    )


async def main() -> int:
    conn = await asyncpg.connect(DSN)
    print(f"Ingest competencia Saymi · 2 dirigentes")
    results = {}
    for handle in PROFILES.keys():
        print(f"\n=== {handle} ===")
        results[f"{handle}_posts"] = await ingest_posts(conn, handle)
        results[f"{handle}_reactors"] = await ingest_reactors(conn, handle)
        await update_profile_counts(conn, PROFILES[handle]["profile_id"])
    await conn.close()
    print("\n===== RESULT =====")
    for k, v in results.items():
        print(f"  {k}: {dict(v)}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
