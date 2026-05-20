"""consolidate_fans_duplicates.py · 2026-05-20 · CEO LV

Consolida watched_profiles duplicados per regla Hugo+Linda 2026-05-20:

- Bucket D · grupo contiene cliente_seed → consolidar hacia cliente_seed
  (preserva tags + notes manuales del cliente)
- Bucket A · grupo `[sha256+, fb_numerico_único]` → consolidar hacia fb_numerico
- Bucket B · varios rows mismo fb_id → merge directo
- Bucket C · sha256 distintos sin fb_id → SKIP (homónimos riesgo per Hugo R1)
- Bucket C2 · fb_ids distintos → SKIP (cuentas distintas, posiblemente personas distintas)

Cero pérdida de datos:
- UPDATE watched_like_events.watched_profile_id de viejo a nuevo (preserva reactions)
- DELETE rows vacíos solo después de migrar TODOS sus eventos
- TRANSACTION atómico per grupo · rollback si cualquier paso falla

Modos:
  --dry-run  → log JSON de qué movería, NO tocar BD
  (default)  → ejecuta REAL con transaction

Uso:
  python backend/scripts/consolidate_fans_duplicates.py --dirigente-id 3 --dry-run
  python backend/scripts/consolidate_fans_duplicates.py --dirigente-id 3
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import psycopg2 as psycopg

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://crece:crece_dev@localhost:5438/crece",
)

RE_FB_NUMERICO = re.compile(r"^\d+$")
RE_SHA256 = re.compile(r"^[a-f0-9]{64}$")


def classify_ext_id(ext_id: str | None) -> str:
    if not ext_id:
        return "vacio"
    if RE_FB_NUMERICO.fullmatch(ext_id):
        return "fb_numerico"
    if RE_SHA256.fullmatch(ext_id):
        return "sha256"
    return "otro"


def pick_target(rows: list[dict]) -> tuple[int, str] | None:
    """Devuelve (target_id, bucket) o None si grupo NO consolidable.

    Prioridad: cliente_seed > fb_numerico único > skip.
    """
    # D · cliente_seed
    seed_rows = [r for r in rows if r["source"] == "cliente_seed"]
    if seed_rows:
        # Si hay >1 cliente_seed (raro), tomamos el primero estable por id
        return (sorted(seed_rows, key=lambda r: r["id"])[0]["id"], "D_cliente_seed")

    # B/A · UN fb_numerico único
    num_rows = [r for r in rows if classify_ext_id(r["ext_id"]) == "fb_numerico"]
    unique_nums = {r["ext_id"] for r in num_rows}
    if len(unique_nums) >= 2:
        return None  # C2 fb_ids distintos · skip
    if num_rows and len(unique_nums) == 1:
        # Si hay 2+ rows con el mismo fb_id → B. Tomamos el más antiguo (id mínimo).
        target = sorted(num_rows, key=lambda r: r["id"])[0]
        if len(num_rows) >= 2 and not any(classify_ext_id(r["ext_id"]) == "sha256" for r in rows):
            return (target["id"], "B_fbid_dup")
        return (target["id"], "A_sha_to_fbid")

    # No hay fb_numerico → bucket C (sha256 distintos) · skip
    return None


def fetch_groups(conn, dirigente_id: int) -> dict[str, list[dict]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT wp.id, wp.display_name, wp.profile_external_id, wp.source,
                   wp.platform, wp.author_hash,
                   (SELECT COUNT(*) FROM watched_like_events wle WHERE wle.watched_profile_id=wp.id) AS reactions
            FROM watched_profiles wp
            WHERE wp.dirigente_observador_id = %s
              AND wp.display_name IS NOT NULL
            ORDER BY LOWER(TRIM(wp.display_name)), wp.id
            """,
            (dirigente_id,),
        )
        all_rows = cur.fetchall()

    groups: dict[str, list[dict]] = defaultdict(list)
    for row_id, display_name, ext_id, source, platform, author_hash, reactions in all_rows:
        key = (display_name or "").lower().strip()
        groups[key].append({
            "id": row_id,
            "display_name": display_name,
            "ext_id": ext_id,
            "source": source,
            "platform": platform,
            "author_hash": author_hash,
            "reactions": reactions,
        })

    return {k: v for k, v in groups.items() if len(v) >= 2}


def consolidate_group(conn, target_id: int, source_ids: list[int],
                       group_name: str, bucket: str, dry_run: bool) -> dict:
    """Migra eventos de source_ids→target_id, después DELETE rows vacíos.

    Retorna stats del grupo.
    """
    stats = {
        "display_name": group_name,
        "bucket": bucket,
        "target_id": target_id,
        "source_ids": source_ids,
        "events_migrated": 0,
        "rows_deleted": 0,
        "error": None,
    }

    if dry_run:
        # Solo contamos eventos que se migrarían
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) FROM watched_like_events
                WHERE watched_profile_id = ANY(%s)
                """,
                (source_ids,),
            )
            stats["events_migrated"] = cur.fetchone()[0]
            stats["rows_deleted"] = len(source_ids)
        return stats

    try:
        with conn.cursor() as cur:
            # Estrategia atómica:
            # 1. Identificar 1 wle source por (post_id, reaction_type) que NO existe en target
            # 2. UPDATE solo esos (cero colisión unique constraint)
            # 3. DELETE el resto de wle en sources (duplicados que ya están cubiertos)
            # 4. DELETE rows watched_profiles source
            cur.execute(
                """
                WITH existentes_target AS (
                  SELECT post_id, reaction_type
                  FROM watched_like_events
                  WHERE watched_profile_id = %s
                ),
                ranked_source_events AS (
                  SELECT wle.id, wle.post_id, wle.reaction_type,
                         ROW_NUMBER() OVER (
                           PARTITION BY wle.post_id, wle.reaction_type
                           ORDER BY wle.id
                         ) AS rn
                  FROM watched_like_events wle
                  WHERE wle.watched_profile_id = ANY(%s)
                ),
                migrables AS (
                  SELECT r.id FROM ranked_source_events r
                  WHERE r.rn = 1
                    AND NOT EXISTS (
                      SELECT 1 FROM existentes_target e
                      WHERE e.post_id = r.post_id AND e.reaction_type = r.reaction_type
                    )
                )
                UPDATE watched_like_events
                SET watched_profile_id = %s
                WHERE id IN (SELECT id FROM migrables)
                """,
                (target_id, source_ids, target_id),
            )
            stats["events_migrated"] = cur.rowcount

            # DELETE wle remanentes en sources (duplicados ya cubiertos en target)
            cur.execute(
                """
                DELETE FROM watched_like_events
                WHERE watched_profile_id = ANY(%s)
                """,
                (source_ids,),
            )

            # DELETE rows vacíos de watched_profiles
            cur.execute(
                "DELETE FROM watched_profiles WHERE id = ANY(%s)",
                (source_ids,),
            )
            stats["rows_deleted"] = cur.rowcount
    except Exception as e:
        stats["error"] = str(e)
        conn.rollback()
        raise

    return stats


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dirigente-id", type=int, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output", default=None,
                        help="Default: backend/.context/CONSOLIDATE-fans-d{id}-{fecha}.json")
    args = parser.parse_args()

    output = Path(args.output) if args.output else Path(
        f"backend/.context/CONSOLIDATE-fans-d{args.dirigente_id}-"
        f"{datetime.now().strftime('%Y%m%d_%H%M')}{'-dryrun' if args.dry_run else ''}.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)

    print(f"=== Consolidación fans · dirigente={args.dirigente_id} · "
          f"dry_run={args.dry_run} ===")

    with psycopg.connect(DB_URL) as conn:
        groups = fetch_groups(conn, args.dirigente_id)
        print(f"Grupos duplicados: {len(groups)}")

        # Conteo pre-fix (para verificar después)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) FROM watched_like_events wle
                JOIN social_posts sp ON wle.post_id=sp.id
                JOIN social_profiles sprof ON sp.profile_id=sprof.id
                WHERE sprof.dirigente_id=%s
                """,
                (args.dirigente_id,),
            )
            reactions_pre = cur.fetchone()[0]
            print(f"Reactions BD pre-fix: {reactions_pre:,}")

        results = []
        skipped = []
        bucket_counts = defaultdict(int)
        total_events_migrated = 0
        total_rows_deleted = 0

        for name, rows in sorted(groups.items()):
            decision = pick_target(rows)
            if decision is None:
                skipped.append({
                    "display_name": name,
                    "n_rows": len(rows),
                    "ext_id_types": [classify_ext_id(r["ext_id"]) for r in rows],
                    "sources": [r["source"] for r in rows],
                    "reactions_total": sum(r["reactions"] for r in rows),
                    "reason": "homónimo / fb_ids distintos",
                })
                bucket_counts["SKIP"] += 1
                continue

            target_id, bucket = decision
            source_ids = [r["id"] for r in rows if r["id"] != target_id]

            stats = consolidate_group(
                conn, target_id, source_ids, name, bucket, args.dry_run
            )
            results.append(stats)
            bucket_counts[bucket] += 1
            total_events_migrated += stats["events_migrated"]
            total_rows_deleted += stats["rows_deleted"]

        if not args.dry_run:
            conn.commit()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COUNT(*) FROM watched_like_events wle
                    JOIN social_posts sp ON wle.post_id=sp.id
                    JOIN social_profiles sprof ON sp.profile_id=sprof.id
                    WHERE sprof.dirigente_id=%s
                    """,
                    (args.dirigente_id,),
                )
                reactions_post = cur.fetchone()[0]
        else:
            reactions_post = reactions_pre  # dry-run no toca

    summary = {
        "dirigente_id": args.dirigente_id,
        "dry_run": args.dry_run,
        "groups_total": len(groups),
        "groups_consolidated": len(results),
        "groups_skipped": len(skipped),
        "buckets": dict(bucket_counts),
        "total_events_migrated": total_events_migrated,
        "total_rows_deleted": total_rows_deleted,
        "reactions_pre": reactions_pre,
        "reactions_post": reactions_post,
        "reactions_delta": reactions_pre - reactions_post,
        "results": results[:50],  # primeros 50 detalles
        "skipped_samples": skipped[:20],
    }

    output.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"\nGrupos consolidados: {len(results)}")
    print(f"Grupos skipped (homónimos): {len(skipped)}")
    print(f"Buckets: {dict(bucket_counts)}")
    print(f"Eventos migrados: {total_events_migrated:,}")
    print(f"Rows eliminados: {total_rows_deleted}")
    print(f"Reactions pre→post: {reactions_pre:,} → {reactions_post:,} (delta {reactions_pre-reactions_post})")
    print(f"\nReporte JSON: {output}")
    if args.dry_run:
        print("\n⚠️  DRY-RUN · ningún cambio aplicado a BD. Re-corre sin --dry-run para aplicar.")


if __name__ == "__main__":
    main()
