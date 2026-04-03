from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Abstract base class for all platform scrapers.

    Subclasses must implement scrape(), parse(), and store() methods.
    Each scraper handles a single platform and knows how to:
    1. Fetch raw data from the platform API or web
    2. Parse it into structured post objects
    3. Store new posts in the database (deduplicating by platform_post_id)
    """

    platform: str = ""

    @abstractmethod
    def scrape(self, profile_id: int) -> dict[str, Any]:
        """Execute the full scrape pipeline for a profile.

        Returns:
            dict with keys: new_posts (int), updated_profile (bool), errors (list)
        """
        ...

    @abstractmethod
    def fetch_raw(self, handle: str, **kwargs: Any) -> list[dict[str, Any]]:
        """Fetch raw post data from the platform.

        Returns a list of raw post dicts as received from the platform.
        """
        ...

    @abstractmethod
    def parse(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Parse a single raw post into a normalized structure.

        Returns a dict matching SocialPost column names.
        """
        ...

    @abstractmethod
    def update_profile_stats(self, handle: str) -> dict[str, int]:
        """Fetch current profile statistics (followers, following, posts count).

        Returns dict with followers_count, following_count, posts_count.
        """
        ...


def get_scraper(platform: str) -> BaseScraper:
    """Factory: return the scraper instance for a given platform."""
    scrapers: dict[str, type[BaseScraper]] = {}

    # Lazy imports to avoid loading heavy dependencies at module level
    from app.scrapers.facebook import FacebookScraper
    from app.scrapers.instagram import InstagramScraper
    from app.scrapers.tiktok import TikTokScraper
    from app.scrapers.twitter import TwitterScraper
    from app.scrapers.youtube import YouTubeScraper

    scrapers = {
        "twitter": TwitterScraper,
        "instagram": InstagramScraper,
        "facebook": FacebookScraper,
        "tiktok": TikTokScraper,
        "youtube": YouTubeScraper,
    }

    scraper_class = scrapers.get(platform)
    if scraper_class is None:
        raise ValueError(f"No scraper available for platform: {platform}")

    return scraper_class()
