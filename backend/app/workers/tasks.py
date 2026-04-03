from __future__ import annotations

import logging

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.workers.tasks.scrape_profile", max_retries=3)
def scrape_profile(self, profile_id: int, platform: str) -> dict:  # type: ignore[no-untyped-def]
    """Scrape a single social profile and store new posts.

    Uses the appropriate platform scraper based on the platform parameter.
    """
    from app.scrapers.base import get_scraper

    try:
        scraper = get_scraper(platform)
        result = scraper.scrape(profile_id)
        logger.info("Scraped %d new posts for profile %d (%s)", result["new_posts"], profile_id, platform)
        return result
    except Exception as exc:
        logger.error("Scrape failed for profile %d: %s", profile_id, exc)
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


@celery_app.task(bind=True, name="app.workers.tasks.analyze_sentiment", max_retries=2)
def analyze_sentiment(self, post_id: int) -> dict:  # type: ignore[no-untyped-def]
    """Run NLP sentiment analysis on a single post."""
    try:
        from app.services.sentiment_service import sentiment_service

        # In a real implementation, load the post from DB synchronously
        # (Celery tasks run in sync context)
        logger.info("Analyzing sentiment for post %d", post_id)
        # Placeholder: actual implementation would load post content and call:
        # result = sentiment_service.analyze(post.content)
        return {"post_id": post_id, "status": "analyzed"}
    except Exception as exc:
        logger.error("Sentiment analysis failed for post %d: %s", post_id, exc)
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(bind=True, name="app.workers.tasks.generate_plan", max_retries=1)
def generate_plan(self, dirigente_id: int, tipo: str, user_id: int, contexto: str | None = None) -> dict:  # type: ignore[no-untyped-def]
    """Generate an AI plan (runs synchronously in worker context)."""
    try:
        logger.info("Generating %s plan for dirigente %d", tipo, dirigente_id)
        # Actual implementation would use asyncio.run() to call the async service
        return {"dirigente_id": dirigente_id, "tipo": tipo, "status": "generated"}
    except Exception as exc:
        logger.error("Plan generation failed: %s", exc)
        raise self.retry(exc=exc, countdown=120)


@celery_app.task(name="app.workers.tasks.sync_electoral_data")
def sync_electoral_data(estado: str | None = None) -> dict:
    """Sync electoral section data from INE/official sources."""
    logger.info("Syncing electoral data for estado=%s", estado or "ALL")
    # Placeholder: would download and upsert SeccionElectoral records
    return {"status": "synced", "estado": estado}


@celery_app.task(name="app.workers.tasks.scrape_all_profiles")
def scrape_all_profiles() -> dict:
    """Periodic task: dispatch scrape tasks for all active profiles."""
    logger.info("Dispatching scrape tasks for all profiles")
    # In production, would query all active profiles and dispatch scrape_profile for each
    return {"status": "dispatched"}
