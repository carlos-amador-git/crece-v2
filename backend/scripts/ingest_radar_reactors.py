"""ingest_radar_reactors.py · 2026-05-20

Sprint post-ingest Hugo · Fase 1 parcial · solo reactors (ortogonal al Sprint 10
de Marx que arreglará captions FB).

Procesa el dump RADAR en
`/Users/marxchavez/Projects/radar/exports/linda_handoff_20260520_0510/` para
Saymi (dirigente_id=3) y Pepe (dirigente_id=57). Inserts idempotentes:

1. social_posts: UPSERT ON CONFLICT platform_post_id (content=null OK · se
   actualiza cuando Marx termine Sprint 10).
2. watched_profiles: UPSERT ON CONFLICT (dirigente_observador_id, platform,
   profile_external_id).
3. watched_like_events: INSERT ON CONFLICT (watched_profile_id, post_id,
   reaction_type) DO NOTHING.

Reactor → post mapping vía `post_url` (verificado empíricamente: 100% match
vs platform_post_id base64 que no mapea con el numeric post_id en reactors).

Engagement rate normalizado: (likes+comments+shares) / followers_count del
SocialProfile. RADAR entrega valor absoluto.

Uso:
    cd backend
    docker compose exec backend python scripts/ingest_radar_reactors.py --dry-run
    docker compose exec backend python scripts/ingest_radar_reactors.py --commit

Pre-ingest snapshot OBLIGATORIO antes de --commit (postmortem S-8.1).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import asyncpg

import os
DUMP_ROOT = Path(
    os.environ.get("DUMP_ROOT", "/Users/marxchavez/Projects/radar/exports/linda_handoff_20260520_0510")
)

TENANTS = [
    {
        "slug": "saymi-adriana-pineda-velasco",
        "dirigente_id": 3,
        "fb_profile_id": 27,
        "fb_followers": 114000,
        "fb_handle": "saymipinedavelasco",
    },
    {
        "slug": "pepe-monroy",
        "dirigente_id": 57,
        "fb_profile_id": 47,
        "fb_followers": 10970,
        "fb_handle": "PepeMonroyM",
    },
]


def normalize_post_type(rt: str | None) -> str:
    """RADAR usa TEXT/REEL/VIDEO/IMAGE/etc · CRECE PostType enum acepta:
    TEXT/IMAGE/VIDEO/LINK/REEL/STORY/CAROUSEL."""
    if not rt:
        return "TEXT"
    rt = rt.upper().strip()
    if rt in {"TEXT", "IMAGE", "VIDEO", "LINK", "REEL", "STORY", "CAROUSEL"}:
        return rt
    # Fallbacks comunes
    if rt in {"PHOTO", "IMG"}:
        return "IMAGE"
    if rt in {"VID"}:
        return "VIDEO"
    return "TEXT"


def normalize_engagement(post: dict, followers: int) -> float:
    """CRECE usa float ratio. RADAR entrega absoluto (likes+comments+shares).
    Recalculamos para mantener consistencia con baseline BD CRECE."""
    if followers <= 0:
        return 0.0
    interactions = (post.get("likes") or 0) + (post.get("comments") or 0) + (post.get("shares") or 0)
    return interactions / followers


REACTION_MAP = {
    # FB Spanish → CRECE canonical (ck_watched_reaction_type constraint)
    "me gusta": "like",
    "me encanta": "love",
    "me asombra": "wow",
    "me divierte": "haha",
    "me entristece": "sad",
    "me enoja": "angry",
    "me importa": "care",
    "like": "like",
    "love": "love",
    "wow": "wow",
    "haha": "haha",
    "sad": "sad",
    "angry": "angry",
    "support": "support",
    "care": "care",
}


def normalize_reaction(rt: str | None) -> str:
    if not rt:
        return "like"
    return REACTION_MAP.get(rt.lower().strip(), "like")


def normalize_published_at(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except (ValueError, TypeError):
        return None


async def upsert_posts(
    conn: asyncpg.Connection,
    posts: list[dict],
    profile_id: int,
    followers: int,
    handle: str,
    *,
    dry_run: bool,
) -> tuple[int, int, int]:
    """Retorna (inserted, updated, skipped_other_handle)."""
    inserted = 0
    updated = 0
    skipped = 0
    skipped_no_published_at = 0
    for p in posts:
        # Saymi dump trae posts de los 7 targets (1 self + 2 competidoras + 4 más).
        # Solo ingestamos los del handle del dirigente, los demás son competitors
        # que viven en otro modelo (competitor_profiles · D-COMPETIDORES-LIGHTWEIGHT-DIRECTORY-1).
        if p.get("handle") != handle:
            skipped += 1
            continue

        platform_post_id = p["platform_post_id"]
        published_at = normalize_published_at(p.get("published_at"))

        # social_posts.published_at es NOT NULL. ~50% FB reels dump no traen este
        # campo (limit FB API · Marx caveat). Skipear sin perder watched_like_events
        # downstream (reactors apuntan via post_url · esos posts skip = sus reactors
        # también skip downstream con skipped_no_post_in_bd flag).
        if published_at is None:
            skipped_no_published_at += 1
            continue
        post_type = normalize_post_type(p.get("post_type"))
        er = normalize_engagement(p, followers)
        content = p.get("content")  # null OK para FB · Sprint 10 Marx llenará después

        if dry_run:
            # Check existence
            existing = await conn.fetchval(
                "SELECT id FROM social_posts WHERE platform_post_id = $1",
                platform_post_id,
            )
            if existing:
                updated += 1
            else:
                inserted += 1
            continue

        result = await conn.fetchrow(
            """
            INSERT INTO social_posts (
                profile_id, platform_post_id, content, post_type,
                published_at, likes, comments, shares, views,
                engagement_rate, scraped_at, is_political
            ) VALUES (
                $1, $2, $3, $4::post_type_enum,
                $5, $6, $7, $8, $9,
                $10, $11, FALSE
            )
            ON CONFLICT (platform_post_id) DO UPDATE SET
                content = COALESCE(EXCLUDED.content, social_posts.content),
                likes = EXCLUDED.likes,
                comments = EXCLUDED.comments,
                shares = EXCLUDED.shares,
                views = EXCLUDED.views,
                engagement_rate = EXCLUDED.engagement_rate,
                scraped_at = EXCLUDED.scraped_at,
                post_type = EXCLUDED.post_type,
                published_at = COALESCE(EXCLUDED.published_at, social_posts.published_at)
            RETURNING (xmax = 0) AS inserted_now
            """,
            profile_id,
            platform_post_id,
            content,
            post_type,
            published_at,
            p.get("likes") or 0,
            p.get("comments") or 0,
            p.get("shares") or 0,
            p.get("views") or 0,
            er,
            datetime.now(UTC),
        )
        if result and result["inserted_now"]:
            inserted += 1
        else:
            updated += 1

    return inserted, updated, skipped, skipped_no_published_at


async def build_post_url_to_id_map(
    conn: asyncpg.Connection, profile_id: int
) -> dict[str, int]:
    """Lookup post_url → social_posts.id para profiles del dirigente."""
    # Tabla NO tiene columna post_url. Pero tiene platform_post_id.
    # El JSON de reactors usa post_url como llave común con el JSON de posts.
    # Sigue el approach: hacer match en RAM (JSON-side) entre reactors.post_url
    # y posts.post_url, extraer platform_post_id de posts, mapear a id de BD.
    rows = await conn.fetch(
        "SELECT id, platform_post_id FROM social_posts WHERE profile_id = $1",
        profile_id,
    )
    return {r["platform_post_id"]: r["id"] for r in rows}


async def upsert_watched_profiles_and_events(
    conn: asyncpg.Connection,
    reactors: list[dict],
    posts: list[dict],
    *,
    dirigente_id: int,
    profile_id: int,
    handle: str,
    dry_run: bool,
) -> dict[str, int]:
    """Procesa reactors en batch.

    Estrategia mapping reactor → post:
    1. Construir índice post_url → platform_post_id desde posts.json (solo del handle).
    2. Construir índice platform_post_id → social_posts.id desde BD.
    3. Para cada reactor, lookup reactor.post_url → platform_post_id → social_posts.id.
    4. UPSERT watched_profiles (dedup por reactor_hash).
    5. INSERT watched_like_events ON CONFLICT DO NOTHING.
    """
    stats = {
        "reactors_total": len(reactors),
        "skipped_other_post": 0,
        "skipped_no_post_in_bd": 0,
        "watched_profiles_inserted": 0,
        "watched_profiles_existed": 0,
        "events_inserted": 0,
        "events_existed": 0,
    }

    # 1. Mapping post_url → platform_post_id solo del handle objetivo
    posts_by_url: dict[str, str] = {}
    for p in posts:
        if p.get("handle") != handle:
            continue
        url = p.get("post_url")
        if url:
            posts_by_url[url] = p["platform_post_id"]

    # 2. Mapping platform_post_id → social_posts.id desde BD
    bd_post_map = await build_post_url_to_id_map(conn, profile_id)

    # 3. Procesar reactors
    # First pass: dedup watched_profiles por reactor_hash
    reactor_hashes: dict[str, dict] = {}
    for r in reactors:
        rh = r.get("reactor_hash")
        if rh and rh not in reactor_hashes:
            reactor_hashes[rh] = {
                "display_name": r.get("reactor_display_name"),
                "platform_external_id": r.get("platform_reactor_id"),
            }

    # Insert/upsert watched_profiles
    if not dry_run:
        for rh, meta in reactor_hashes.items():
            result = await conn.fetchrow(
                """
                INSERT INTO watched_profiles (
                    dirigente_observador_id, platform, profile_external_id,
                    display_name, source, tags, is_active, author_hash
                ) VALUES (
                    $1, 'FACEBOOK', $2, $3, 'auto_suggested', '[]'::jsonb, TRUE, $4
                )
                ON CONFLICT (dirigente_observador_id, platform, profile_external_id) DO UPDATE SET
                    display_name = COALESCE(EXCLUDED.display_name, watched_profiles.display_name),
                    updated_at = now()
                RETURNING (xmax = 0) AS inserted_now
                """,
                dirigente_id,
                rh[:100],  # profile_external_id varchar(100) max
                meta["display_name"],
                rh,
            )
            if result and result["inserted_now"]:
                stats["watched_profiles_inserted"] += 1
            else:
                stats["watched_profiles_existed"] += 1
    else:
        for rh in reactor_hashes:
            existing = await conn.fetchval(
                "SELECT id FROM watched_profiles WHERE dirigente_observador_id=$1 AND platform='FACEBOOK' AND profile_external_id=$2",
                dirigente_id,
                rh[:100],
            )
            if existing:
                stats["watched_profiles_existed"] += 1
            else:
                stats["watched_profiles_inserted"] += 1

    # 4. Build mapping reactor_hash → watched_profile_id (fresh from BD post-upsert)
    wp_rows = await conn.fetch(
        "SELECT id, profile_external_id FROM watched_profiles WHERE dirigente_observador_id=$1 AND platform='FACEBOOK'",
        dirigente_id,
    )
    hash_to_wp_id = {r["profile_external_id"]: r["id"] for r in wp_rows}

    # 5. Insert watched_like_events (con dedup por uq constraint)
    for r in reactors:
        url = r.get("post_url")
        if not url:
            stats["skipped_other_post"] += 1
            continue
        platform_post_id = posts_by_url.get(url)
        if not platform_post_id:
            stats["skipped_other_post"] += 1
            continue
        bd_post_id = bd_post_map.get(platform_post_id)
        if not bd_post_id:
            stats["skipped_no_post_in_bd"] += 1
            continue
        rh = r.get("reactor_hash")
        wp_id = hash_to_wp_id.get(rh[:100]) if rh else None
        if not wp_id:
            stats["skipped_other_post"] += 1
            continue

        if dry_run:
            existing = await conn.fetchval(
                "SELECT id FROM watched_like_events WHERE watched_profile_id=$1 AND post_id=$2 AND reaction_type=$3",
                wp_id,
                bd_post_id,
                normalize_reaction(r.get("reaction_type")),
            )
            if existing:
                stats["events_existed"] += 1
            else:
                stats["events_inserted"] += 1
            continue

        try:
            await conn.execute(
                """
                INSERT INTO watched_like_events (
                    watched_profile_id, post_id, reaction_type, source, detected_at
                ) VALUES ($1, $2, $3, 'other_scraper', now())
                ON CONFLICT (watched_profile_id, post_id, reaction_type) DO NOTHING
                """,
                wp_id,
                bd_post_id,
                normalize_reaction(r.get("reaction_type")),
            )
            stats["events_inserted"] += 1
        except Exception as e:
            print(f"  ⚠ event insert failed: wp={wp_id} post={bd_post_id} err={e}")
            stats["skipped_other_post"] += 1

    return stats


async def main(*, dry_run: bool) -> int:
    print(f"\n=== INGEST RADAR REACTORS · dry_run={dry_run} ===\n")

    # Adentro del container: hostname 'db' port 5432. Fuera: localhost:5438.
    import os
    host = os.environ.get("DB_HOST", "db")
    port = int(os.environ.get("DB_PORT", "5432"))
    conn = await asyncpg.connect(
        host=host, port=port, user="crece", password="crece_dev", database="crece"
    )
    try:
        for tenant in TENANTS:
            print(f"\n── {tenant['slug']} (dirigente_id={tenant['dirigente_id']}) ──")

            posts_path = DUMP_ROOT / tenant["slug"] / "posts.json"
            reactors_path = DUMP_ROOT / tenant["slug"] / "reactors.json"
            with open(posts_path) as f:
                posts = json.load(f)
            with open(reactors_path) as f:
                reactors = json.load(f)

            print(f"  loaded posts={len(posts)} reactors={len(reactors)}")

            # 1. Posts
            ins, upd, skip, skip_no_pub = await upsert_posts(
                conn, posts, tenant["fb_profile_id"], tenant["fb_followers"],
                tenant["fb_handle"], dry_run=dry_run,
            )
            print(f"  posts: inserted={ins} updated={upd} skipped_other_handle={skip} skipped_no_published_at={skip_no_pub}")

            # 2. Reactors + watched_profiles + watched_like_events
            stats = await upsert_watched_profiles_and_events(
                conn, reactors, posts,
                dirigente_id=tenant["dirigente_id"],
                profile_id=tenant["fb_profile_id"],
                handle=tenant["fb_handle"],
                dry_run=dry_run,
            )
            for k, v in stats.items():
                print(f"  {k}: {v}")

    finally:
        await conn.close()
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit", action="store_true", help="Real ingest (omit for dry-run)")
    args = parser.parse_args()
    sys.exit(asyncio.run(main(dry_run=not args.commit)))
