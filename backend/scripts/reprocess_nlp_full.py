#!/usr/bin/env python3
"""
Re-process posts with analyze_full() to populate:
- controversy_score (Cardiff NLP offensive)
- toxicity_score (Citizenlab multilingual)
- topics_jsonb (XLM-RoBERTa zero-shot)
- platform_adjusted_sentiment (platform bias correction)
- nlp_model_version = 'multi-model-v1'

Idempotent: skips posts already at multi-model-v1.

Run inside container:
    docker exec crece-backend python scripts/reprocess_nlp_full.py [--limit N] [--batch 20]
"""
import argparse
import json
import os
import sys
from datetime import datetime

import psycopg2

DB_URL = os.environ.get("DATABASE_URL_SYNC", "postgresql://crece:crece_dev@localhost:5438/crece")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Max posts to process")
    parser.add_argument("--batch", type=int, default=20, help="Commit batch size")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # Import NLP analyzer inside container
    sys.path.insert(0, "/app")
    from app.nlp.analyzer import NLPAnalyzer

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    query = """
        SELECT p.id, p.content, sp.platform::text
        FROM social_posts p
        JOIN social_profiles sp ON p.profile_id = sp.id
        WHERE p.content IS NOT NULL
          AND p.content != ''
          AND (p.nlp_model_version IS NULL OR p.nlp_model_version != 'multi-model-v1')
        ORDER BY p.id
    """
    if args.limit:
        query += f" LIMIT {int(args.limit)}"

    cur.execute(query)
    posts = cur.fetchall()
    total = len(posts)
    print(f"Found {total} posts to re-process with analyze_full()")

    if total == 0:
        return

    analyzer = NLPAnalyzer()
    print("Loading models (lazy)...")

    stats = {"success": 0, "fail": 0, "start": datetime.now()}

    for i, (post_id, content, platform) in enumerate(posts):
        try:
            result = analyzer.analyze_full(content[:2000], platform=platform.lower())

            if args.dry_run:
                if i < 3:
                    print(json.dumps(result, indent=2, default=str)[:300])
                continue

            cur.execute(
                """UPDATE social_posts SET
                    controversy_score = %s,
                    toxicity_score = %s,
                    topics_jsonb = %s,
                    platform_adjusted_sentiment = %s,
                    nlp_model_version = 'multi-model-v1'
                   WHERE id = %s""",
                (
                    result.get("controversy_score"),
                    result.get("toxicity"),
                    json.dumps(result.get("topics")) if result.get("topics") else None,
                    result.get("platform_adjusted_sentiment"),
                    post_id,
                ),
            )
            stats["success"] += 1

            if (i + 1) % args.batch == 0:
                conn.commit()
                elapsed = (datetime.now() - stats["start"]).total_seconds()
                rate = (i + 1) / elapsed
                eta = (total - i - 1) / rate
                print(f"  [{i+1}/{total}] processed ({rate:.1f} posts/sec, ETA {eta/60:.1f} min)")

        except Exception as e:
            stats["fail"] += 1
            if stats["fail"] < 5:
                print(f"  Error post {post_id}: {type(e).__name__}: {e}")

    if not args.dry_run:
        conn.commit()

    elapsed = (datetime.now() - stats["start"]).total_seconds()
    print("\n=== Results ===")
    print(f"  Success: {stats['success']}")
    print(f"  Failed:  {stats['fail']}")
    print(f"  Time:    {elapsed/60:.1f} min ({stats['success']/max(elapsed,1):.1f} posts/sec)")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
