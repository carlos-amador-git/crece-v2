"""dedupe_posts.py · 2026-05-20 sprint post-ingest Hugo · Bug 1 F2

Detecta posts Saymi+Pepe FB duplicados por (profile_id, content, likes, shares)
y los consolida en la row más antigua (id más bajo). Causa raíz: ingest Apify
previo + RADAR posterior con platform_post_id en formatos distintos (base64 vs
legacy numeric) → UPSERT no detectó match.

Estrategia idempotente:
1. Encontrar grupos de dups.
2. Para cada grupo, designar canonical = MIN(id).
3. Para cada dup (id != canonical):
   a. Migrar social_comments.parent_post_id → canonical (ON CONFLICT DO NOTHING
      por UNIQUE platform_comment_id).
   b. Migrar watched_like_events.post_id → canonical (ON CONFLICT DO NOTHING
      por UNIQUE wp_id+post_id+reaction).
   c. DELETE social_comments huérfanos del dup_id (no migrados).
   d. DELETE watched_like_events huérfanos.
   e. DELETE social_posts WHERE id=dup_id.

Uso:
    docker exec crece-backend python /app/scripts/dedupe_posts.py --dry-run
    docker exec crece-backend python /app/scripts/dedupe_posts.py --commit
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

import asyncpg

DIRIGENTES = [3, 57]


async def find_groups(conn, *, strict: bool = True) -> list[dict]:
    """strict=True: match content exacto. strict=False: solo (likes, shares, comments).

    En modo laxo, canonical es la row con content NOT NULL más completa (longest),
    luego id más bajo como tiebreaker.
    """
    if strict:
        rows = await conn.fetch(
            """
            SELECT sprof.dirigente_id, sp.profile_id, sp.content, sp.likes, sp.shares,
                   ARRAY_AGG(sp.id ORDER BY sp.id) AS ids
            FROM social_posts sp
            JOIN social_profiles sprof ON sp.profile_id = sprof.id
            WHERE sprof.dirigente_id = ANY($1::int[])
              AND sprof.platform = 'FACEBOOK'
              AND sp.content IS NOT NULL
            GROUP BY sprof.dirigente_id, sp.profile_id, sp.content, sp.likes, sp.shares
            HAVING COUNT(*) > 1
            """,
            DIRIGENTES,
        )
    else:
        # Criterio laxo MAS PRECISO (post manual verification):
        # - mismos (likes, shares, comments) en mismo profile
        # - mismo published_at::date (mismo día)
        # - likes > 5 (filtra 0/0/0 ruido)
        # - exactamente UNO de los dos tiene URL en raw_data (señal Apify legacy + RADAR nuevo)
        # Canonical: row con content NOT NULL más largo, luego id menor.
        rows = await conn.fetch(
            """
            SELECT sprof.dirigente_id, sp.profile_id, sp.likes, sp.shares, sp.comments,
                   sp.published_at::date AS pub_date,
                   ARRAY_AGG(sp.id ORDER BY (sp.content IS NULL) ASC, LENGTH(COALESCE(sp.content,'')) DESC, sp.id ASC) AS ids,
                   NULL::text AS content
            FROM social_posts sp
            JOIN social_profiles sprof ON sp.profile_id = sprof.id
            WHERE sprof.dirigente_id = ANY($1::int[])
              AND sprof.platform = 'FACEBOOK'
              AND sp.likes > 5
              AND sp.published_at IS NOT NULL
            GROUP BY sprof.dirigente_id, sp.profile_id, sp.likes, sp.shares, sp.comments, sp.published_at::date
            HAVING COUNT(*) > 1
              -- exactamente UNO de los dups tiene URL
              AND COUNT(*) FILTER (WHERE sp.raw_data->>'url' IS NOT NULL) >= 1
              AND COUNT(*) FILTER (WHERE sp.raw_data->>'url' IS NULL) >= 1
            """,
            DIRIGENTES,
        )
    return [dict(r) for r in rows]


async def merge_group(conn, group: dict, *, dry_run: bool) -> dict:
    ids = group["ids"]
    canonical = ids[0]
    dups = ids[1:]
    stats = {
        "canonical": canonical,
        "dups": dups,
        "comments_migrated": 0,
        "comments_deleted": 0,
        "events_migrated": 0,
        "events_deleted": 0,
        "posts_deleted": 0,
    }

    for dup_id in dups:
        if dry_run:
            # Solo contar
            n_comments = await conn.fetchval(
                "SELECT COUNT(*) FROM social_comments WHERE parent_post_id=$1", dup_id
            )
            n_events = await conn.fetchval(
                "SELECT COUNT(*) FROM watched_like_events WHERE post_id=$1", dup_id
            )
            stats["comments_migrated"] += n_comments  # se intentaría migrar
            stats["events_migrated"] += n_events
            stats["posts_deleted"] += 1
            continue

        # Update statements aprovechan UNIQUE constraints para no duplicar
        # social_comments UNIQUE (platform_comment_id)
        try:
            res = await conn.execute(
                """
                UPDATE social_comments SET parent_post_id=$1
                WHERE parent_post_id=$2
                  AND NOT EXISTS (
                    SELECT 1 FROM social_comments sc2
                    WHERE sc2.parent_post_id=$1
                      AND sc2.platform_comment_id=social_comments.platform_comment_id
                  )
                """,
                canonical, dup_id,
            )
            stats["comments_migrated"] += int(res.split()[-1])
        except Exception as e:
            print(f"    ⚠ comments migrate err dup={dup_id}: {e}")

        # DELETE comments huérfanos (no migrados porque conflict con canonical)
        res = await conn.execute(
            "DELETE FROM social_comments WHERE parent_post_id=$1", dup_id
        )
        stats["comments_deleted"] += int(res.split()[-1])

        # watched_like_events UNIQUE (wp_id, post_id, reaction_type)
        try:
            res = await conn.execute(
                """
                UPDATE watched_like_events SET post_id=$1
                WHERE post_id=$2
                  AND NOT EXISTS (
                    SELECT 1 FROM watched_like_events wle2
                    WHERE wle2.post_id=$1
                      AND wle2.watched_profile_id=watched_like_events.watched_profile_id
                      AND wle2.reaction_type=watched_like_events.reaction_type
                  )
                """,
                canonical, dup_id,
            )
            stats["events_migrated"] += int(res.split()[-1])
        except Exception as e:
            print(f"    ⚠ events migrate err dup={dup_id}: {e}")

        res = await conn.execute(
            "DELETE FROM watched_like_events WHERE post_id=$1", dup_id
        )
        stats["events_deleted"] += int(res.split()[-1])

        res = await conn.execute("DELETE FROM social_posts WHERE id=$1", dup_id)
        stats["posts_deleted"] += int(res.split()[-1])

    return stats


async def main(*, dry_run: bool) -> int:
    print(f"\n=== DEDUPE POSTS · dry_run={dry_run} ===\n")
    host = os.environ.get("DB_HOST", "db")
    port = int(os.environ.get("DB_PORT", "5432"))
    conn = await asyncpg.connect(host=host, port=port, user="crece", password="crece_dev", database="crece")

    try:
        # Detección: primero strict (content+likes+shares idénticos), luego lax (solo likes+shares+comments)
        strict_groups = await find_groups(conn, strict=True)
        lax_groups = await find_groups(conn, strict=False)
        # Filter lax para excluir grupos ya cubiertos por strict
        strict_ids_set = set()
        for g in strict_groups:
            for i in g["ids"]:
                strict_ids_set.add(i)
        lax_groups_filtered = [
            g for g in lax_groups
            if not any(i in strict_ids_set for i in g["ids"])
        ]
        groups = strict_groups + lax_groups_filtered
        print(f"Grupos strict: {len(strict_groups)} · lax (no overlap): {len(lax_groups_filtered)} · total={len(groups)}")
        if not groups:
            print("Sin duplicados. Salgo.")
            return 0

        totals = {
            "groups": 0, "posts_to_delete": 0,
            "comments_to_migrate": 0, "comments_to_delete": 0,
            "events_to_migrate": 0, "events_to_delete": 0,
        }
        for g in groups:
            ids = g["ids"]
            dirigente = g["dirigente_id"]
            content_preview = (g["content"] or "")[:60].replace("\n", " ")
            print(f"\n── dirigente={dirigente} dups={len(ids)} ids={ids}")
            print(f"   content: {content_preview!r} likes={g['likes']} shares={g['shares']}")
            stats = await merge_group(conn, g, dry_run=dry_run)
            print(f"   canonical={stats['canonical']} dups={stats['dups']}")
            print(f"   comments migrated={stats['comments_migrated']} deleted={stats['comments_deleted']}")
            print(f"   events migrated={stats['events_migrated']} deleted={stats['events_deleted']}")
            print(f"   posts deleted={stats['posts_deleted']}")
            totals["groups"] += 1
            totals["posts_to_delete"] += stats["posts_deleted"]
            totals["comments_to_migrate"] += stats["comments_migrated"]
            totals["comments_to_delete"] += stats["comments_deleted"]
            totals["events_to_migrate"] += stats["events_migrated"]
            totals["events_to_delete"] += stats["events_deleted"]

        print(f"\n=== TOTALES ===")
        for k, v in totals.items():
            print(f"  {k}: {v}")

    finally:
        await conn.close()
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit", action="store_true")
    args = parser.parse_args()
    sys.exit(asyncio.run(main(dry_run=not args.commit)))
