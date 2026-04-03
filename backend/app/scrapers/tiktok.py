from __future__ import annotations

import logging
from typing import Any

from app.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class TikTokScraper(BaseScraper):
    """TikTok scraper using unofficial API patterns.

    Note: TikTok aggressively blocks scraping. Consider using
    TikTok Research API for authorized access.
    """

    platform = "tiktok"

    def scrape(self, profile_id: int) -> dict[str, Any]:
        logger.info("TikTokScraper.scrape called for profile_id=%d", profile_id)
        return {"new_posts": 0, "updated_profile": False, "errors": []}

    def fetch_raw(self, handle: str, **kwargs: Any) -> list[dict[str, Any]]:
        logger.info("TikTokScraper.fetch_raw for @%s", handle)
        return []

    def parse(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "platform_post_id": raw_data.get("id", ""),
            "content": raw_data.get("desc", ""),
            "post_type": "video",
            "published_at": raw_data.get("createTime"),
            "likes": raw_data.get("diggCount", 0),
            "comments": raw_data.get("commentCount", 0),
            "shares": raw_data.get("shareCount", 0),
            "views": raw_data.get("playCount", 0),
            "raw_data": raw_data,
        }

    def update_profile_stats(self, handle: str) -> dict[str, int]:
        logger.info("TikTokScraper.update_profile_stats for @%s", handle)
        return {"followers_count": 0, "following_count": 0, "posts_count": 0}
