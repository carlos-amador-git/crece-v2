from __future__ import annotations

import logging
from typing import Any

from app.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class InstagramScraper(BaseScraper):
    """Instagram scraper using instaloader pattern.

    Requires session cookies or login credentials.
    See: https://instaloader.github.io/
    """

    platform = "instagram"

    def scrape(self, profile_id: int) -> dict[str, Any]:
        logger.info("InstagramScraper.scrape called for profile_id=%d", profile_id)
        return {"new_posts": 0, "updated_profile": False, "errors": []}

    def fetch_raw(self, handle: str, **kwargs: Any) -> list[dict[str, Any]]:
        """Fetch posts using instaloader.

        Example implementation:
            import instaloader
            L = instaloader.Instaloader()
            profile = instaloader.Profile.from_username(L.context, handle)
            posts = [post for post in profile.get_posts()]
            return [serialize_post(p) for p in posts[:50]]
        """
        logger.info("InstagramScraper.fetch_raw for @%s", handle)
        return []

    def parse(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Parse a raw Instagram post into normalized SocialPost fields."""
        # Determine post type
        post_type = "image"
        if raw_data.get("is_video"):
            post_type = "video"
        if raw_data.get("typename") == "GraphSidecar":
            post_type = "carousel"

        return {
            "platform_post_id": raw_data.get("shortcode", ""),
            "content": raw_data.get("caption", ""),
            "post_type": post_type,
            "published_at": raw_data.get("date_utc"),
            "likes": raw_data.get("likes", 0),
            "comments": raw_data.get("comments", 0),
            "shares": 0,
            "views": raw_data.get("video_view_count", 0),
            "raw_data": raw_data,
        }

    def update_profile_stats(self, handle: str) -> dict[str, int]:
        logger.info("InstagramScraper.update_profile_stats for @%s", handle)
        return {"followers_count": 0, "following_count": 0, "posts_count": 0}
