"""YouTube comments via yt-dlp — offline, unrestricted, capped at 500/video.

Queries all YT videos in BD for dirigentes with social_profiles.platform='YOUTUBE'.
For each video: runs yt-dlp with --write-info-json + --write-comments, parses JSON
output, inserts comments with data_source='ytdlp-v1'.

LFPDPPP: author_id hashed with SHA256+salt. Raw channel_id never persisted.

Usage:
  python3 backend/scripts/ytdlp_youtube_comments.py [--dirigente-id N] [--max-comments 200]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from datetime import UTC, datetime

import psycopg2

DB_DSN = os.environ.get('DB_DSN', 'host=localhost port=5438 dbname=crece user=crece password=crece_dev')
HASH_SALT = os.environ.get('COMMENT_AUTHOR_SALT', 'crece-v2-lfpdppp-salt-2026')
DATA_SOURCE = 'ytdlp-v1'


def author_hash(channel_id: str | None) -> str:
    raw = f"YOUTUBE:{channel_id or 'anon'}:{HASH_SALT}"
    return hashlib.sha256(raw.encode()).hexdigest()


def fetch_videos(conn, dirigente_id: int | None) -> list[tuple]:
    where = "WHERE p.platform='YOUTUBE'"
    params: tuple = ()
    if dirigente_id:
        where += " AND p.dirigente_id=%s"
        params = (dirigente_id,)
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT sp.id, sp.platform_post_id, p.dirigente_id
        FROM social_posts sp
        JOIN social_profiles p ON sp.profile_id=p.id
        {where}
        ORDER BY p.dirigente_id, sp.published_at DESC NULLS LAST
        """,
        params,
    )
    rows = cur.fetchall()
    cur.close()
    return rows


def run_ytdlp(video_id: str, max_comments: int) -> list[dict]:
    """Run yt-dlp, return list of comment dicts."""
    url = f'https://www.youtube.com/watch?v={video_id}'
    cmd = [
        'yt-dlp',
        '--skip-download',
        '--write-comments',
        '--no-write-info-json',
        '--dump-single-json',
        '--extractor-args', f'youtube:max_comments={max_comments};comment_sort=top',
        '--no-warnings',
        url,
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
    except subprocess.TimeoutExpired:
        print('    [timeout]', flush=True)
        return []
    if r.returncode != 0:
        err = r.stderr.strip().split('\n')[-1][:150]
        print(f'    [rc={r.returncode}] {err}', flush=True)
        return []
    try:
        data = json.loads(r.stdout)
    except Exception as e:
        print(f'    [bad-json] {e}', flush=True)
        return []
    return data.get('comments', []) or []


def insert_comment(conn, parent_id: int, c: dict) -> bool:
    text = (c.get('text') or '').strip()
    cid = c.get('id')
    if not cid or not text or len(text) < 2:
        return False
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM social_comments WHERE parent_post_id=%s AND platform_comment_id=%s",
        (parent_id, cid[:255]),
    )
    if cur.fetchone():
        cur.close()
        return False
    cur.execute(
        """
        INSERT INTO social_comments
            (parent_post_id, platform_comment_id, content, author_hash,
             likes, data_source, is_reply_to_comment, parent_comment_id, published_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, NULL, %s)
        """,
        (
            parent_id,
            cid[:255],
            text[:4000],
            author_hash(c.get('author_id') or c.get('author')),
            c.get('like_count') or 0,
            DATA_SOURCE,
            bool(c.get('parent') and c.get('parent') != 'root'),
            (datetime.fromtimestamp(c['timestamp'], UTC) if c.get('timestamp') else None),
        ),
    )
    cur.close()
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dirigente-id', type=int, default=None)
    ap.add_argument('--max-comments', type=int, default=200)
    args = ap.parse_args()

    conn = psycopg2.connect(DB_DSN)
    conn.autocommit = True
    videos = fetch_videos(conn, args.dirigente_id)
    print(f'videos: {len(videos)}')

    total = {'videos': 0, 'with_comments': 0, 'comments_inserted': 0, 'errors': 0}
    for vid_row in videos:
        db_id, vid, did = vid_row
        total['videos'] += 1
        print(f'[{total["videos"]}/{len(videos)}] dirigente={did} vid={vid}', flush=True)
        comments = run_ytdlp(vid, args.max_comments)
        if not comments:
            continue
        total['with_comments'] += 1
        new_ins = 0
        for c in comments:
            if insert_comment(conn, db_id, c):
                new_ins += 1
        total['comments_inserted'] += new_ins
        print(f'    -> raw={len(comments)} inserted={new_ins}', flush=True)

    print(f'\nFINAL: {total}')


if __name__ == '__main__':
    main()
