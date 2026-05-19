"""FB gap fill for Solano + Pineda via Brightdata Browser API (WSS).

Prereqs:
  - social_profiles inserted for dirigente_id=2 (rafaelsolanoperez) and =3 (saymipinedavelasco).
  - BRIGHTDATA_BROWSER_WSS env var from backend/.env.scraping-keys.
  - Node helper at /tmp/crece-playwright/fb_gap_solano_pineda.js.

Pipeline:
  Node scraper emits ndjson:
    {type:'posts_found', dirigente_id, handle, post_ids:[...]}
    {type:'comments', dirigente_id, handle, post_id, url, count, comments:[...]}
  This script:
    - On posts_found → INSERT stub rows in social_posts
    - On comments → INSERT social_comments with surrogate platform_comment_id

Surrogate platform_comment_id = sha256(post_id|author_href|text)[:40]  — idempotent dedup.
author_hash = sha256(INSTAGRAM-style FACEBOOK:author_href:salt)[:64]   — LFPDPPP.

data_source='brightdata-fb-browser-v1' (matches Joy's earlier ingest).
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import psycopg2

NODE_SCRIPT = Path('/tmp/crece-playwright/fb_gap_solano_pineda.js')
DB_DSN = os.environ.get('DB_DSN', 'host=localhost port=5438 dbname=crece user=crece password=crece_dev')
HASH_SALT = os.environ.get('COMMENT_AUTHOR_SALT', 'crece-v2-lfpdppp-salt-2026')
DATA_SOURCE = 'brightdata-fb-browser-v1'

# Load WSS from .env.scraping-keys
ENV_FILE = Path(__file__).parent.parent / '.env.scraping-keys'
WSS = None
if ENV_FILE.exists():
    for line in ENV_FILE.read_text().splitlines():
        if line.startswith('BRIGHTDATA_BROWSER_WSS='):
            WSS = line.split('=', 1)[1].strip().strip('"').strip("'")
            break
if not WSS:
    sys.exit('BRIGHTDATA_BROWSER_WSS not found in backend/.env.scraping-keys')

TARGETS = [
    {'id': 2, 'handle': 'rafaelsolanoperez'},
    {'id': 3, 'handle': 'saymipinedavelasco'},
]


def author_hash(author_href: str | None) -> str:
    raw = f"FACEBOOK:{author_href or 'anon'}:{HASH_SALT}"
    return hashlib.sha256(raw.encode()).hexdigest()


def comment_surrogate(post_id: str, author_href: str | None, text: str) -> str:
    raw = f"{post_id}|{author_href or ''}|{text}"
    return hashlib.sha256(raw.encode()).hexdigest()[:40]


def ensure_profile_id(conn, dirigente_id: int) -> int:
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM social_profiles WHERE dirigente_id=%s AND platform='FACEBOOK'",
        (dirigente_id,),
    )
    row = cur.fetchone()
    cur.close()
    if not row:
        sys.exit(f'No FB profile for dirigente_id={dirigente_id}. Insert first.')
    return row[0]


def upsert_post(conn, profile_id: int, post_id: str) -> int | None:
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM social_posts WHERE profile_id=%s AND platform_post_id=%s",
        (profile_id, post_id),
    )
    row = cur.fetchone()
    if row:
        cur.close()
        return row[0]
    now = datetime.now(UTC)
    cur.execute(
        """
        INSERT INTO social_posts
            (profile_id, platform_post_id, content, post_type, published_at,
             likes, comments, shares, views, engagement_rate,
             is_political, scraped_at)
        VALUES (%s, %s, %s, 'IMAGE', %s, 0, 0, 0, 0, 0, false, %s)
        RETURNING id
        """,
        (profile_id, post_id, '', now, now),
    )
    pid = cur.fetchone()[0]
    cur.close()
    return pid


def upsert_comment(conn, parent_post_id: int, post_id_str: str, c: dict) -> bool:
    text = (c.get('text') or '').strip()
    if not text or len(text) < 2:
        return False
    scid = comment_surrogate(post_id_str, c.get('author_href'), text)
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM social_comments WHERE parent_post_id=%s AND platform_comment_id=%s",
        (parent_post_id, scid),
    )
    if cur.fetchone():
        cur.close()
        return False
    cur.execute(
        """
        INSERT INTO social_comments
            (parent_post_id, platform_comment_id, content, author_hash,
             likes, data_source, is_reply_to_comment)
        VALUES (%s, %s, %s, %s, 0, %s, false)
        """,
        (parent_post_id, scid, text[:4000], author_hash(c.get('author_href')), DATA_SOURCE),
    )
    cur.close()
    return True


def main():
    conn = psycopg2.connect(DB_DSN)
    conn.autocommit = True

    # Map dirigente_id → profile_id
    profile_map = {t['id']: ensure_profile_id(conn, t['id']) for t in TARGETS}
    print(f'Profile map: {profile_map}', flush=True)

    payload = json.dumps({'wss': WSS, 'dirigentes': TARGETS})
    print(f'[node] launching scraper for {len(TARGETS)} dirigentes...', flush=True)
    proc = subprocess.Popen(
        ['node', str(NODE_SCRIPT)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    proc.stdin.write(payload)
    proc.stdin.close()

    stats = {'posts_inserted': 0, 'comments_inserted': 0, 'errors': 0}
    post_id_db_map = {}  # (dirigente_id, post_id_str) -> parent_post_id

    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except Exception as e:
            print(f'[bad-line] {line[:120]} ({e})', flush=True)
            continue
        t = ev.get('type')
        if t == 'posts_found':
            did = ev['dirigente_id']
            prof_id = profile_map[did]
            for pid in ev.get('post_ids', []):
                db_pid = upsert_post(conn, prof_id, pid)
                if db_pid is not None:
                    post_id_db_map[(did, pid)] = db_pid
                    stats['posts_inserted'] += 1
            print(f'[posts_found] dirigente_id={did}: {len(ev.get("post_ids", []))} posts', flush=True)
        elif t == 'comments':
            did = ev['dirigente_id']
            pid_str = ev['post_id']
            key = (did, pid_str)
            parent = post_id_db_map.get(key)
            if parent is None:
                prof_id = profile_map[did]
                parent = upsert_post(conn, prof_id, pid_str)
                post_id_db_map[key] = parent
            new_count = 0
            for c in ev.get('comments', []):
                if upsert_comment(conn, parent, pid_str, c):
                    new_count += 1
            stats['comments_inserted'] += new_count
            print(f'[comments] dirigente={did} post={pid_str[:20]}... new={new_count}/{ev.get("count",0)}', flush=True)
        elif t == 'error':
            stats['errors'] += 1
            print(f'[error] {ev}', flush=True)
        elif t == 'profile_start':
            print(f'[profile_start] dirigente={ev["dirigente_id"]} handle={ev["handle"]}', flush=True)

    stderr = proc.stderr.read() if proc.stderr else ''
    rc = proc.wait()
    print(f'\nnode rc={rc}', flush=True)
    if stderr:
        print(f'stderr:\n{stderr[:2000]}', flush=True)
    print(f'\nFINAL STATS: {stats}', flush=True)


if __name__ == '__main__':
    main()
