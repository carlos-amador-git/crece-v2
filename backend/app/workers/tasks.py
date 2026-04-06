from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _get_sync_session():
    """Create a synchronous SQLAlchemy session for Celery tasks."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from app.core.config import settings

    engine = create_engine(settings.DATABASE_URL_SYNC, echo=False)
    return Session(engine)


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
    """Run NLP sentiment analysis on a single post.

    After analysis, checks for toxicity spikes and generates crisis alerts
    when a profile has 2+ toxic posts within a 2-hour window.
    """
    try:
        from app.services.sentiment_service import sentiment_service

        logger.info("Analyzing sentiment for post %d", post_id)

        session = _get_sync_session()
        try:
            from app.models.social import SentimentAnalysis, SocialPost, SocialProfile

            post = session.get(SocialPost, post_id)
            if post is None:
                logger.warning("Post %d not found, skipping sentiment analysis", post_id)
                return {"post_id": post_id, "status": "skipped", "reason": "post_not_found"}

            # Run sentiment analysis
            analysis_result = sentiment_service.analyze(post.content or "")

            # Convert dataclass to dict for downstream use
            result = {
                "model": "pysentimiento",
                "sentiment_score": analysis_result.sentiment_score,
                "sentiment_label": analysis_result.sentiment_label,
                "emotions": analysis_result.emotions,
                "topics": analysis_result.topics,
                "toxicity_score": analysis_result.toxicity_score,
            }

            # Store the analysis
            analysis = SentimentAnalysis(
                post_id=post_id,
                model_used="pysentimiento",
                sentiment_score=analysis_result.sentiment_score,
                sentiment_label=analysis_result.sentiment_label,
                emotions=analysis_result.emotions,
                topics={"topics": analysis_result.topics} if analysis_result.topics else None,
                is_toxic=analysis_result.is_toxic,
                toxicity_score=analysis_result.toxicity_score,
            )
            session.add(analysis)

            # Secondary model: sentiment-analysis-spanish (validation)
            secondary_result = sentiment_service.analyze_secondary(post.content or "")
            if secondary_result is not None:
                secondary_analysis = SentimentAnalysis(
                    post_id=post_id,
                    model_used="sentiment-spanish",
                    sentiment_score=secondary_result.sentiment_score,
                    sentiment_label=secondary_result.sentiment_label,
                    emotions=None,
                    topics=None,
                    is_toxic=False,
                    toxicity_score=0.0,
                )
                session.add(secondary_analysis)

            session.commit()

            # ── Crisis alert generation ──────────────────────────
            _check_toxicity_alert(session, post_id, post, result)

            return {"post_id": post_id, "status": "analyzed"}
        finally:
            session.close()
    except Exception as exc:
        logger.error("Sentiment analysis failed for post %d: %s", post_id, exc)
        raise self.retry(exc=exc, countdown=30)


def _check_toxicity_alert(session, post_id: int, post, result: dict) -> None:
    """Check for toxicity spike and generate crisis alert if warranted.

    Creates an AlertaCrisis when:
    - Current post has toxicity_score > 0.7
    - The same profile has 2+ toxic posts in the last 2 hours
    - No similar alert exists for this profile in the last hour
    """
    from sqlalchemy import func, select

    from app.models.alerta_crisis import AlertaCrisis
    from app.models.social import SentimentAnalysis, SocialPost, SocialProfile

    toxicity_score = result.get("toxicity_score", 0.0)
    if toxicity_score <= 0.7:
        return

    two_hours_ago = datetime.now(UTC) - timedelta(hours=2)

    # Count toxic posts from same profile in last 2 hours
    toxic_count_query = (
        select(func.count(SocialPost.id))
        .join(SentimentAnalysis, SocialPost.id == SentimentAnalysis.post_id)
        .where(
            SocialPost.profile_id == post.profile_id,
            SentimentAnalysis.toxicity_score > 0.7,
            SocialPost.scraped_at > two_hours_ago,
        )
    )
    toxic_count = session.execute(toxic_count_query).scalar() or 0

    if toxic_count < 2:
        return

    # Get profile's org_id via dirigente
    profile = session.get(SocialProfile, post.profile_id)
    org_id = profile.dirigente.org_id if profile and profile.dirigente else None

    severity = "alta" if toxicity_score > 0.8 else "media"

    # Check if similar alert exists in last hour
    one_hour_ago = datetime.now(UTC) - timedelta(hours=1)
    existing = session.execute(
        select(AlertaCrisis).where(
            AlertaCrisis.perfil_id == post.profile_id,
            AlertaCrisis.tipo == "toxicity_spike",
            AlertaCrisis.created_at > one_hour_ago,
        )
    ).scalar_one_or_none()

    if existing is not None:
        return

    alert = AlertaCrisis(
        org_id=org_id or 1,
        perfil_id=post.profile_id,
        tipo="toxicity_spike",
        severidad=severity,
        descripcion=f"Detectados {toxic_count} posts toxicos en las ultimas 2 horas para este perfil",
        post_ids=[post_id],
        estado="nueva",
    )
    session.add(alert)
    session.commit()
    logger.warning(
        "Created toxicity alert for profile %d: %s",
        post.profile_id,
        severity,
    )


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
