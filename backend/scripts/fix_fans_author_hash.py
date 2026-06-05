"""fix_fans_author_hash.py · 2026-06-05

Repara D-AUTHOR-HASH-PII: el backfill de reactors guardó author_hash NUMÉRICO crudo
en watched_profiles (bypaseó ensure_author_hash). Re-deriva el hash canónico por
NOMBRE (display_name) con la función real (mismo salt env que comments) para
restaurar el join watched_profiles↔social_comments y deduplicar.

USA LA FUNCIÓN REAL ensure_author_hash → salt consistente con los comments en BD.

Dry-run por default: NO escribe, solo mide cuántos fans quedarían unidos a comments.
--commit: aplica UPDATE + consolidación (mover watched_like_events + borrar remanentes).

Política: identidad por nombre, colisión de homónimos ACEPTADA (D-AUTHOR-HASH-PII).
"""
from __future__ import annotations
import argparse, asyncio, os, re
import asyncpg
from app.services.author_hash import ensure_author_hash

# Un author_hash CANÓNICO = sha256 exacto de 64 hex. OJO: is_hashed() del service
# usa ^[0-9a-f]{8,}$ que da TRUE para IDs numéricos (puros dígitos = hex válido) —
# por eso NO sirve aquí para detectar los numéricos crudos del backfill. Usamos 64-char.
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

DSN = os.environ.get("DATABASE_URL_RAW", "postgresql://crece:crece_dev@localhost:5438/crece")
DIRS = [1, 3, 5, 8, 60]
# String de plataforma que usaron los adapters de comments (para que el join matchee):
# comments_payload.py usa "RADAR" (FB/X/TT/YT) · ingest_radar_ig.py usa "INSTAGRAM"
PLAT_STR = {"FACEBOOK": "RADAR", "INSTAGRAM": "INSTAGRAM",
            "TWITTER": "RADAR", "TIKTOK": "RADAR", "YOUTUBE": "RADAR"}


async def main(commit: bool) -> int:
    conn = await asyncpg.connect(DSN)
    # 1) fans con author_hash NO-canónico (numérico crudo) + display_name
    rows = await conn.fetch(
        """SELECT id, dirigente_observador_id did, platform, display_name, author_hash
           FROM watched_profiles
           WHERE dirigente_observador_id = ANY($1::int[]) AND display_name IS NOT NULL""",
        DIRS,
    )
    to_fix = []  # (id, new_hash)
    new_hash_by_id = {}
    for r in rows:
        ah = r["author_hash"]
        if ah and SHA256_RE.match(ah):
            new_hash_by_id[r["id"]] = ah  # ya canónico (sha256 64-char), lo dejamos
            continue
        plat = PLAT_STR.get(r["platform"], r["platform"])
        nh = ensure_author_hash(r["display_name"], plat)
        new_hash_by_id[r["id"]] = nh
        to_fix.append((r["id"], nh))
    print(f"[scan] fans totales={len(rows)} · a re-hashear (no-canónicos)={len(to_fix)}")

    # 2) DRY measure: ¿cuántos fans quedarían unidos a un comment? (set de comment hashes)
    chs = await conn.fetch(
        """SELECT DISTINCT sc.author_hash FROM social_comments sc
           JOIN social_posts p ON p.id=sc.parent_post_id
           JOIN social_profiles sp ON sp.id=p.profile_id
           WHERE sp.dirigente_id = ANY($1::int[])""", DIRS)
    comment_hashes = {c["author_hash"] for c in chs}
    nuevos_unidos = sum(1 for _id, nh in new_hash_by_id.items() if nh in comment_hashes)
    print(f"[dry] comment hashes distinct={len(comment_hashes)}")
    print(f"[dry] fans que quedarían UNIDOS a comments tras el fix: {nuevos_unidos}")
    # antes (estado actual)
    antes = await conn.fetchval(
        """SELECT count(*) FROM watched_profiles wp
           WHERE wp.dirigente_observador_id = ANY($1::int[])
             AND wp.author_hash IN (SELECT DISTINCT sc.author_hash FROM social_comments sc
               JOIN social_posts p ON p.id=sc.parent_post_id JOIN social_profiles sp ON sp.id=p.profile_id
               WHERE sp.dirigente_id = ANY($1::int[]))""", DIRS)
    print(f"[dry] fans unidos a comments AHORA (antes del fix): {antes}")

    if not commit:
        print("\n=== DRY-RUN · nada escrito. Re-correr con --commit para aplicar. ===")
        await conn.close(); return 0

    # 3) COMMIT: re-hash + consolidar dentro de UNA transacción
    async with conn.transaction():
        await conn.executemany(
            "UPDATE watched_profiles SET author_hash=$1, updated_at=NOW() WHERE id=$2",
            [(nh, _id) for _id, nh in to_fix])
        # consolidar SET-BASED: mapping loser→keep (min id por dirigente,platform,author_hash)
        await conn.execute("""
            CREATE TEMP TABLE merge_map ON COMMIT DROP AS
            SELECT wp.id AS loser, m.keep
            FROM watched_profiles wp
            JOIN (SELECT dirigente_observador_id did, platform, author_hash, min(id) keep
                  FROM watched_profiles WHERE dirigente_observador_id = ANY($1::int[])
                  GROUP BY 1,2,3) m
              ON wp.dirigente_observador_id=m.did AND wp.platform=m.platform AND wp.author_hash=m.author_hash
            WHERE wp.dirigente_observador_id = ANY($1::int[]) AND wp.id <> m.keep
        """, DIRS)
        n_losers = await conn.fetchval("SELECT count(*) FROM merge_map")
        # mover eventos deduplicados de losers → keep (skip los que keep ya tiene)
        ins = await conn.execute("""
            INSERT INTO watched_like_events (watched_profile_id, post_id, reaction_type, detected_at, source)
            SELECT mm.keep, e.post_id, e.reaction_type, min(e.detected_at), min(e.source)
            FROM watched_like_events e JOIN merge_map mm ON e.watched_profile_id=mm.loser
            GROUP BY mm.keep, e.post_id, e.reaction_type
            ON CONFLICT (watched_profile_id, post_id, reaction_type) DO NOTHING
        """)
        await conn.execute("DELETE FROM watched_like_events WHERE watched_profile_id IN (SELECT loser FROM merge_map)")
        await conn.execute("DELETE FROM watched_profiles WHERE id IN (SELECT loser FROM merge_map)")
        print(f"[commit] re-hashed={len(to_fix)} · fans consolidados(borrados)={n_losers} · eventos reubicados={ins.split()[-1]}")
    await conn.close()
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true")
    raise SystemExit(asyncio.run(main(ap.parse_args().commit)))
