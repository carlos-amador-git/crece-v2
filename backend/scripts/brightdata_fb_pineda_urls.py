"""FB comments for Pineda (dirigente_id=3) via manual post URLs + Brightdata Browser.

Input: /tmp/crece-playwright/pineda_urls.txt  (one URL per line)
For each URL:
  1. Derive canonical platform_post_id: pfbid pattern || pcb=... || reel/{id} || fbid=...
  2. Ensure social_post row exists (profile_id=27)
  3. Invoke Node helper to extract comments
  4. Insert comments with data_source='brightdata-fb-browser-v1'
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg2

URLS_FILE = Path('/tmp/crece-playwright/pineda_urls.txt')
NODE_SCRIPT = Path('/tmp/crece-playwright/fb_comments_by_url.js')
DB_DSN = os.environ.get('DB_DSN', 'host=localhost port=5438 dbname=crece user=crece password=crece_dev')
HASH_SALT = os.environ.get('COMMENT_AUTHOR_SALT', 'crece-v2-lfpdppp-salt-2026')
DATA_SOURCE = 'brightdata-fb-browser-v1'
PROFILE_ID = 27  # dirigente_id=3 (Pineda) FACEBOOK — from prior insert

ENV_FILE = Path(__file__).parent.parent / '.env.scraping-keys'
WSS = None
for line in ENV_FILE.read_text().splitlines():
    if line.startswith('BRIGHTDATA_BROWSER_WSS='):
        WSS = line.split('=', 1)[1].strip().strip('"').strip("'")
        break
if not WSS:
    sys.exit('BRIGHTDATA_BROWSER_WSS not found')


def extract_post_id(url: str) -> str:
    """Derive canonical platform_post_id from a FB URL."""
    m = re.search(r'/posts/(pfbid[0-9A-Za-z]+)', url)
    if m:
        return m.group(1)
    m = re.search(r'set=pcb\.(\d+)', url)
    if m:
        return m.group(1)
    m = re.search(r'/reel/(\d+)', url)
    if m:
        return m.group(1)
    m = re.search(r'fbid=(\d+)', url)
    if m:
        return m.group(1)
    return hashlib.sha256(url.encode()).hexdigest()[:24]


def author_hash(author_href: str | None) -> str:
    raw = f"FACEBOOK:{author_href or 'anon'}:{HASH_SALT}"
    return hashlib.sha256(raw.encode()).hexdigest()


def comment_surrogate(post_id: str, author_href: str | None, text: str) -> str:
    raw = f"{post_id}|{author_href or ''}|{text}"
    return hashlib.sha256(raw.encode()).hexdigest()[:40]


def ensure_post(conn, profile_id: int, platform_post_id: str) -> int:
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM social_posts WHERE profile_id=%s AND platform_post_id=%s",
        (profile_id, platform_post_id),
    )
    row = cur.fetchone()
    if row:
        cur.close()
        return row[0]
    now = datetime.now(timezone.utc)
    cur.execute(
        """
        INSERT INTO social_posts
            (profile_id, platform_post_id, content, post_type, published_at,
             likes, comments, shares, views, engagement_rate, is_political, scraped_at)
        VALUES (%s, %s, %s, 'IMAGE', %s, 0, 0, 0, 0, 0, false, %s) RETURNING id
        """,
        (profile_id, platform_post_id, '', now, now),
    )
    pid = cur.fetchone()[0]
    cur.close()
    return pid


def insert_comment(conn, parent_id: int, platform_post_id: str, c: dict) -> bool:
    text = (c.get('text') or '').strip()
    if not text or len(text) < 2:
        return False
    scid = comment_surrogate(platform_post_id, c.get('author_href'), text)
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM social_comments WHERE parent_post_id=%s AND platform_comment_id=%s",
        (parent_id, scid),
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
        (parent_id, scid, text[:4000], author_hash(c.get('author_href')), DATA_SOURCE),
    )
    cur.close()
    return True


def main():
    urls = [l.strip() for l in URLS_FILE.read_text().splitlines() if l.strip() and not l.startswith('#')]
    print(f'URLs input: {len(urls)}')
    conn = psycopg2.connect(DB_DSN)
    conn.autocommit = True

    items = []
    for url in urls:
        ppid = extract_post_id(url)
        db_id = ensure_post(conn, PROFILE_ID, ppid)
        items.append({'url': url, 'post_id_db': db_id, 'platform_post_id': ppid})
    print(f'social_posts ensured: {len(items)}')

    payload = json.dumps({'wss': WSS, 'items': items})
    proc = subprocess.Popen(['node', str(NODE_SCRIPT)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    proc.stdin.write(payload); proc.stdin.close()

    total_inserted = 0
    errors = 0
    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.strip()
        if not line: continue
        try:
            ev = json.loads(line)
        except Exception as e:
            print(f'[bad-line] {line[:120]}'); continue
        if ev.get('type') == 'comments':
            new = 0
            for c in ev.get('comments', []):
                if insert_comment(conn, ev['post_id_db'], ev['platform_post_id'], c):
                    new += 1
            total_inserted += new
            print(f'[ok] post={ev["platform_post_id"][:24]} raw={ev.get("count",0)} inserted={new}')
        elif ev.get('type') == 'error':
            errors += 1
            print(f'[err] {ev}')

    rc = proc.wait()
    stderr = proc.stderr.read() if proc.stderr else ''
    print(f'\nnode rc={rc}  inserted={total_inserted}  errors={errors}')
    if stderr: print(f'stderr:\n{stderr[:1500]}')


if __name__ == '__main__':
    main()
