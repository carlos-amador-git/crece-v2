"""ingest_radar_comments_payload.py · 2026-05-26

Ingest de comments en shape RAW-PAYLOAD de RADAR (FB/TT/YT/X) — distinto del
IG aplanado (que usa ingest_radar_ig.py). Reusable por-dirigente.

Item: {entity_id, payload, detected_at, source}
payload (varía por red): text, post_id (parent), comment_id|comment_id_surrogate,
author_username, author_display_name, time_iso|create_time_iso.

Resuelve parent por payload.post_id → social_posts.platform_post_id del profile.
Mapea campos, pseudonimiza author_hash (ensure_author_hash, SQL crudo bypassa ORM).
Salta comments cuyo post padre no esté en CRECE (huérfanos) — los reporta.

CAVEAT por red (verificado Piña 2026-05-26):
  - TT: payload.post_id matchea ppid del post → resuelve limpio.
  - FB: payload.post_id es `pfbid…` pero el post se guarda con feedback-id base64
        → NO matchea. Requiere que RADAR mande un join key consistente. Quedan huérfanos.
  - YT/X: payload.post_id None (volumen despreciable).

Uso:
    python3 backend/scripts/ingest_radar_comments_payload.py --dirigente-id 1 \\
        --profile-id 16 --comments /path/pina-tt-comments.json [--commit]
"""
from __future__ import annotations

import argparse
import os
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

import asyncpg

from app.services.author_hash import ensure_author_hash

DSN = os.environ.get("DATABASE_URL_RAW", "postgresql://crece:crece_dev@localhost:5438/crece")
DATA_SOURCE = "radar-payload-comments-v1"


def bare(ppid) -> str:
    return str(ppid or "").split("_")[0]


def parse_dt(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None


async def main(profile_id: int, comments_f: Path, commit: bool) -> int:
    conn = await asyncpg.connect(DSN)
    rows = await conn.fetch(
        "SELECT id, platform_post_id FROM social_posts WHERE profile_id = $1", profile_id
    )
    post_map = {r["platform_post_id"]: r["id"] for r in rows}

    items = json.load(comments_f.open()).get("comments", [])
    # Contadores separados para visibilidad real (fix 2026-05-28):
    #   n_ingestable: items con post padre + cid resueltos (candidatos a INSERT)
    #   n_inserted:   INSERTs reales emitidos (solo si --commit y cid presente)
    #   n_skipped_no_cid: post padre OK pero cid es falsy → SKIP silencioso pre-fix
    n_ingestable = n_inserted = n_skipped_no_cid = n_orphan = n_nokey = 0
    for it in items:
        # Soporta ambos shapes RADAR: raw-payload (TT) y aplanado (FB con join key).
        pl = it.get("payload", {}) or {}
        post_pid = it.get("platform_post_id") or pl.get("post_id")
        if not post_pid:
            n_nokey += 1
            continue
        # Match exacto primero (FB base64 que NO debe truncarse); bare como fallback.
        parent = post_map.get(str(post_pid)) or post_map.get(bare(post_pid))
        if not parent:
            n_orphan += 1
            continue
        cid = (it.get("comment_id") or it.get("comment_id_surrogate")
               or pl.get("comment_id") or pl.get("comment_id_surrogate"))
        content = it.get("comment_text") or pl.get("text") or ""
        display = it.get("author_display_name") or pl.get("author_display_name")
        author_raw = (it.get("author_hash") or it.get("author_username") or display
                      or pl.get("author_username") or "")
        ah = ensure_author_hash(author_raw, "RADAR")
        if not cid:
            n_skipped_no_cid += 1
            continue
        n_ingestable += 1
        if commit:
            await conn.execute(
                """
                INSERT INTO social_comments
                    (parent_post_id, platform_comment_id, content, author_hash,
                     likes, published_at, is_reply_to_comment, data_source, commenter_handle)
                VALUES ($1,$2,$3,$4,0,$5,false,$6,$7)
                ON CONFLICT (platform_comment_id) DO NOTHING
                """,
                parent, str(cid), content, ah[:64],
                parse_dt(it.get("time_iso") or pl.get("time_iso") or pl.get("create_time_iso")),
                DATA_SOURCE, display,
            )
            n_inserted += 1
    await conn.close()
    print(
        f"[comments] ingestables={n_ingestable} inserted={n_inserted} "
        f"sin_cid={n_skipped_no_cid} huérfanos(post no en CRECE)={n_orphan} "
        f"sin_post_id={n_nokey}"
    )
    print("[APPLY] OK" if commit else "[DRY-RUN] nada escrito.")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dirigente-id", type=int, required=True)
    ap.add_argument("--profile-id", type=int, required=True)
    ap.add_argument("--comments", type=Path, required=True)
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()
    sys.exit(asyncio.run(main(args.profile_id, args.comments, args.commit)))
