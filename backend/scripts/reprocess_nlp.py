"""One-shot script to run the NLP pipeline over existing social_posts
that don't have a sentiment_label yet.

Usage (inside the crece-backend container):
    python -m scripts.reprocess_nlp

Or via docker:
    docker exec crece-backend python -m scripts.reprocess_nlp
"""

from __future__ import annotations

import asyncio
import logging
import sys

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.social import SentimentLabel, SocialPost
from app.nlp.analyzer import NLPAnalyzer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
)
logger = logging.getLogger("reprocess_nlp")


# Map analyze() lowercase labels → SentimentLabel enum (uppercase)
LABEL_MAP = {
    "positive": SentimentLabel.POSITIVE,
    "negative": SentimentLabel.NEGATIVE,
    "neutral": SentimentLabel.NEUTRAL,
    "mixed": SentimentLabel.MIXED,
}


async def reprocess_nlp(force: bool = False) -> int:
    """Run NLP over social_posts missing sentiment_label.

    Args:
        force: if True, reprocess ALL posts (not just nulls).

    Returns:
        Number of posts updated.
    """
    analyzer = NLPAnalyzer()

    async with async_session_factory() as session:
        session: AsyncSession

        stmt = select(SocialPost)
        if not force:
            stmt = stmt.where(SocialPost.sentiment_label.is_(None))

        result = await session.execute(stmt)
        posts = result.scalars().all()

        logger.info("Loaded %d posts to reprocess (force=%s)", len(posts), force)

        if not posts:
            logger.info("Nothing to do — all posts already have sentiment_label")
            return 0

        updated = 0
        for post in posts:
            text = (post.content or "").strip()
            if not text:
                logger.debug("Post %d has empty content, skipping", post.id)
                continue

            try:
                result_nlp = analyzer.analyze(text)
            except Exception as exc:
                logger.warning("NLP failed on post %d: %s", post.id, exc)
                continue

            label_enum = LABEL_MAP.get(result_nlp.sentiment_label.lower())
            if label_enum is None:
                logger.warning(
                    "Unknown label '%s' on post %d, defaulting to NEUTRAL",
                    result_nlp.sentiment_label,
                    post.id,
                )
                label_enum = SentimentLabel.NEUTRAL

            await session.execute(
                update(SocialPost)
                .where(SocialPost.id == post.id)
                .values(
                    sentiment_score=result_nlp.sentiment_score,
                    sentiment_label=label_enum,
                    emotions=result_nlp.emotions or None,
                )
            )
            updated += 1
            logger.info(
                "Post %d → label=%s score=%.3f",
                post.id,
                label_enum.value,
                result_nlp.sentiment_score,
            )

        await session.commit()
        logger.info("Committed %d updates", updated)
        return updated


async def _main() -> int:
    force = "--force" in sys.argv
    updated = await reprocess_nlp(force=force)
    print(f"Done. {updated} posts updated.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
