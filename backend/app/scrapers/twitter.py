"""Twitter/X scraper with three-tier fallback strategy.

Tier 1 (Primary): Scweet — uses X GraphQL API with auth_token cookie.
    Reliable as of 2026, requires browser cookie rotation every ~30 days.
Tier 2 (Fallback): twscrape — async scraper with account pool.
    Requires configured accounts in local SQLite DB.
Tier 3 (Last resort): httpx syndication endpoint — public, no auth, fragile.

Design decisions:
- Scweet is synchronous, perfect for Celery worker context.
- twscrape is async; we wrap calls with asyncio.run().
- All tiers share the same parse() logic that normalizes to SocialPost fields.
- auth_token comes from settings.TWITTER_AUTH_TOKEN (browser cookie from x.com).
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

# Twitter syndication API (public, no auth, limited — Tier 3)
_SYNDICATION_TIMELINE_URL = (
    "https://syndication.twitter.com/srv/timeline-profile/screen-name/{handle}"
)


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
    ceiling = min(_BACKOFF_BASE**attempt, _BACKOFF_MAX)
    sleep_time = random.uniform(0, ceiling)  # noqa: S311
    logger.debug("Backoff attempt %d — sleeping %.1fs", attempt, sleep_time)
    time.sleep(sleep_time)


class TwitterScraper(BaseScraper):
    """Twitter/X scraper with three-tier fallback.

    Tier 1: Scweet (GraphQL + auth_token cookie)
    Tier 2: twscrape (async, account pool)
    Tier 3: httpx syndication (degraded, public only)
    """

    platform = "twitter"

    def __init__(self) -> None:
        self._scweet_client: Any | None = None
        self._scweet_available: bool | None = None
        self._twscrape_api: Any | None = None
        self._twscrape_available: bool | None = None

    # ==================================================================
    # Tier 1: Scweet (primary)
    # ==================================================================
    def _get_scweet_client(self) -> Any | None:
        """Lazy-initialize Scweet client with auth_token from settings."""
        if self._scweet_available is False:
            return None
        if self._scweet_client is not None:
            return self._scweet_client

        auth_token = settings.TWITTER_AUTH_TOKEN
        if not auth_token:
            logger.info(
                "TWITTER_AUTH_TOKEN not configured — Scweet unavailable, "
                "will fall back to twscrape/httpx"
            )
            self._scweet_available = False
            return None

        try:
            from Scweet import Scweet  # type: ignore[import-untyped]

            self._scweet_client = Scweet(auth_token=auth_token)
            self._scweet_available = True
            logger.info("Scweet client initialized (Tier 1 active)")
            return self._scweet_client
        except ImportError:
            logger.warning(
                "Scweet library not installed — pip install Scweet. "
                "Falling back to twscrape/httpx."
            )
            self._scweet_available = False
            return None
        except Exception as exc:
            logger.warning("Scweet initialization failed: %s", exc)
            self._scweet_available = False
            return None

    def _fetch_tweets_scweet(
        self, handle: str, limit: int = _MAX_TWEETS_PER_SCRAPE
    ) -> list[dict[str, Any]]:
        """Fetch tweets via Scweet (synchronous, GraphQL API)."""
        client = self._get_scweet_client()
        if client is None:
            return []

        for attempt in range(_MAX_RETRIES):
            try:
                raw_tweets = client.get_profile_tweets([handle], limit=limit)
                if raw_tweets is None:
                    raw_tweets = []

                logger.info(
                    "Scweet fetched %d tweets for @%s",
                    len(raw_tweets),
                    handle,
                )
                # Tag source for parse() disambiguation
                for tweet in raw_tweets:
                    tweet["_source"] = "scweet"
                return raw_tweets

            except Exception as exc:
                logger.warning(
                    "Scweet attempt %d failed for @%s: %s",
                    attempt,
                    handle,
                    exc,
                )
                # On auth errors, mark Scweet as unavailable for this session
                exc_str = str(exc).lower()
                if "unauthorized" in exc_str or "401" in exc_str or "forbidden" in exc_str:
                    logger.error(
                        "Scweet auth_token appears expired for @%s — "
                        "rotate TWITTER_AUTH_TOKEN from browser cookies",
                        handle,
                    )
                    self._scweet_available = False
                    return []
                _sleep_with_jitter(attempt)

        logger.warning("Scweet exhausted retries for @%s", handle)
        return []

    def _fetch_profile_scweet(self, handle: str) -> dict[str, Any] | None:
        """Fetch profile info via Scweet.get_user_info()."""
        client = self._get_scweet_client()
        if client is None:
            return None

        for attempt in range(_MAX_RETRIES):
            try:
                # get_user_info returns a list with one dict
                info_list = client.get_user_info(handle)
                if not info_list:
                    return None

                info = info_list[0] if isinstance(info_list, list) else info_list
                return {
                    "followers_count": int(info.get("followers_count", 0) or 0),
                    "following_count": int(info.get("following_count", 0) or 0),
                    "posts_count": int(info.get("statuses_count", 0) or 0),
                    "raw": info,
                }

            except Exception as exc:
                logger.warning(
                    "Scweet profile info attempt %d for @%s: %s",
                    attempt,
                    handle,
                    exc,
                )
                exc_str = str(exc).lower()
                if "unauthorized" in exc_str or "401" in exc_str:
                    self._scweet_available = False
                    return None
                _sleep_with_jitter(attempt)

        return None

    # ==================================================================
    # Tier 2: twscrape (fallback)
    # ==================================================================
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
                "twscrape is not installed — Twitter scraper Tier 2 unavailable"
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

    # ==================================================================
    # Tier 3: httpx syndication (last resort)
    # ==================================================================
    def _fetch_tweets_httpx(self, handle: str) -> list[dict[str, Any]]:
        """Degraded-mode: fetch public timeline via syndication endpoint.

        This endpoint returns an HTML page with embedded tweet data.
        It is fragile and may stop working; it exists only as a last resort.
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
                with httpx.Client(
                    timeout=_HTTPX_TIMEOUT, follow_redirects=True
                ) as client:
                    resp = client.get(url, headers=headers)

                if resp.status_code == 429:
                    logger.warning(
                        "Rate limited on syndication endpoint (attempt %d)",
                        attempt,
                    )
                    _sleep_with_jitter(attempt + 2)
                    continue

                if resp.status_code != 200:
                    logger.warning(
                        "Syndication returned HTTP %d for @%s",
                        resp.status_code,
                        handle,
                    )
                    return []

                return self._parse_syndication_html(resp.text, handle)

            except httpx.TimeoutException:
                logger.warning(
                    "Timeout fetching syndication for @%s (attempt %d)",
                    handle,
                    attempt,
                )
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
        """Best-effort extraction of tweet data from syndication HTML."""
        import json
        import re

        tweets: list[dict[str, Any]] = []

        patterns = [
            r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>',
            r'"tweet_results":\s*(\{.*?\})\s*[,}]',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, html, re.DOTALL)
            for match in matches:
                try:
                    data = json.loads(match)
                    if isinstance(data, dict):
                        _extract_tweets_from_json(data, tweets)
                except (json.JSONDecodeError, TypeError):
                    continue

        if not tweets:
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

    def _fetch_profile_stats_httpx(self, handle: str) -> dict[str, int]:
        """Fallback profile stats via public web scraping (Tier 3)."""
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
                with httpx.Client(
                    timeout=_HTTPX_TIMEOUT, follow_redirects=True
                ) as client:
                    resp = client.get(url, headers=headers)

                if resp.status_code == 429:
                    _sleep_with_jitter(attempt + 2)
                    continue

                if resp.status_code != 200:
                    logger.warning(
                        "Profile page returned %d for @%s",
                        resp.status_code,
                        handle,
                    )
                    return default

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

        match = re.search(
            r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>',
            html,
            re.DOTALL,
        )
        if match:
            try:
                data = json.loads(match.group(1))
                user = _deep_find_key(data, "user_results") or _deep_find_key(
                    data, "user"
                )
                if user and isinstance(user, dict):
                    legacy = user.get("legacy") or user
                    return {
                        "followers_count": legacy.get("followers_count", 0),
                        "following_count": legacy.get("friends_count", 0),
                        "posts_count": legacy.get("statuses_count", 0),
                    }
            except (json.JSONDecodeError, TypeError):
                pass

        meta_match = re.search(
            r"(\d[\d,.]*[KMkm]?)\s*Followers.*?(\d[\d,.]*[KMkm]?)\s*Following",
            html,
        )
        if meta_match:
            return {
                "followers_count": _parse_count_str(meta_match.group(1)),
                "following_count": _parse_count_str(meta_match.group(2)),
                "posts_count": 0,
            }

        return None

    # ==================================================================
    # BaseScraper interface
    # ==================================================================
    def fetch_raw(self, handle: str, **kwargs: Any) -> list[dict[str, Any]]:
        """Fetch tweets — cascades through Scweet -> twscrape -> httpx."""
        limit = kwargs.get("limit", _MAX_TWEETS_PER_SCRAPE)
        handle = handle.lstrip("@").strip()

        if not handle:
            logger.error("Empty handle provided to fetch_raw")
            return []

        # ── Tier 1: Scweet ──────────────────────────────────
        if self._scweet_available is not False:
            tweets = self._fetch_tweets_scweet(handle, limit=limit)
            if tweets:
                return tweets
            # Empty result from Scweet with available client = account exists but
            # has no tweets. Only fall through if Scweet itself failed.
            if self._scweet_available:
                logger.info("Scweet returned 0 tweets for @%s (account may be empty)", handle)
                return []

        # ── Tier 2: twscrape ───────────────────────────────
        self._get_twscrape_api()
        if self._twscrape_available:
            logger.info("Falling back to twscrape (Tier 2) for @%s", handle)
            for attempt in range(_MAX_RETRIES):
                try:
                    tweets = asyncio.run(
                        self._fetch_tweets_twscrape(handle, limit=limit)
                    )
                    if tweets:
                        return tweets
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

            logger.warning(
                "twscrape exhausted retries for @%s — falling back to httpx",
                handle,
            )

        # ── Tier 3: httpx syndication ──────────────────────
        logger.info("Using httpx syndication fallback (Tier 3) for @%s", handle)
        return self._fetch_tweets_httpx(handle)

    def parse(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Parse a single raw tweet into normalized SocialPost fields.

        Handles three formats:
        - Scweet dict (tweet_id, text, likes, retweets, comments, timestamp, media)
        - twscrape dict (id, rawContent, likeCount, retweetCount, etc.)
        - syndication fallback (id_str, full_text, favorite_count, etc.)
        """
        source = raw_data.get("_source", "")

        # ── Resolve post ID ─────────────────────────────────
        if source == "scweet":
            platform_post_id = str(raw_data.get("tweet_id") or "")
        else:
            platform_post_id = str(
                raw_data.get("id_str")
                or raw_data.get("id")
                or raw_data.get("rest_id")
                or ""
            )

        # ── Resolve content ─────────────────────────────────
        if source == "scweet":
            # Scweet: 'text' is primary, 'embedded_text' may have quoted tweet
            content = raw_data.get("text") or ""
            embedded = raw_data.get("embedded_text")
            if embedded and embedded != content:
                content = f"{content}\n\n[QT] {embedded}"
        else:
            content = (
                raw_data.get("rawContent")
                or raw_data.get("full_text")
                or raw_data.get("text")
                or ""
            )

        # ── Resolve published_at ────────────────────────────
        published_at = self._parse_tweet_date(raw_data)

        # ── Determine post type ─────────────────────────────
        post_type = self._determine_post_type(raw_data)

        # ── Metrics ─────────────────────────────────────────
        if source == "scweet":
            likes = raw_data.get("likes", 0)
            comments = raw_data.get("comments", 0)
            shares = raw_data.get("retweets", 0)
            views = 0  # Scweet does not expose view counts
        else:
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
            "likes": _safe_int(likes),
            "comments": _safe_int(comments),
            "shares": _safe_int(shares),
            "views": _safe_int(views),
            "raw_data": raw_data,
        }

    def update_profile_stats(self, handle: str) -> dict[str, int]:
        """Fetch current profile statistics — cascades through all tiers."""
        handle = handle.lstrip("@").strip()
        if not handle:
            return {"followers_count": 0, "following_count": 0, "posts_count": 0}

        # ── Tier 1: Scweet ──────────────────────────────────
        if self._scweet_available is not False:
            result = self._fetch_profile_scweet(handle)
            if result is not None:
                return {
                    "followers_count": result["followers_count"],
                    "following_count": result["following_count"],
                    "posts_count": result["posts_count"],
                }

        # ── Tier 2: twscrape ───────────────────────────────
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

        # ── Tier 3: httpx ──────────────────────────────────
        return self._fetch_profile_stats_httpx(handle)

    def scrape(self, profile_id: int) -> dict[str, Any]:
        """Full scrape pipeline for a Twitter profile.

        1. Load profile from DB
        2. Fetch raw tweets (Scweet -> twscrape -> httpx)
        3. Parse each tweet
        4. Deduplicate by platform_post_id
        5. Store new posts via upsert
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
                existing_ids_query = select(SocialPost.platform_post_id).where(
                    SocialPost.profile_id == profile_id
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

                        # 5. Store via upsert
                        stmt = (
                            pg_insert(SocialPost)
                            .values(
                                profile_id=profile_id,
                                platform_post_id=parsed["platform_post_id"],
                                content=parsed["content"],
                                post_type=parsed["post_type"],
                                published_at=parsed["published_at"]
                                or datetime.now(UTC),
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

    # ==================================================================
    # Private helpers
    # ==================================================================
    @staticmethod
    def _parse_tweet_date(raw_data: dict[str, Any]) -> datetime | None:
        """Extract and parse the tweet creation timestamp."""
        # Scweet uses 'timestamp', twscrape uses 'date', legacy uses 'created_at'
        date_val = (
            raw_data.get("timestamp")
            or raw_data.get("date")
            or raw_data.get("created_at")
        )
        if date_val is None:
            return None

        if isinstance(date_val, datetime):
            return date_val.replace(tzinfo=UTC) if date_val.tzinfo is None else date_val

        if isinstance(date_val, (int, float)):
            # Unix timestamp (Scweet may return epoch seconds)
            try:
                return datetime.fromtimestamp(date_val, tz=UTC)
            except (ValueError, OSError):
                return None

        if isinstance(date_val, str):
            for fmt in (
                "%a %b %d %H:%M:%S %z %Y",  # Twitter legacy
                "%Y-%m-%dT%H:%M:%S%z",  # ISO 8601
                "%Y-%m-%dT%H:%M:%S.%f%z",  # ISO 8601 with microseconds
                "%Y-%m-%d %H:%M:%S%z",  # Common datetime
                "%Y-%m-%d %H:%M:%S",  # Naive datetime
                "%Y-%m-%dT%H:%M:%SZ",  # UTC with Z suffix
            ):
                try:
                    dt = datetime.strptime(date_val, fmt)
                    return (
                        dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt
                    )
                except ValueError:
                    continue

            logger.debug("Could not parse tweet date: %s", date_val)

        return None

    @staticmethod
    def _determine_post_type(raw_data: dict[str, Any]) -> str:
        """Determine PostType from tweet media attachments."""
        source = raw_data.get("_source", "")

        if source == "scweet":
            # Scweet media: dict with image_links (list of URLs)
            media = raw_data.get("media")
            if not media or not isinstance(media, dict):
                return PostType.TEXT

            image_links = media.get("image_links") or []
            if not image_links:
                return PostType.TEXT

            # Scweet does not distinguish video vs image in media dict
            # Video URLs typically contain /ext_tw_video/ or /amplify_video/
            has_video = any(
                "video" in str(url).lower() for url in image_links
            )
            if has_video:
                return PostType.VIDEO

            if len(image_links) > 1:
                return PostType.CAROUSEL

            return PostType.IMAGE

        # twscrape / syndication format
        media = raw_data.get("media") or {}
        if isinstance(media, dict):
            media_list = (
                media.get("all", [])
                or media.get("photos", [])
                or media.get("videos", [])
            )
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


# ---------------------------------------------------------------------------
# Module-level utility functions
# ---------------------------------------------------------------------------
def _safe_int(value: Any) -> int:
    """Safely convert a value to int, returning 0 on failure."""
    if value is None:
        return 0
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def _strip_html_tags(text: str) -> str:
    """Remove HTML tags from a string."""
    import re

    return re.sub(r"<[^>]+>", "", text).strip()


def _extract_tweets_from_json(
    data: Any, results: list[dict[str, Any]], depth: int = 0
) -> None:
    """Recursively search a nested dict/list for tweet-like objects."""
    if depth > 15:
        return

    if isinstance(data, dict):
        if "id_str" in data and ("full_text" in data or "text" in data):
            results.append(data)
            return

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
