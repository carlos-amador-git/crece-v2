"""Playwright-based scraper for Instagram comments → social_comments table.

Uses CEO's authenticated Chrome profile in /tmp/crece-playwright/profile.
Invokes Node helper /tmp/crece-playwright/ig_scrape_prod.js for the actual
browser work; this script handles DB queries, SHA256 hashing for LFPDPPP
compliance, and idempotent upserts.

Sprint B continuation — IG comments slot. data_source='playwright-ig-cookies-v1'.

Usage:
  python3 backend/scripts/playwright_ig_comments.py [--dirigente-id N] [--top-posts 10] [--dry-run]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import psycopg2

NODE_SCRIPT = Path('/tmp/crece-playwright/ig_scrape_prod.js')
DB_DSN = os.environ.get(
    'DB_DSN',
    'host=localhost port=5438 dbname=crece user=crece password=crece_dev',
)
HASH_SALT = os.environ.get('COMMENT_AUTHOR_SALT', 'crece-v2-lfpdppp-salt-2026')
DATA_SOURCE = 'playwright-ig-cookies-v1'


def author_hash(author_id: str | None) -> str:
    raw = f"INSTAGRAM:{author_id or 'anon'}:{HASH_SALT}"
    return hashlib.sha256(raw.encode()).hexdigest()


def fetch_targets(conn, dirigente_id: int | None, top: int) -> list[dict]:
    """Return [{post_id, shortcode, dirigente_id}] for top IG posts with comments>0."""
    where = "WHERE p.platform='INSTAGRAM' AND sp.comments > 0"
    params: tuple = ()
    if dirigente_id:
        where += " AND p.dirigente_id = %s"
        params = (dirigente_id,)
    sql = f"""
        SELECT sp.id, sp.platform_post_id, p.dirigente_id, sp.comments
        FROM social_posts sp
        JOIN social_profiles p ON sp.profile_id = p.id
        {where}
        ORDER BY p.dirigente_id, sp.comments DESC
    """
    cur = conn.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall()
    cur.close()
    # Group by dirigente_id, take top N each
    by_dir: dict[int, list] = {}
    for r in rows:
        by_dir.setdefault(r[2], []).append(r)
    targets = []
    for did, rs in by_dir.items():
        for r in rs[:top]:
            targets.append({'post_id': r[0], 'shortcode': r[1], 'dirigente_id': did, 'declared_comments': r[3]})
    return targets


def run_scraper(targets: list[dict]) -> list[dict]:
    """Pipe targets to node scraper, parse ndjson stdout."""
    payload = json.dumps([{'post_id': t['post_id'], 'shortcode': t['shortcode']} for t in targets])
    print(f'[node] launching scraper for {len(targets)} posts...', file=sys.stderr, flush=True)
    proc = subprocess.run(
        ['node', str(NODE_SCRIPT)],
        input=payload,
        capture_output=True,
        text=True,
        timeout=60 + len(targets) * 25,
    )
    if proc.returncode != 0:
        print(f'[node] stderr:\n{proc.stderr}', file=sys.stderr)
        raise RuntimeError(f'node exited {proc.returncode}')
    out = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception as e:
            print(f'[node] bad line: {line[:120]} ({e})', file=sys.stderr)
    return out


def upsert_comments(conn, results: list[dict], dry_run: bool) -> dict:
    cur = conn.cursor()
    stats = {'inserted': 0, 'skipped_dup': 0, 'errors_post': 0, 'comments_seen': 0}
    sql = """
        INSERT INTO social_comments
            (parent_post_id, platform_comment_id, content, author_hash,
             likes, published_at, data_source, is_reply_to_comment, parent_comment_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, false, NULL)
        ON CONFLICT (parent_post_id, platform_comment_id) DO NOTHING
    """
    # Note: there is no unique constraint by default — rely on ON CONFLICT only if exists.
    # Fallback: SELECT existence first.
    check_sql = "SELECT 1 FROM social_comments WHERE parent_post_id=%s AND platform_comment_id=%s LIMIT 1"
    insert_sql_basic = """
        INSERT INTO social_comments
            (parent_post_id, platform_comment_id, content, author_hash,
             likes, published_at, data_source, is_reply_to_comment)
        VALUES (%s, %s, %s, %s, %s, %s, %s, false)
    """
    for r in results:
        if 'error' in r:
            stats['errors_post'] += 1
            print(f'[err] post={r.get("post_id")} shortcode={r.get("shortcode")}: {r["error"]}', file=sys.stderr)
            continue
        post_id = r['post_id']
        for c in r.get('comments', []):
            stats['comments_seen'] += 1
            cur.execute(check_sql, (post_id, c['platform_comment_id']))
            if cur.fetchone():
                stats['skipped_dup'] += 1
                continue
            if dry_run:
                stats['inserted'] += 1
                continue
            cur.execute(
                insert_sql_basic,
                (
                    post_id,
                    c['platform_comment_id'],
                    c['content'][:5000],
                    author_hash(c.get('author_id')),
                    c.get('likes', 0),
                    c.get('published_at'),
                    DATA_SOURCE,
                ),
            )
            stats['inserted'] += 1
    if not dry_run:
        conn.commit()
    cur.close()
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dirigente-id', type=int, default=None)
    ap.add_argument('--top-posts', type=int, default=10)
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    if not NODE_SCRIPT.exists():
        sys.exit(f'Node script not found: {NODE_SCRIPT}')

    conn = psycopg2.connect(DB_DSN)
    targets = fetch_targets(conn, args.dirigente_id, args.top_posts)
    print(f'targets: {len(targets)} posts across {len(set(t["dirigente_id"] for t in targets))} dirigentes')
    if not targets:
        sys.exit('No targets found.')
    by_dir = {}
    for t in targets:
        by_dir.setdefault(t['dirigente_id'], []).append(t)
    for did, ts in by_dir.items():
        print(f'  dirigente_id={did}: {len(ts)} posts ({sum(t["declared_comments"] for t in ts)} declared)')

    results = run_scraper(targets)
    print(f'\nresults from scraper: {len(results)} entries')

    stats = upsert_comments(conn, results, args.dry_run)
    print(f'\nstats: {stats}')
    print(f'mode: {"DRY-RUN" if args.dry_run else "WRITE"}')
    conn.close()


if __name__ == '__main__':
    main()
