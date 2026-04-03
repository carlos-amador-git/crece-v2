"""Twitter/X scraper using twscrape for authenticated scraping
and httpx as a degraded-mode fallback for public profile metadata.

Design decisions:
- twscrape is async; we wrap calls with asyncio.run() because Celery
  workers execute tasks synchronously.
- Account pool lives in a local SQLite DB managed by twscrape.  If no
  accounts are configured the scraper falls back to httpx syndication
  endpoint (limited, no auth needed, may break without notice).
- All network operations use exponential backoff with jitter.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import create_engine, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.social import PostType, SocialPost, SocialProfile
from app.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_MAX_TWEETS_PER_SCRAPE = 100
_BACKOFF_BASE = 2.0
_BACKOFF_MAX = 300  # 5 minutes ceiling
_MAX_RETRIES = 4
_HTTPX_TIMEOUT = 30.0

# Twitter syndication API (public, no auth, limited)
_SYNDICATION_TIMELINE_URL = "https://syndication.twitter.com/srv/timeline-profile/screen-name/{handle}"
_SYNDICATION_PROFILE_URL = "https://api.twitter.com/1.1/users/show.json"


def _get_sync_session() -> Session:
    """Create a synchronous SQLAlchemy session for Celery worker context."""
    engine = create_engine(
        settings.DATABASE_URL_SYNC,
        pool_size=5,
        max_overflow=2,
        pool_pre_ping=True,
    )
    return Session(bind=engine, expire_on_commit=False)


def _sleep_with_jitter(attempt: int) -> None:
    """Exponential backoff with full jitter (AWS-style)."""
    ceiling = min(_BACKOFF_BASE ** attempt, _BACKOFF_MAX)
    sleep_time = random.uniform(0, ceiling)  # noqa: S311
    logger.debug("Backoff attempt %d — sleeping %.1fs", attempt, sleep_time)
    time.sleep(sleep_time)


class TwitterScraper(BaseScraper):
    """Twitter/X scraper.

    Primary backend: twscrape (async, requires account pool).
    Fallback: httpx against syndication endpoints (degraded, public only).
    """

    platform = "twitter"

    def __init__(self) -> None:
        self._twscrape_api: Any | None = None
        self._twscrape_available: bool | None = None

    # ------------------------------------------------------------------
    # twscrape helpers
    # ------------------------------------------------------------------
    def _get_twscrape_api(self) -> Any:
        """Lazy-import and cache the twscrape API instance."""
        if self._twscrape_api is not None:
            return self._twscrape_api

        try:
            from twscrape import API  # type: ignore[import-untyped]

            self._twscrape_api = API()
            self._twscrape_available = True
            return self._twscrape_api
        except ImportError:
            logger.warning(
                "twscrape is not installed — Twitter scraper will use degraded httpx mode"
            )
            self._twscrape_available = False
            return None

    async def _fetch_tweets_twscrape(
        self, handle: str, limit: int = _MAX_TWEETS_PER_SCRAPE
    ) -> list[dict[str, Any]]:
        """Fetch tweets via twscrape (async)."""
        from twscrape import API  # type: ignore[import-untyped]

        api: API = self._get_twscrape_api()
        if api is None:
            return []

        # Resolve user ID from handle
        user = await api.user_by_login(handle)
        if user is None:
            logger.warning("twscrape could not resolve user @%s", handle)
            return []

        tweets: list[dict[str, Any]] = []
        async for tweet in api.user_tweets(user.id, limit=limit):
            tweets.append(tweet.dict())

        logger.info(
            "twscrape fetched %d tweets for @%s (user_id=%d)",
            len(tweets),
            handle,
            user.id,
        )
        return tweets

    async def _fetch_profile_twscrape(self, handle: str) -> dict[str, Any] | None:
        """Fetch profile stats via twscrape."""
        api = self._get_twscrape_api()
        if api is None:
            return None

        user = await api.user_by_login(handle)
        if user is None:
            return None

        user_dict = user.dict()
        return {
            "followers_count": user_dict.get("followers_count", 0),
            "following_count": user_dict.get("friends_count", 0),
            "posts_count": user_dict.get("statuses_count", 0),
            "raw": user_dict,
        }

    # ------------------------------------------------------------------
    # httpx fallback helpers
    # ------------------------------------------------------------------
    def _fetch_tweets_httpx(self, handle: str) -> list[dict[str, Any]]:
        """Degraded-mode: fetch public timeline via syndication endpoint.

        This endpoint returns an HTML page with embedded tweet data.
        It is fragile and may stop working; it exists only as a fallback
        when twscrape accounts are not configured.
        """
        url = _SYNDICATION_TIMELINE_URL.format(handle=handle)
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml",
        }

        for attempt in range(_MAX_RETRIES):
            try:
                with httpx.Client(timeout=_HTTPX_TIMEOUT, follow_redirects=True) as client:
                    resp = client.get(url, headers=headers)

                if resp.status_code == 429:
                    logger.warning("Rate limited on syndication endpoint (attempt %d)", attempt)
                    _sleep_with_jitter(attempt + 2)
                    continue

                if resp.status_code != 200:
                    logger.warning(
                        "Syndication returned HTTP %d for @%s",
                        resp.status_code,
                        handle,
                    )
                    return []

                # The syndication page embeds JSON inside a <script> tag.
                # Attempt to extract it; this is inherently brittle.
                return self._parse_syndication_html(resp.text, handle)

            except httpx.TimeoutException:
                logger.warning("Timeout fetching syndication for @%s (attempt %d)", handle, attempt)
                _sleep_with_jitter(attempt)
            except httpx.HTTPError as exc:
                logger.warning(
                    "HTTP error fetching syndication for @%s: %s (attempt %d)",
                    handle,
                    exc,
                    attempt,
                )
                _sleep_with_jitter(attempt)

        logger.error("All retries exhausted fetching syndication for @%s", handle)
        return []

    @staticmethod
    def _parse_syndication_html(html: str, handle: str) -> list[dict[str, Any]]:
        """Best-effort extraction of tweet data from syndication HTML.

        Returns a list of partial tweet dicts.  Fields may be incomplete
        compared to the twscrape path.
        """
        import json
        import re

        tweets: list[dict[str, Any]] = []

        # Look for JSON-LD or embedded __NEXT_DATA__ style payloads
        patterns = [
            r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>',
            r'"tweet_results":\s*(\{.*?\})\s*[,}]',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, html, re.DOTALL)
            for match in matches:
                try:
                    data = json.loads(match)
                    # Navigate common Twitter JSON structures
                    if isinstance(data, dict):
                        # Try to find tweet objects in nested structure
                        _extract_tweets_from_json(data, tweets)
                except (json.JSONDecodeError, TypeError):
                    continue

        if not tweets:
            # Simpler fallback: extract any data-tweet-id attributes
            tweet_ids = re.findall(r'data-tweet-id=["\'](\d+)["\']', html)
            texts = re.findall(
                r'<p[^>]*class="[^"]*tweet-text[^"]*"[^>]*>(.*?)</p>',
                html,
                re.DOTALL,
            )
            for i, tid in enumerate(tweet_ids):
                text = _strip_html_tags(texts[i]) if i < len(texts) else ""
                tweets.append(
                    {
                        "id_str": tid,
                        "full_text": text,
                        "created_at": None,
                        "favorite_count": 0,
                        "reply_count": 0,
                        "retweet_count": 0,
                        "view_count": 0,
                        "media": [],
                        "_source": "syndication_html",
                    }
                )

        logger.info(
            "Syndication HTML extraction found %d tweets for @%s",
            len(tweets),
            handle,
        )
        return tweets

    # ------------------------------------------------------------------
    # BaseScraper interface
    # ------------------------------------------------------------------
    def fetch_raw(self, handle: str, **kwargs: Any) -> list[dict[str, Any]]:
        """Fetch tweets — tries twscrape first, falls back to httpx."""
        limit = kwargs.get("limit", _MAX_TWEETS_PER_SCRAPE)
        handle = handle.lstrip("@").strip()

        if not handle:
            logger.error("Empty handle provided to fetch_raw")
            return []

        # Attempt twscrape (async)
        self._get_twscrape_api()
        if self._twscrape_available:
            for attempt in range(_MAX_RETRIES):
                try:
                    tweets = asyncio.run(self._fetch_tweets_twscrape(handle, limit=limit))
                    if tweets:
                        return tweets
                    # Empty result is not necessarily an error (new account, protected, etc.)
                    logger.info("twscrape returned 0 tweets for @%s", handle)
                    return []
                except Exception as exc:
                    logger.warning(
                        "twscrape attempt %d failed for @%s: %s",
                        attempt,
                        handle,
                        exc,
                    )
                    _sleep_with_jitter(attempt)

            logger.warning("twscrape exhausted retries for @%s — falling back to httpx", handle)

        # Fallback: httpx syndication
        logger.info("Using httpx fallback for @%s", handle)
        return self._fetch_tweets_httpx(handle)

    def parse(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Parse a single raw tweet into normalized SocialPost fields.

        Handles both twscrape dict format and syndication fallback format.
        """
        # twscrape uses snake_case fields matching Twitter API v2
        # Syndication fallback uses the legacy field names

        # Resolve post ID
        platform_post_id = str(
            raw_data.get("id_str")
            or raw_data.get("id")
            or raw_data.get("rest_id")
            or ""
        )

        # Resolve content
        content = (
            raw_data.get("rawContent")
            or raw_data.get("full_text")
            or raw_data.get("text")
            or ""
        )

        # Resolve published_at
        published_at = self._parse_tweet_date(raw_data)

        # Determine post type from media attachments
        post_type = self._determine_post_type(raw_data)

        # Metrics — twscrape nests under different keys depending on version
        likes = (
            raw_data.get("likeCount")
            or raw_data.get("favorite_count")
            or 0
        )
        comments = (
            raw_data.get("replyCount")
            or raw_data.get("reply_count")
            or 0
        )
        shares = (
            raw_data.get("retweetCount")
            or raw_data.get("retweet_count")
            or 0
        )
        views = (
            raw_data.get("viewCount")
            or raw_data.get("view_count")
            or 0
        )

        return {
            "platform_post_id": platform_post_id,
            "content": content,
            "post_type": post_type,
            "published_at": published_at,
            "likes": int(likes) if likes else 0,
            "comments": int(comments) if comments else 0,
            "shares": int(shares) if shares else 0,
            "views": int(views) if views else 0,
            "raw_data": raw_data,
        }

    def update_profile_stats(self, handle: str) -> dict[str, int]:
        """Fetch current profile statistics for a Twitter handle."""
        handle = handle.lstrip("@").strip()
        if not handle:
            return {"followers_count": 0, "following_count": 0, "posts_count": 0}

        # Try twscrape
        self._get_twscrape_api()
        if self._twscrape_available:
            for attempt in range(_MAX_RETRIES):
                try:
                    result = asyncio.run(self._fetch_profile_twscrape(handle))
                    if result is not None:
                        return {
                            "followers_count": result["followers_count"],
                            "following_count": result["following_count"],
                            "posts_count": result["posts_count"],
                        }
                except Exception as exc:
                    logger.warning(
                        "twscrape profile stats attempt %d for @%s: %s",
                        attempt,
                        handle,
                        exc,
                    )
                    _sleep_with_jitter(attempt)

        # Fallback: try public JSON endpoint (may require bearer token)
        return self._fetch_profile_stats_httpx(handle)

    def scrape(self, profile_id: int) -> dict[str, Any]:
        """Full scrape pipeline for a Twitter profile.

        1. Load profile from DB
        2. Fetch raw tweets
        3. Parse each tweet
        4. Deduplicate by platform_post_id
        5. Store new posts
        6. Update profile stats
        """
        errors: list[str] = []
        new_posts_count = 0
        updated_profile = False

        session = _get_sync_session()
        try:
            # 1. Load profile
            profile = session.get(SocialProfile, profile_id)
            if profile is None:
                msg = f"SocialProfile id={profile_id} not found"
                logger.error(msg)
                return {"new_posts": 0, "updated_profile": False, "errors": [msg]}

            handle = profile.handle.lstrip("@").strip()
            logger.info(
                "Starting Twitter scrape for @%s (profile_id=%d)",
                handle,
                profile_id,
            )

            # 2. Fetch raw tweets
            try:
                raw_tweets = self.fetch_raw(handle)
            except Exception as exc:
                msg = f"fetch_raw failed for @{handle}: {exc}"
                logger.error(msg)
                errors.append(msg)
                raw_tweets = []

            # 3 & 4. Parse and deduplicate
            if raw_tweets:
                # Get existing platform_post_ids to avoid duplicate DB lookups
                existing_ids_query = (
                    select(SocialPost.platform_post_id)
                    .where(SocialPost.profile_id == profile_id)
                )
                existing_ids: set[str] = {
                    row[0] for row in session.execute(existing_ids_query).all()
                }

                for raw_tweet in raw_tweets:
                    try:
                        parsed = self.parse(raw_tweet)

                        if not parsed["platform_post_id"]:
                            continue

                        if parsed["platform_post_id"] in existing_ids:
                            continue

                        # 5. Store new post via upsert (safety net for race conditions)
                        stmt = (
                            pg_insert(SocialPost)
                            .values(
                                profile_id=profile_id,
                                platform_post_id=parsed["platform_post_id"],
                                content=parsed["content"],
                                post_type=parsed["post_type"],
                                published_at=parsed["published_at"] or datetime.now(UTC),
                                likes=parsed["likes"],
                                comments=parsed["comments"],
                                shares=parsed["shares"],
                                views=parsed["views"],
                                raw_data=parsed["raw_data"],
                                scraped_at=datetime.now(UTC),
                            )
                            .on_conflict_do_nothing(
                                index_elements=["platform_post_id"]
                            )
                        )
                        result = session.execute(stmt)
                        if result.rowcount and result.rowcount > 0:
                            new_posts_count += 1
                            existing_ids.add(parsed["platform_post_id"])

                    except Exception as exc:
                        msg = f"Error parsing/storing tweet: {exc}"
                        logger.warning(msg)
                        errors.append(msg)

                session.commit()

            # 6. Update profile stats
            try:
                stats = self.update_profile_stats(handle)
                if any(v > 0 for v in stats.values()):
                    profile.followers_count = stats["followers_count"]
                    profile.following_count = stats["following_count"]
                    profile.posts_count = stats["posts_count"]
                    updated_profile = True

                profile.last_scraped_at = datetime.now(UTC)
                session.commit()
            except Exception as exc:
                msg = f"Failed to update profile stats for @{handle}: {exc}"
                logger.warning(msg)
                errors.append(msg)

            logger.info(
                "Twitter scrape complete for @%s: %d new posts, profile_updated=%s, errors=%d",
                handle,
                new_posts_count,
                updated_profile,
                len(errors),
            )

        except Exception as exc:
            session.rollback()
            msg = f"Scrape pipeline error for profile_id={profile_id}: {exc}"
            logger.error(msg)
            errors.append(msg)
        finally:
            session.close()

        return {
            "new_posts": new_posts_count,
            "updated_profile": updated_profile,
            "errors": errors,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_tweet_date(raw_data: dict[str, Any]) -> datetime | None:
        """Extract and parse the tweet creation timestamp."""
        # twscrape format: ISO string or datetime object
        date_val = raw_data.get("date") or raw_data.get("created_at")
        if date_val is None:
            return None

        if isinstance(date_val, datetime):
            return date_val.replace(tzinfo=UTC) if date_val.tzinfo is None else date_val

        if isinstance(date_val, str):
            # Twitter legacy format: "Thu Oct 26 14:30:00 +0000 2023"
            for fmt in (
                "%a %b %d %H:%M:%S %z %Y",
                "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S.%f%z",
                "%Y-%m-%d %H:%M:%S%z",
                "%Y-%m-%d %H:%M:%S",
            ):
                try:
                    dt = datetime.strptime(date_val, fmt)
                    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt
                except ValueError:
                    continue

            logger.debug("Could not parse tweet date: %s", date_val)

        return None

    @staticmethod
    def _determine_post_type(raw_data: dict[str, Any]) -> str:
        """Determine PostType from tweet media attachments."""
        # twscrape exposes media list
        media = raw_data.get("media") or {}
        if isinstance(media, dict):
            media_list = media.get("all", []) or media.get("photos", []) or media.get("videos", [])
        elif isinstance(media, list):
            media_list = media
        else:
            media_list = []

        if not media_list:
            return PostType.TEXT

        has_video = any(
            (isinstance(m, dict) and m.get("type") in ("video", "animated_gif"))
            or (isinstance(m, dict) and m.get("videoInfo"))
            for m in media_list
        )
        if has_video:
            return PostType.VIDEO

        if len(media_list) > 1:
            return PostType.CAROUSEL

        return PostType.IMAGE

    def _fetch_profile_stats_httpx(self, handle: str) -> dict[str, int]:
        """Fallback profile stats fetch via public web scraping.

        Very limited — parses the public twitter.com page HTML for follower counts.
        """
        default = {"followers_count": 0, "following_count": 0, "posts_count": 0}
        url = f"https://x.com/{handle}"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        }

        for attempt in range(_MAX_RETRIES):
            try:
                with httpx.Client(timeout=_HTTPX_TIMEOUT, follow_redirects=True) as client:
                    resp = client.get(url, headers=headers)

                if resp.status_code == 429:
                    _sleep_with_jitter(attempt + 2)
                    continue

                if resp.status_code != 200:
                    logger.warning("Profile page returned %d for @%s", resp.status_code, handle)
                    return default

                # Attempt to extract counts from meta tags or JSON-LD
                return self._parse_profile_page_stats(resp.text) or default

            except (httpx.TimeoutException, httpx.HTTPError) as exc:
                logger.warning(
                    "httpx profile stats attempt %d for @%s: %s",
                    attempt,
                    handle,
                    exc,
                )
                _sleep_with_jitter(attempt)

        return default

    @staticmethod
    def _parse_profile_page_stats(html: str) -> dict[str, int] | None:
        """Best-effort extraction of follower/following counts from profile HTML."""
        import json
        import re

        # Look for __NEXT_DATA__ or similar JSON blob
        match = re.search(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                # Navigate to user stats (structure varies)
                user = _deep_find_key(data, "user_results") or _deep_find_key(data, "user")
                if user and isinstance(user, dict):
                    legacy = user.get("legacy") or user
                    return {
                        "followers_count": legacy.get("followers_count", 0),
                        "following_count": legacy.get("friends_count", 0),
                        "posts_count": legacy.get("statuses_count", 0),
                    }
            except (json.JSONDecodeError, TypeError):
                pass

        # Try meta description: "X (@handle). Y Followers, Z Following"
        meta_match = re.search(
            r'(\d[\d,.]*[KMkm]?)\s*Followers.*?(\d[\d,.]*[KMkm]?)\s*Following',
            html,
        )
        if meta_match:
            return {
                "followers_count": _parse_count_str(meta_match.group(1)),
                "following_count": _parse_count_str(meta_match.group(2)),
                "posts_count": 0,
            }

        return None


# ---------------------------------------------------------------------------
# Module-level utility functions
# ---------------------------------------------------------------------------
def _strip_html_tags(text: str) -> str:
    """Remove HTML tags from a string."""
    import re

    return re.sub(r"<[^>]+>", "", text).strip()


def _extract_tweets_from_json(data: Any, results: list[dict[str, Any]], depth: int = 0) -> None:
    """Recursively search a nested dict/list for tweet-like objects."""
    if depth > 15:
        return

    if isinstance(data, dict):
        # Check if this looks like a tweet object
        if "id_str" in data and ("full_text" in data or "text" in data):
            results.append(data)
            return

        # twscrape-style: check for "rawContent"
        if "id" in data and "rawContent" in data:
            results.append(data)
            return

        for value in data.values():
            _extract_tweets_from_json(value, results, depth + 1)

    elif isinstance(data, list):
        for item in data:
            _extract_tweets_from_json(item, results, depth + 1)


def _deep_find_key(data: Any, key: str, depth: int = 0) -> Any:
    """Find the first value for *key* anywhere in a nested structure."""
    if depth > 20:
        return None

    if isinstance(data, dict):
        if key in data:
            return data[key]
        for v in data.values():
            result = _deep_find_key(v, key, depth + 1)
            if result is not None:
                return result

    elif isinstance(data, list):
        for item in data:
            result = _deep_find_key(item, key, depth + 1)
            if result is not None:
                return result

    return None


def _parse_count_str(s: str) -> int:
    """Parse human-readable count strings like '3.1K' or '1,234'."""
    s = s.strip().replace(",", "")
    multiplier = 1

    if s.endswith(("K", "k")):
        multiplier = 1_000
        s = s[:-1]
    elif s.endswith(("M", "m")):
        multiplier = 1_000_000
        s = s[:-1]

    try:
        return int(float(s) * multiplier)
    except ValueError:
        return 0
