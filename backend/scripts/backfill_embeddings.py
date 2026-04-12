"""D-S4-08 — Backfill embeddings for social_posts using sentence-transformers.

Processes posts in batches, generates 384-dim embeddings with
paraphrase-multilingual-MiniLM-L12-v2, and UPDATEs the embedding column.

Usage:
    python scripts/backfill_embeddings.py [--batch-size 50]
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sentence_transformers import SentenceTransformer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def backfill(batch_size: int = 50) -> int:
    """Embed all social_posts that have NULL embedding."""
    logger.info("Loading sentence-transformers model (CPU)...")
    model = SentenceTransformer(
        "paraphrase-multilingual-MiniLM-L12-v2",
        device="cpu",
    )

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    total_processed = 0

    async with async_session() as db:
        # Count pending
        result = await db.execute(
            text("SELECT COUNT(*) FROM social_posts WHERE embedding IS NULL")
        )
        pending = result.scalar() or 0
        logger.info("Posts pending embedding: %d", pending)

        if pending == 0:
            logger.info("Nothing to do — all posts already have embeddings")
            await engine.dispose()
            return 0

        # Process in batches
        offset = 0
        while True:
            result = await db.execute(
                text("""
                    SELECT id, content FROM social_posts
                    WHERE embedding IS NULL
                    ORDER BY id
                    LIMIT :batch
                """),
                {"batch": batch_size},
            )
            rows = result.fetchall()
            if not rows:
                break

            ids = [r.id for r in rows]
            texts = [r.content or "" for r in rows]

            # Generate embeddings (CPU, blocking but fast for small batches)
            embeddings = model.encode(texts, show_progress_bar=False)

            # Update each row
            for post_id, emb in zip(ids, embeddings):
                vec_str = "[" + ",".join(str(float(x)) for x in emb) + "]"
                await db.execute(
                    text("UPDATE social_posts SET embedding = :vec WHERE id = :id"),
                    {"vec": vec_str, "id": post_id},
                )

            await db.commit()
            total_processed += len(rows)
            offset += len(rows)
            logger.info("Batch done: %d/%d posts embedded", total_processed, pending)

    await engine.dispose()
    return total_processed


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill social_posts embeddings")
    parser.add_argument("--batch-size", type=int, default=50, help="Posts per batch")
    args = parser.parse_args()

    total = asyncio.run(backfill(args.batch_size))
    logger.info("Backfill complete: %d posts embedded", total)


if __name__ == "__main__":
    main()
