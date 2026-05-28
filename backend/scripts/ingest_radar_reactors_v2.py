"""ingest_radar_reactors_v2.py · 2026-05-21

Ingest sencillo del export JSON Hugo · re-scrape 7 días huecos Saymi FB.
Formato JSON: {export_meta, reactors[]} (shape v2 acordado entre Linda y Hugo).

Idempotente:
- watched_profiles UPSERT por (dirigente_observador_id, platform, author_hash)
- watched_like_events INSERT ON CONFLICT (watched_profile_id, post_id, reaction_type) DO NOTHING

Mapping reactor → post: lookup social_posts.platform_post_id (Saymi FB).
Si no se encuentra el post → skip + log.

Uso:
    docker exec crece-backend python scripts/ingest_radar_reactors_v2.py --dry-run
    docker exec crece-backend python scripts/ingest_radar_reactors_v2.py --commit
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
from typing import Any

import asyncpg

DEFAULT_JSON = "/host/radar-reactors-saymi-fb-7days-2026-05-21.json"
DIRIGENTE_ID = int(os.environ.get("DIRIGENTE_ID", "3"))  # default Saymi, override via env
PLATFORM = os.environ.get("PLATFORM", "FACEBOOK")  # FB default · IG vía env


async def main(json_path: Path, commit: bool) -> int:
    with json_path.open() as f:
        data = json.load(f)

    meta = data["export_meta"]
    # Hugo v3 IG export usa "likers" en lugar de "reactors" · acepto ambos.
    reactors = data.get("reactors") or data.get("likers") or []
    print(f"[meta] {meta.get('n_reactors')} reactors · {meta.get('unique_posts')} posts · {meta.get('unique_authors')} authors")
    print(f"[meta] generated_at={meta.get('generated_at_utc')} engine={meta.get('filter')}")

    dsn = os.environ.get(
        "DATABASE_URL_RAW",
        "postgresql://crece:crece_dev@crece-db:5432/crece",
    )
    conn = await asyncpg.connect(dsn)

    # 1) Mapear platform_post_id → post_id usando social_posts.
    # Hugo v3 export (2026-05-21): si existe platform_post_id_base64, usarlo
    # como primary (matchea con CRECE que insertó posts en base64). Fallback
    # a platform_post_id_numeric o platform_post_id legacy. Fallback final a
    # post_url match.
    def _pp_key(r: dict) -> str:
        return r.get("platform_post_id_base64") or r.get("platform_post_id") or r.get("platform_post_id_numeric") or ""

    pp_ids = sorted({_pp_key(r) for r in reactors if _pp_key(r)})
    rows = await conn.fetch(
        """
        SELECT sp.platform_post_id, sp.id AS post_id, sps.dirigente_id
        FROM social_posts sp
        JOIN social_profiles sps ON sps.id = sp.profile_id
        WHERE sps.dirigente_id = $1 AND sps.platform = $2
          AND sp.platform_post_id = ANY($3::text[])
        """,
        DIRIGENTE_ID,
        PLATFORM,
        pp_ids,
    )
    pp_to_post = {r["platform_post_id"]: r["post_id"] for r in rows}
    print(f"[map] {len(pp_to_post)}/{len(pp_ids)} platform_post_ids (base64) resueltos a posts CRECE")

    # Numeric-match (FB): CRECE guarda platform_post_id en base64 que decodifica a
    # "S:_I<page>:<numeric>:<numeric>". Extraemos el numeric para matchear reactors
    # cuyo base64 no resolvió (Balles/Piña: post_url sin pfbid → solo traen numeric).
    import base64 as _b64
    numeric_to_post: dict[str, int] = {}
    all_posts = await conn.fetch(
        """SELECT sp.platform_post_id, sp.id AS post_id FROM social_posts sp
           JOIN social_profiles sps ON sps.id = sp.profile_id
           WHERE sps.dirigente_id = $1 AND sps.platform = $2""",
        DIRIGENTE_ID, PLATFORM,
    )
    for row in all_posts:
        try:
            decoded = _b64.b64decode(row["platform_post_id"]).decode("utf-8", "ignore")
            num = decoded.split(":")[-1].strip()  # último segmento = post numeric
            if num.isdigit():
                numeric_to_post[num] = row["post_id"]
        except Exception:
            continue
    print(f"[map numeric] {len(numeric_to_post)} posts indexados por numeric (decode base64 CRECE)")

    # Fallback: para reactors con post_url pero pp_id no encontrado, buscar via URL substring.
    urls_to_try = sorted({r.get("post_url", "") for r in reactors if r.get("post_url") and _pp_key(r) not in pp_to_post})
    url_to_post: dict[str, int] = {}
    if urls_to_try:
        # Extrae pfbid del URL para hacer LIKE match en raw_data->>'url'
        for u in urls_to_try[:500]:  # cap defensa N+1
            row = await conn.fetchrow(
                """
                SELECT sp.id FROM social_posts sp
                JOIN social_profiles sps ON sps.id = sp.profile_id
                WHERE sps.dirigente_id = $1 AND sps.platform = $2
                  AND (sp.raw_data->>'url' = $3 OR sp.raw_data->>'url' LIKE $4)
                LIMIT 1
                """,
                DIRIGENTE_ID, PLATFORM, u, f"%{u[-30:]}%" if len(u) > 30 else u,
            )
            if row:
                url_to_post[u] = row["id"]
        print(f"[fallback url] {len(url_to_post)} reactors adicionales resueltos via post_url")
    missing = set(pp_ids) - set(pp_to_post.keys())
    if missing:
        print(f"[warn] {len(missing)} platform_post_ids no encontrados en CRECE social_posts")
        for m in list(missing)[:5]:
            print(f"  · missing pp_id: {m}")

    # 2) Resolver org_id de Saymi (para watched_profiles.org_id)
    org_row = await conn.fetchrow(
        "SELECT org_id FROM dirigentes WHERE id = $1", DIRIGENTE_ID
    )
    org_id = org_row["org_id"] if org_row else None
    print(f"[map] dirigente_id={DIRIGENTE_ID} org_id={org_id}")

    # 3) UPSERT watched_profiles por author_hash (extracción set)
    unique_authors = {r["author_hash"]: r["author_display_name"] for r in reactors}
    print(f"[wp] processing {len(unique_authors)} unique authors")

    counters: Counter[str] = Counter()

    if commit:
        # Crear/actualizar watched_profiles
        for author_hash, display_name in unique_authors.items():
            await conn.execute(
                """
                INSERT INTO watched_profiles (
                    dirigente_observador_id, org_id, platform, profile_external_id,
                    display_name, source, tags, is_active, author_hash, created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, '[]'::jsonb, true, $7, NOW(), NOW())
                ON CONFLICT (dirigente_observador_id, platform, profile_external_id)
                DO UPDATE SET
                    display_name = COALESCE(EXCLUDED.display_name, watched_profiles.display_name),
                    author_hash = EXCLUDED.author_hash,
                    updated_at = NOW()
                """,
                DIRIGENTE_ID,
                org_id,
                PLATFORM,
                author_hash,
                display_name,
                "auto_suggested",
                author_hash,
            )
            counters["wp_upserts"] += 1

        # Cachear author_hash → watched_profile_id
        wp_rows = await conn.fetch(
            """
            SELECT id, author_hash FROM watched_profiles
            WHERE dirigente_observador_id = $1 AND platform = $2
              AND author_hash = ANY($3::text[])
            """,
            DIRIGENTE_ID,
            PLATFORM,
            list(unique_authors.keys()),
        )
        ah_to_wp = {r["author_hash"]: r["id"] for r in wp_rows}

        # 4) INSERT watched_like_events ON CONFLICT DO NOTHING
        events_batch: list[tuple[int, int, str, datetime, str]] = []
        for r in reactors:
            pp = _pp_key(r)
            post_id = pp_to_post.get(pp)
            if not post_id:
                url = r.get("post_url")
                if url:
                    post_id = url_to_post.get(url)
            if not post_id:
                num = str(r.get("platform_post_id_numeric") or "")
                if num:
                    post_id = numeric_to_post.get(num)
            if not post_id:
                counters["events_skipped_no_post"] += 1
                continue
            ah = r["author_hash"]
            wp_id = ah_to_wp.get(ah)
            if not wp_id:
                counters["events_skipped_no_wp"] += 1
                continue
            detected_at_str = r["detected_at"]
            try:
                detected_at = datetime.fromisoformat(detected_at_str.replace("Z", "+00:00"))
            except Exception:
                counters["events_skipped_bad_date"] += 1
                continue
            # source debe ser uno de los permitidos por ck_watched_like_source:
            # apify_reactions | visual_evidence | oauth_api | other_scraper
            # RADAR CDP usa "other_scraper" como bucket compatible.
            # Normalizar reaction_type: CRECE constraint solo acepta
            # like/love/wow/haha/sad/angry/support/care. "unknown" del engine
            # RADAR (6-7% de reactors cuando el DOM no permite categorizar)
            # se mapea a 'like' como default conservador (es el ~64% del total
            # por estructura · estimación razonable).
            reaction = r["reaction_type"]
            if reaction not in ("like", "love", "wow", "haha", "sad", "angry", "support", "care"):
                reaction = "like"
            events_batch.append(
                (wp_id, post_id, reaction, detected_at, "other_scraper")
            )

        # Batch insert
        for i in range(0, len(events_batch), 1000):
            chunk = events_batch[i : i + 1000]
            await conn.executemany(
                """
                INSERT INTO watched_like_events
                  (watched_profile_id, post_id, reaction_type, detected_at, source)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (watched_profile_id, post_id, reaction_type) DO NOTHING
                """,
                chunk,
            )
            counters["events_attempted"] += len(chunk)
            print(f"  inserted batch {i + len(chunk)}/{len(events_batch)}")

        # Count actual rows inserted (post-conflict)
        post_count = await conn.fetchval(
            """
            SELECT COUNT(*) FROM watched_like_events wle
            JOIN social_posts sp ON sp.id = wle.post_id
            JOIN social_profiles sps ON sps.id = sp.profile_id
            WHERE sps.dirigente_id = $1 AND sps.platform = $2
              AND sp.id = ANY($3::int[])
            """,
            DIRIGENTE_ID,
            PLATFORM,
            list(pp_to_post.values()),
        )
        counters["events_in_db_target_posts"] = post_count
    else:
        # dry-run · solo conteo (misma resolución que el commit: base64 → url → numeric)
        for r in reactors:
            pp = _pp_key(r)
            post_id = pp_to_post.get(pp)
            if not post_id and r.get("post_url"):
                post_id = url_to_post.get(r["post_url"])
            if not post_id:
                num = str(r.get("platform_post_id_numeric") or "")
                if num:
                    post_id = numeric_to_post.get(num)
            if post_id:
                counters["events_resolvable"] += 1
            else:
                counters["events_skipped_no_post"] += 1

    await conn.close()

    print("\n===== RESULT =====")
    for k, v in counters.items():
        print(f"  {k}: {v}")
    if not commit:
        print("\n[dry-run] Pasa --commit para escribir.")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--json", type=Path, default=Path(DEFAULT_JSON))
    p.add_argument("--commit", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    sys.exit(asyncio.run(main(args.json, args.commit)))
