"""
Scrape real posts for the 4 new dirigentes (GOB-OAXACA + CDMX-IND).
Uses the project's existing scraper infrastructure (profile_id based).
Then runs NLP via reprocess_nlp.

Run with: docker exec crece-backend python -m scripts.scrape_new_dirigentes
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.dirigente import Dirigente
from app.models.social import SocialProfile

TARGET_DIRIGENTES = [
    "Saymi Adriana Pineda Velasco",
    "Yesenia Nolasco Ramírez",
    "Gabriela Jiménez Godoy",
    "César Cravioto Romero",
]


async def main():
    engine = create_async_engine(str(settings.DATABASE_URL), echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Collect profile IDs to scrape
    profiles_to_scrape: list[tuple[int, str, str]] = []  # (profile_id, platform, handle)

    async with async_session() as session:
        for name in TARGET_DIRIGENTES:
            result = await session.execute(
                select(Dirigente).where(Dirigente.full_name == name)
            )
            dirigente = result.scalar_one_or_none()
            if not dirigente:
                logger.warning(f"Dirigente not found: {name}")
                continue

            profiles = (await session.execute(
                select(SocialProfile).where(SocialProfile.dirigente_id == dirigente.id)
            )).scalars().all()

            for p in profiles:
                profiles_to_scrape.append((p.id, p.platform.value.lower(), p.handle))
                logger.info(f"  Queued: {name} — {p.platform.value} @{p.handle} (profile_id={p.id})")

    await engine.dispose()

    # Run scrapers (synchronous — they create their own DB sessions)
    from app.scrapers.base import get_scraper

    for profile_id, platform, handle in profiles_to_scrape:
        logger.info(f"Scraping {platform} @{handle} (profile_id={profile_id})...")
        try:
            scraper = get_scraper(platform)
            result = scraper.scrape(profile_id=profile_id)
            new_posts = result.get("new_posts", 0)
            errors = result.get("errors", [])
            logger.info(f"  OK: {new_posts} new posts" + (f", errors: {errors}" if errors else ""))
        except Exception as e:
            logger.error(f"  FAIL: {platform} @{handle} — {type(e).__name__}: {e}")

    # Run NLP on new posts
    logger.info("\nRunning NLP on new posts...")
    try:
        from scripts.reprocess_nlp import reprocess_nlp
        updated = await reprocess_nlp()
        logger.info(f"  NLP processed {updated} posts")
    except Exception as e:
        logger.error(f"  NLP failed: {type(e).__name__}: {e}")

    # Summary
    engine2 = create_async_engine(str(settings.DATABASE_URL), echo=False)
    async_session2 = sessionmaker(engine2, class_=AsyncSession, expire_on_commit=False)
    async with async_session2() as session:
        for name in TARGET_DIRIGENTES:
            result = await session.execute(
                select(Dirigente).where(Dirigente.full_name == name)
            )
            d = result.scalar_one_or_none()
            if not d:
                continue
            post_count = (await session.execute(
                text("""
                    SELECT count(*) FROM social_posts sp
                    JOIN social_profiles p ON sp.profile_id = p.id
                    WHERE p.dirigente_id = :did
                """),
                {"did": d.id},
            )).scalar()
            logger.info(f"  {name}: {post_count} posts in DB")

    await engine2.dispose()
    logger.info("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
