#!/usr/bin/env python3
"""IG likers vía instagrapi · sustituye Apify para IG · $0.

Pre-requisito: cuenta IG configurada en env
- INSTAGRAM_USERNAME=soporte@consultoriamd.com.mx
- INSTAGRAM_PASSWORD=<secret>

Output: inserts en `watched_like_events` con source='instagrapi_auth'
        (nueva source distinta de 'apify_reactions' para auditoría).

Usage:
    python3 backend/scripts/ig_likers_instagrapi.py --dirigente 3 --max-posts 5
"""
from __future__ import annotations

import argparse
import hashlib
import logging
import os
import sys
import time
import unicodedata
from datetime import UTC, datetime
from pathlib import Path

import psycopg2
import psycopg2.extras

PROJECT_ROOT = Path("/Users/marxchavez/Projects/crece-v2")
for env_file in [PROJECT_ROOT / ".env", PROJECT_ROOT / "backend/.env.scraping-keys"]:
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.split("#")[0].strip())

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("ig_likers")

SALT = os.environ.get("COMMENT_AUTHOR_SALT", "crece-v2-lfpdppp-salt-2026")
DB_DSN = os.environ.get(
    "DB_DSN_LIKES",
    "host=crece-db port=5432 dbname=crece user=crece password=crece_dev",
)


def H_ig(pk: str) -> str:
    """Hash compatible con social_comments.author_hash para plataforma INSTAGRAM."""
    return hashlib.sha256(f"INSTAGRAM:{pk}:{SALT}".encode()).hexdigest()


def norm(s: str) -> str:
    if not s: return ""
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()


def load_watchlist_ig(cur, dirigente_id: int):
    """Retorna watchlists con platform=INSTAGRAM filtrados."""
    cur.execute(
        """SELECT id, display_name, profile_external_id, author_hash, profile_handle
           FROM watched_profiles
           WHERE dirigente_observador_id=%s AND is_active=TRUE
             AND platform='INSTAGRAM'""",
        (dirigente_id,),
    )
    rows = cur.fetchall()
    by_hash = {r["author_hash"]: dict(r) for r in rows}
    by_name = {norm(r["display_name"]): dict(r) for r in rows if r["display_name"]}
    by_handle = {(r["profile_handle"] or "").lstrip("@").lower(): dict(r) for r in rows if r["profile_handle"]}
    return by_hash, by_name, by_handle


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dirigente", type=int, default=3, help="dirigente_id (default 3 = Saymi)")
    ap.add_argument("--max-posts", type=int, default=5)
    ap.add_argument("--max-likers-per-post", type=int, default=100, help="instagrapi default 100")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    import instagrapi

    conn = psycopg2.connect(DB_DSN); conn.autocommit = False
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SET app.current_org_id='2'")

    by_hash, by_name, by_handle = load_watchlist_ig(cur, args.dirigente)
    log.info("Watchlist IG: %d perfiles (hash=%d names=%d handles=%d)",
             len(by_hash), len(by_hash), len(by_name), len(by_handle))
    if not by_hash and not by_name:
        log.warning("Watchlist IG vacía para dirigente=%d. No hay nada que matchear · solo capturará reactors sin match.",
                    args.dirigente)

    cur.execute(
        """SELECT sp.id, sp.platform_post_id, sp.published_at, sp.likes,
                  sp.raw_data->>'url' AS url
           FROM social_posts sp
           JOIN social_profiles spr ON sp.profile_id=spr.id
           WHERE spr.dirigente_id=%s AND spr.platform='INSTAGRAM'
             AND sp.likes > 0
           ORDER BY sp.published_at DESC NULLS LAST, sp.likes DESC
           LIMIT %s""",
        (args.dirigente, args.max_posts),
    )
    posts = cur.fetchall()
    log.info("Target posts IG: %d", len(posts))

    # Login
    c = instagrapi.Client()
    user = os.environ["INSTAGRAM_USERNAME"]
    pwd = os.environ["INSTAGRAM_PASSWORD"]
    log.info("Login IG con %s***...", user[:5])
    try:
        c.login(user, pwd)
    except Exception as e:
        log.error("Login fallo: %s", e)
        sys.exit(1)
    log.info("✓ Login OK")

    total_likers_capturados = 0
    total_matches = 0
    inserted = 0

    for p in posts:
        post_pk_db = p["id"]
        media_id = p["platform_post_id"]
        log.info("Post id=%d media_id=%s likes_reportados=%s", post_pk_db, media_id, p["likes"])
        try:
            # media_id puede ser shortcode o media_pk; instagrapi resuelve ambos
            if str(media_id).isdigit():
                media_pk = int(media_id)
            else:
                media_pk = c.media_pk_from_code(media_id)
        except Exception as e:
            log.warning("  resolución media_pk falló: %s", e)
            continue

        try:
            likers = c.media_likers(media_pk)
        except Exception as e:
            log.warning("  media_likers falló: %s", e)
            continue

        log.info("  likers retornados: %d", len(likers))
        total_likers_capturados += len(likers)

        for liker in likers:
            pk_str = str(liker.pk)
            uname = (liker.username or "").lower()
            fullname = liker.full_name or ""
            ah = H_ig(pk_str)
            match = None; method = None
            if ah in by_hash:
                match = by_hash[ah]; method = "id_hash"
            elif uname in by_handle:
                match = by_handle[uname]; method = "handle"
            elif norm(fullname) in by_name:
                match = by_name[norm(fullname)]; method = "name"

            if match:
                total_matches += 1
                log.info("    ✓ MATCH %s · @%s · method=%s", match["display_name"], uname, method)
                if not args.dry_run:
                    cur.execute(
                        # NOTA: 'instagrapi_auth' no existe en ck_watched_like_source enum
                        # actual. Próximo sprint: migración cp3 amplía enum para incluir
                        # 'instagrapi_auth' explícito. Por ahora usar 'other_scraper'.
                        """INSERT INTO watched_like_events
                             (watched_profile_id, post_id, reaction_type, source)
                           VALUES (%s, %s, 'like', 'other_scraper')
                           ON CONFLICT DO NOTHING RETURNING id""",
                        (match["id"], post_pk_db),
                    )
                    if cur.fetchone():
                        inserted += 1

        time.sleep(2)  # cortesía a la API IG

    if not args.dry_run:
        conn.commit()

    log.info("=== Resumen ===")
    log.info("  posts procesados: %d", len(posts))
    log.info("  likers capturados (total): %d", total_likers_capturados)
    log.info("  matches con watchlist: %d", total_matches)
    log.info("  inserts en BD: %d", inserted)

    cur.close(); conn.close()


if __name__ == "__main__":
    main()
