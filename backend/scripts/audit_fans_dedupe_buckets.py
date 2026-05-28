"""audit_fans_dedupe_buckets.py · 2026-05-20

Audit READ-ONLY de duplicados watched_profiles. Clasifica cada grupo de
duplicados (mismo LOWER(TRIM(display_name)) + dirigente_observador_id) en
buckets per regla Hugo+Linda 2026-05-20:

- D · grupo contiene cliente_seed → consolidar hacia cliente_seed
- A · grupo contiene [sha256_hash + fb_numerico] → consolidar hacia fb_numerico
- B · grupo contiene varios fb_numerico (mismo id duplicado en BD) → consolidar
- C · grupo contiene varios sha256 distintos SIN ningún fb_numerico → SKIP (homónimo riesgo)
- E · grupo contiene solo 1 row (no duplicado · sanity check)

Output: tabla agregada de cuántos grupos caen en cada bucket + reactions
afectadas. Cero escritura a BD.

Uso:
  python backend/scripts/audit_fans_dedupe_buckets.py --dirigente-id 3
"""
from __future__ import annotations

import argparse
import os
import re
from collections import defaultdict

import psycopg2 as psycopg

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://crece:crece_dev@localhost:5438/crece",
)

# fb_id numérico = solo dígitos (FB user ids son ints largos)
RE_FB_NUMERICO = re.compile(r"^\d+$")
# sha256 = 64 chars hex
RE_SHA256 = re.compile(r"^[a-f0-9]{64}$")


def classify_ext_id(ext_id: str) -> str:
    if not ext_id:
        return "vacio"
    if RE_FB_NUMERICO.fullmatch(ext_id):
        return "fb_numerico"
    if RE_SHA256.fullmatch(ext_id):
        return "sha256"
    return "otro"


def bucket_for_group(rows: list[dict]) -> str:
    """rows = [{source, ext_id_type, ext_id, ...}, ...]"""
    if len(rows) == 1:
        return "E_unico"

    sources = {r["source"] for r in rows}
    ext_id_types = [r["ext_id_type"] for r in rows]
    ext_ids = [r["ext_id"] for r in rows]

    # D · cualquier row es cliente_seed → consolidar hacia ese
    if "cliente_seed" in sources:
        return "D_cliente_seed"

    # Inspeccionar fb_numericos presentes
    has_sha = any(t == "sha256" for t in ext_id_types)
    has_num = any(t == "fb_numerico" for t in ext_id_types)
    unique_nums = {e for e, t in zip(ext_ids, ext_id_types) if t == "fb_numerico"}
    num_count = sum(1 for t in ext_id_types if t == "fb_numerico")

    # Si hay >1 fb_id DISTINTOS → C2 (skip · posibles personas distintas o cuentas diff)
    # Aplica AUNQUE haya sha256 además.
    if len(unique_nums) >= 2:
        return "C2_fbids_distintos"

    # A · mix sha256 + UN solo fb_numerico → consolidar hacia ese fb_numerico
    if has_sha and has_num:
        return "A_sha_to_fbid"

    # B · 2+ rows con el mismo fb_id (raro)
    if num_count >= 2 and len(unique_nums) == 1:
        return "B_fbid_dup"

    # C · solo sha256 (varios distintos) sin fb_numerico → SKIP homónimo riesgo
    sha_count = sum(1 for t in ext_id_types if t == "sha256")
    if sha_count >= 2 and not has_num:
        return "C_sha_distintos"

    return "F_caso_raro"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dirigente-id", type=int, required=True)
    args = parser.parse_args()

    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT wp.id, wp.display_name, wp.profile_external_id, wp.source,
                       (SELECT COUNT(*) FROM watched_like_events wle WHERE wle.watched_profile_id=wp.id) AS reactions
                FROM watched_profiles wp
                WHERE wp.dirigente_observador_id = %s
                  AND wp.display_name IS NOT NULL
                ORDER BY LOWER(TRIM(wp.display_name))
                """,
                (args.dirigente_id,),
            )
            all_rows = cur.fetchall()

    # Agrupar por display_name normalizado
    groups: dict[str, list[dict]] = defaultdict(list)
    for row_id, display_name, ext_id, source, reactions in all_rows:
        key = (display_name or "").lower().strip()
        groups[key].append({
            "id": row_id, "display_name": display_name, "ext_id": ext_id,
            "source": source, "ext_id_type": classify_ext_id(ext_id),
            "reactions": reactions,
        })

    # Solo grupos con >=2 rows (duplicados reales)
    dup_groups = {k: v for k, v in groups.items() if len(v) >= 2}

    # Bucketizar
    bucket_stats: dict[str, dict] = defaultdict(lambda: {"groups": 0, "rows": 0, "reactions": 0})
    samples_per_bucket: dict[str, list[dict]] = defaultdict(list)

    for name, rows in dup_groups.items():
        bucket = bucket_for_group(rows)
        bucket_stats[bucket]["groups"] += 1
        bucket_stats[bucket]["rows"] += len(rows)
        bucket_stats[bucket]["reactions"] += sum(r["reactions"] for r in rows)
        if len(samples_per_bucket[bucket]) < 3:
            samples_per_bucket[bucket].append({
                "display_name": rows[0]["display_name"],
                "n_rows": len(rows),
                "sources": [r["source"] for r in rows],
                "ext_id_types": [r["ext_id_type"] for r in rows],
                "ext_ids": [r["ext_id"] for r in rows],
                "reactions_total": sum(r["reactions"] for r in rows),
            })

    # Reporte
    print(f"\n=== Audit dedupe fans · dirigente_id={args.dirigente_id} ===")
    print(f"Total grupos duplicados: {len(dup_groups)}")
    print(f"Total rows en grupos duplicados: {sum(s['rows'] for s in bucket_stats.values())}")
    print(f"Total reactions afectadas: {sum(s['reactions'] for s in bucket_stats.values())}")
    print()
    print(f"{'Bucket':<25} {'Grupos':>8} {'Rows':>8} {'Reactions':>12} {'Decisión':<40}")
    print(f"{'-'*25} {'-'*8} {'-'*8} {'-'*12} {'-'*40}")

    decisions = {
        "D_cliente_seed": "✅ SAFE · consolidar hacia cliente_seed",
        "A_sha_to_fbid": "✅ SAFE · consolidar hacia fb_numerico",
        "B_fbid_dup": "✅ SAFE · mismo fb_id duplicado · merge directo",
        "C_sha_distintos": "⛔ SKIP · homónimos sin id (regla Hugo R1)",
        "C2_fbids_distintos": "⛔ SKIP · fb_ids distintos = personas distintas",
        "E_unico": "ℹ️  unique row (no debería aparecer en duplicados)",
        "F_caso_raro": "⚠️  inspeccionar manualmente",
    }
    safe_groups = 0
    safe_reactions = 0
    for bucket in ["D_cliente_seed", "A_sha_to_fbid", "B_fbid_dup", "C_sha_distintos", "C2_fbids_distintos", "F_caso_raro"]:
        s = bucket_stats[bucket]
        print(f"{bucket:<25} {s['groups']:>8} {s['rows']:>8} {s['reactions']:>12,} {decisions.get(bucket,''):<40}")
        if bucket.startswith(("A_", "B_", "D_")):
            safe_groups += s["groups"]
            safe_reactions += s["reactions"]

    print()
    print(f"Grupos consolidables (A+B+D · safe): {safe_groups}")
    print(f"Reactions consolidables (safe): {safe_reactions:,}")

    print("\n=== Sample por bucket ===")
    for bucket in ["D_cliente_seed", "A_sha_to_fbid", "B_fbid_dup", "C_sha_distintos", "C2_fbids_distintos", "F_caso_raro"]:
        samples = samples_per_bucket[bucket]
        if not samples:
            continue
        print(f"\n[{bucket}]")
        for s in samples:
            print(f"  · {s['display_name']!r}: {s['n_rows']} rows · sources={s['sources']} · "
                  f"types={s['ext_id_types']} · reactions_total={s['reactions_total']}")


if __name__ == "__main__":
    main()
