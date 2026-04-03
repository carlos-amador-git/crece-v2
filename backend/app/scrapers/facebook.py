from __future__ import annotations

import logging
from typing import Any

from app.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class FacebookScraper(BaseScraper):
    """Facebook scraper for public pages.

    Uses facebook-scraper library or Graph API for page access tokens.
    """

    platform = "facebook"

    def scrape(self, profile_id: int) -> dict[str, Any]:
        logger.info("FacebookScraper.scrape called for profile_id=%d", profile_id)
        return {"new_posts": 0, "updated_profile": False, "errors": []}

    def fetch_raw(self, handle: str, **kwargs: Any) -> list[dict[str, Any]]:
        logger.info("FacebookScraper.fetch_raw for %s", handle)
        return []

    def parse(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        post_type = "text"
        if raw_data.get("images"):
            post_type = "image"
        if raw_data.get("video"):
            post_type = "video"

        return {
            "platform_post_id": raw_data.get("post_id", ""),
            "content": raw_data.get("text", ""),
            "post_type": post_type,
            "published_at": raw_data.get("time"),
            "likes": raw_data.get("likes", 0),
            "comments": raw_data.get("comments", 0),
            "shares": raw_data.get("shares", 0),
            "views": 0,
            "raw_data": raw_data,
        }

    def update_profile_stats(self, handle: str) -> dict[str, int]:
        logger.info("FacebookScraper.update_profile_stats for %s", handle)
        return {"followers_count": 0, "following_count": 0, "posts_count": 0}
