#!/usr/bin/env python3
"""
Batch NLP sentiment analysis for posts that were transcribed by whisper
but don't have sentiment_score yet.

Usage:
    docker exec crece-backend python scripts/nlp_batch_transcribed.py
    # or locally (requires pysentimiento installed):
    python backend/scripts/nlp_batch_transcribed.py [--limit N] [--dry-run]
"""
import argparse
import os
import sys

import psycopg2

DB_URL = os.environ.get(
    "DATABASE_URL_SYNC",
    "postgresql://crece:crece_dev@localhost:5438/crece",
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # Find posts that were transcribed but lack sentiment
    query = """
        SELECT p.id, p.content
        FROM social_posts p
        WHERE p.raw_data->>'transcribed' = 'true'
          AND p.sentiment_score IS NULL
          AND p.content IS NOT NULL
          AND p.content != ''
        ORDER BY p.id
    """
    if args.limit:
        query += f" LIMIT {int(args.limit)}"

    cur.execute(query)
    posts = cur.fetchall()
    print(f"Found {len(posts)} transcribed posts without sentiment")

    if not posts:
        return

    # Import pysentimiento
    print("Loading pysentimiento models...")
    try:
        from pysentimiento import create_analyzer
        sentiment_analyzer = create_analyzer(task="sentiment", lang="es")
        emotion_analyzer = create_analyzer(task="emotion", lang="es")
    except ImportError:
        print("ERROR: pysentimiento not installed. Run inside Docker container:")
        print("  docker exec crece-backend python scripts/nlp_batch_transcribed.py")
        sys.exit(1)

    print("Models loaded. Processing...")

    success = 0
    for i, (post_id, content) in enumerate(posts):
        try:
            # Truncate very long transcriptions
            text = content[:1000] if content else ""
            if not text:
                continue

            sent = sentiment_analyzer.predict(text)
            emo = emotion_analyzer.predict(text)

            # Map sentiment to score
            label = sent.output
            probas = sent.probas
            if label == "POS":
                score = probas.get("POS", 0.5)
                db_label = "POSITIVE"
            elif label == "NEG":
                score = -probas.get("NEG", 0.5)
                db_label = "NEGATIVE"
            else:
                score = 0.0
                db_label = "NEUTRAL"

            emotions = {k: round(v, 4) for k, v in emo.probas.items()}

            if not args.dry_run:
                cur.execute(
                    """UPDATE social_posts
                       SET sentiment_score = %s,
                           sentiment_label = %s,
                           emotions = %s
                       WHERE id = %s""",
                    (round(score, 4), db_label, psycopg2.extras.Json(emotions), post_id),
                )
                conn.commit()

            success += 1
            if (i + 1) % 10 == 0:
                print(f"  [{i+1}/{len(posts)}] processed...")
        except Exception as e:
            print(f"  Error on post {post_id}: {e}")

    cur.close()
    conn.close()
    print(f"\nDone. {success}/{len(posts)} posts analyzed.")


if __name__ == "__main__":
    import psycopg2.extras
    main()
