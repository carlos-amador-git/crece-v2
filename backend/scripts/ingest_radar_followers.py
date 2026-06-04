"""ingest_radar_followers.py · 2026-06-03

Ingest de followers desde el export RADAR (followers.json) — cierra el gap
documentado (gaby_delta: "FB/TT followers_count=0 → ER no computa, req B07").
Los adapters de posts/reactors LEEN followers_count pero NO lo escriben; el
scraper in-app SALTA perfiles manual_host_ingest (workers/tasks.py:367). Sin
este paso, followers_count queda stale tras un host-ingest.

Hace exactamente lo que el patrón canónico de workers/tasks.py:386:
  1. UPDATE social_profiles.followers_count + last_manual_update + data_source
  2. INSERT social_profile_snapshots (profile_id, dirigente_id, org_id, platform,
     followers_count, posts_count, taken_at) — para el timeseries B07.

followers.json shape: {"FACEBOOK": N, "TIKTOK": N, "X": N, "YOUTUBE": N, "INSTAGRAM": N}
La clave "X" del export mapea a la plataforma CRECE "TWITTER".

Idempotente en followers_count (UPDATE al valor del export). El snapshot es
append-only por diseño (1 fila por corrida = punto en el timeseries).

Uso:
    PYTHONPATH=. .venv/bin/python3 scripts/ingest_radar_followers.py \\
        --dirigente-id 3 --followers /path/saymi/followers.json [--commit]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

import asyncpg

DSN = "postgresql://crece:crece_dev@localhost:5438/crece"
DATA_SOURCE = "manual_host_ingest"

# Clave del export → valor del enum platform_enum en CRECE.
PLATFORM_MAP = {
    "FACEBOOK": "FACEBOOK",
    "INSTAGRAM": "INSTAGRAM",
    "TIKTOK": "TIKTOK",
    "YOUTUBE": "YOUTUBE",
    "X": "TWITTER",
    "TWITTER": "TWITTER",
}


async def main(dirigente_id: int, followers_f: Path, commit: bool) -> int:
    data = json.load(followers_f.open())
    conn = await asyncpg.connect(DSN)
    org_row = await conn.fetchrow(
        "SELECT org_id FROM dirigentes WHERE id = $1", dirigente_id
    )
    if org_row is None:
        print(f"dirigente_id {dirigente_id} no existe", file=sys.stderr)
        await conn.close()
        return 1
    org_id = org_row["org_id"]

    updated = skipped = 0
    for raw_platform, count in data.items():
        platform = PLATFORM_MAP.get(raw_platform.upper())
        if not platform:
            print(f"  [skip] plataforma desconocida en followers.json: {raw_platform}")
            skipped += 1
            continue
        prof = await conn.fetchrow(
            "SELECT id, followers_count, posts_count FROM social_profiles "
            "WHERE dirigente_id = $1 AND platform = $2::platform_enum",
            dirigente_id, platform,
        )
        if prof is None:
            print(f"  [skip] sin perfil {platform} para dirigente {dirigente_id}")
            skipped += 1
            continue
        old = prof["followers_count"] or 0
        diff = count - old
        print(f"  {platform:<10} {old:>8} → {count:<8} (diff {diff:+})")
        if commit:
            await conn.execute(
                "UPDATE social_profiles SET followers_count = $1, "
                "last_manual_update = NOW(), data_source = $2::data_source_enum "
                "WHERE id = $3",
                count, DATA_SOURCE, prof["id"],
            )
            await conn.execute(
                "INSERT INTO social_profile_snapshots "
                "(profile_id, dirigente_id, org_id, platform, followers_count, posts_count, taken_at) "
                "VALUES ($1, $2, $3, $4::platform_enum, $5, $6, NOW())",
                prof["id"], dirigente_id, org_id, platform, count, prof["posts_count"] or 0,
            )
        updated += 1

    await conn.close()
    print(f"\n[{'APPLY' if commit else 'DRY-RUN'}] perfiles={updated} saltados={skipped}")
    if not commit:
        print("(--commit para escribir)")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dirigente-id", type=int, required=True)
    ap.add_argument("--followers", type=Path, required=True)
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()
    sys.exit(asyncio.run(main(args.dirigente_id, args.followers, args.commit)))
