"""Twitter/X replies scraper via Playwright + CEO cookies.

Fetches top-N posts per dirigente (by engagement), navigates to each tweet,
extracts visible replies via DOM, hashes author @handle and inserts into
social_comments with data_source='playwright-x-cookies-v1'.

LFPDPPP: author_hash = SHA256(TWITTER:handle:salt). Raw handle never persisted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg2

NODE_SCRIPT = Path('/tmp/crece-playwright/x_replies_scrape.js')
DB_DSN = os.environ.get('DB_DSN', 'host=localhost port=5438 dbname=crece user=crece password=crece_dev')
HASH_SALT = os.environ.get('COMMENT_AUTHOR_SALT', 'crece-v2-lfpdppp-salt-2026')
DATA_SOURCE = 'playwright-x-cookies-v1'


def author_hash(handle: str | None) -> str:
    raw = f"TWITTER:{(handle or 'anon').lower()}:{HASH_SALT}"
    return hashlib.sha256(raw.encode()).hexdigest()


def fetch_targets(conn, dirigente_id: int | None, top: int):
    where = "WHERE p.platform='TWITTER'"
    params: tuple = ()
    if dirigente_id:
        where += " AND p.dirigente_id=%s"
        params = (dirigente_id,)
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT sp.id, sp.platform_post_id, p.dirigente_id, p.handle
        FROM social_posts sp
        JOIN social_profiles p ON sp.profile_id=p.id
        {where}
        ORDER BY p.dirigente_id, sp.comments DESC NULLS LAST, sp.likes DESC NULLS LAST
        """,
        params,
    )
    rows = cur.fetchall()
    cur.close()
    by_dir = {}
    for r in rows:
        by_dir.setdefault(r[2], []).append(r)
    targets = []
    for did, rs in by_dir.items():
        for r in rs[:top]:
            db_id, ppid, _, handle = r
            h = handle.lstrip('@')
            targets.append({
                'post_id_db': db_id,
                'platform_post_id': ppid,
                'tweet_url': f'https://x.com/{h}/status/{ppid}',
            })
    return targets


def insert_reply(conn, parent_id: int, platform_post_id: str, reply: dict) -> bool:
    text = (reply.get('text') or '').strip()
    handle = reply.get('handle')
    status_id = reply.get('status_id')
    if not text or not handle or len(text) < 2:
        return False
    cid = status_id or hashlib.sha256(f"{platform_post_id}|{handle}|{text}".encode()).hexdigest()[:40]
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM social_comments WHERE parent_post_id=%s AND platform_comment_id=%s",
        (parent_id, cid[:255]),
    )
    if cur.fetchone():
        cur.close()
        return False
    dt = None
    if reply.get('datetime'):
        try:
            dt = datetime.fromisoformat(reply['datetime'].replace('Z', '+00:00'))
        except Exception:
            dt = None
    try:
        cur.execute(
            """
            INSERT INTO social_comments
                (parent_post_id, platform_comment_id, content, author_hash,
                 likes, data_source, is_reply_to_comment, published_at)
            VALUES (%s, %s, %s, %s, 0, %s, false, %s)
            ON CONFLICT (platform_comment_id) DO NOTHING
            """,
            (parent_id, cid[:255], text[:4000], author_hash(handle), DATA_SOURCE, dt),
        )
    except Exception as e:
        print(f'    [insert-skip] {str(e)[:80]}', flush=True)
        cur.close()
        return False
    cur.close()
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dirigente-id', type=int, default=None)
    ap.add_argument('--top-posts', type=int, default=5)
    args = ap.parse_args()

    conn = psycopg2.connect(DB_DSN)
    conn.autocommit = True
    targets = fetch_targets(conn, args.dirigente_id, args.top_posts)
    print(f'targets: {len(targets)} tweets')
    if not targets:
        sys.exit('No targets')

    payload = json.dumps(targets)
    proc = subprocess.Popen(['node', str(NODE_SCRIPT)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    proc.stdin.write(payload); proc.stdin.close()

    stats = {'ok': 0, 'errors': 0, 'inserted': 0, 'seen': 0}
    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.strip()
        if not line: continue
        try: ev = json.loads(line)
        except: continue
        if ev.get('type') == 'replies':
            stats['ok'] += 1
            new = 0
            for r in ev.get('replies', []):
                stats['seen'] += 1
                if insert_reply(conn, ev['post_id_db'], ev['platform_post_id'], r):
                    new += 1
            stats['inserted'] += new
            print(f'[{ev["post_id_db"]}] raw={ev["count"]} new={new} url={ev["url"][:70]}', flush=True)
        elif ev.get('type') == 'error':
            stats['errors'] += 1
            print(f'[err] {ev}', flush=True)
    proc.wait()
    err = proc.stderr.read() if proc.stderr else ''
    print(f'\nstats: {stats}')
    if err: print(f'stderr:\n{err[:1200]}')


if __name__ == '__main__':
    main()
