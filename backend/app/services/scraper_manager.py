from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.social import Platform, SocialProfile

logger = logging.getLogger(__name__)


async def dispatch_scrape(
    db: AsyncSession,
    dirigente_id: int,
    platforms: list[Platform] | None = None,
) -> dict[str, str]:
    """Dispatch Celery scraping tasks for each platform profile of a dirigente.

    Returns a mapping of platform -> task_id for tracking.
    """
    from app.workers.tasks import scrape_profile

    query = select(SocialProfile).where(SocialProfile.dirigente_id == dirigente_id)
    if platforms:
        query = query.where(SocialProfile.platform.in_(platforms))

    result = await db.execute(query)
    profiles = list(result.scalars().all())

    if not profiles:
        return {}

    dispatched: dict[str, str] = {}
    for profile in profiles:
        task = scrape_profile.delay(profile.id, profile.platform.value)
        dispatched[profile.platform.value] = task.id
        logger.info(
            "Dispatched scrape task %s for profile %s (%s)",
            task.id,
            profile.handle,
            profile.platform.value,
        )

    return dispatched
