from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.social import PostType, SocialPost, SocialProfile
from app.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

# How many recent videos to fetch per scrape run.
_MAX_VIDEOS = 30
# Timeout for the entire TikTokApi session (seconds).
_ASYNC_TIMEOUT = 60


class TikTokScraper(BaseScraper):
    """TikTok scraper using the unofficial *TikTokApi* library.

    TikTokApi uses Playwright internally for browser-based session handling.
    Because Celery tasks run in a synchronous context, the async calls are
    executed via ``asyncio.run()``.

    The scraper degrades gracefully when:
    * TikTokApi is not installed.
    * No ``ms_token`` is configured (``settings.TIKTOK_MS_TOKEN``).
    * TikTok blocks or rate-limits the request.
    """

    platform = "tiktok"

    def __init__(self) -> None:
        self._engine = create_engine(
            settings.DATABASE_URL_SYNC,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=2,
        )

    # ------------------------------------------------------------------
    # Internal async helpers
    # ------------------------------------------------------------------

    @staticmethod
    async def _fetch_videos(handle: str, count: int) -> list[dict[str, Any]]:
        """Async coroutine that drives TikTokApi to fetch user videos."""
        try:
            from TikTokApi import TikTokApi
        except ImportError:
            logger.error(
                "TikTokApi is not installed. "
                "Install with: pip install TikTokApi"
            )
            return []

        ms_token = settings.TIKTOK_MS_TOKEN or None
        videos: list[dict[str, Any]] = []

        try:
            async with TikTokApi() as api:
                await api.create_sessions(
                    ms_tokens=[ms_token] if ms_token else [],
                    num_sessions=1,
                    headless=True,
                    sleep_after=3,
                )

                user = api.user(handle)
                async for video in user.videos(count=count):
                    video_dict = video.as_dict
                    videos.append(video_dict)

        except Exception as exc:
            logger.error(
                "TikTokApi fetch failed for @%s: %s",
                handle,
                exc,
            )

        return videos

    @staticmethod
    async def _fetch_user_info(handle: str) -> dict[str, Any]:
        """Async coroutine that fetches user profile metadata."""
        try:
            from TikTokApi import TikTokApi
        except ImportError:
            return {}

        ms_token = settings.TIKTOK_MS_TOKEN or None

        try:
            async with TikTokApi() as api:
                await api.create_sessions(
                    ms_tokens=[ms_token] if ms_token else [],
                    num_sessions=1,
                    headless=True,
                    sleep_after=3,
                )

                user = api.user(handle)
                user_data = await user.info()
                return user_data

        except Exception as exc:
            logger.warning("TikTokApi user info failed for @%s: %s", handle, exc)
            return {}

    # ------------------------------------------------------------------
    # BaseScraper interface
    # ------------------------------------------------------------------

    def fetch_raw(self, handle: str, **kwargs: Any) -> list[dict[str, Any]]:
        """Fetch recent TikTok videos for a user.

        Runs the async TikTokApi call inside ``asyncio.run()`` since Celery
        workers operate in a synchronous context.
        """
        handle = handle.lstrip("@")
        count = kwargs.get("count", _MAX_VIDEOS)

        try:
            raw = asyncio.run(
                asyncio.wait_for(
                    self._fetch_videos(handle, count),
                    timeout=_ASYNC_TIMEOUT,
                )
            )
        except asyncio.TimeoutError:
            logger.error("TikTokApi timed out for @%s after %ds", handle, _ASYNC_TIMEOUT)
            raw = []
        except RuntimeError:
            # Already running event loop (e.g. Jupyter/tests) — use nest_asyncio
            # or fall back to creating a new loop explicitly.
            try:
                loop = asyncio.new_event_loop()
                raw = loop.run_until_complete(
                    asyncio.wait_for(
                        self._fetch_videos(handle, count),
                        timeout=_ASYNC_TIMEOUT,
                    )
                )
                loop.close()
            except Exception as exc:
                logger.error("TikTokApi fallback loop failed for @%s: %s", handle, exc)
                raw = []

        logger.info(
            "Fetched %d raw TikTok videos for @%s",
            len(raw),
            handle,
        )
        return raw

    def parse(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Parse a single TikTokApi video dict into SocialPost fields.

        Field mapping
        ~~~~~~~~~~~~~
        * ``id`` -> ``platform_post_id``
        * ``desc`` -> ``content``
        * ``stats.diggCount`` -> ``likes``
        * ``stats.commentCount`` -> ``comments``
        * ``stats.shareCount`` -> ``shares``
        * ``stats.playCount`` -> ``views``
        * ``createTime`` (unix epoch) -> ``published_at``
        * ``post_type`` is ``video`` or ``reel`` (< 60s with music = reel)
        """
        stats = raw_data.get("stats", {})
        video_meta = raw_data.get("video", {})

        # Determine if it is a short-form "reel" (TikTok-style).
        duration = _safe_int(video_meta.get("duration", 0))
        music = raw_data.get("music")
        post_type = PostType.REEL if (duration > 0 and duration < 60 and music) else PostType.VIDEO

        # Unix timestamp -> aware datetime.
        create_time = raw_data.get("createTime")
        if create_time is not None:
            try:
                published_at = datetime.fromtimestamp(int(create_time), tz=UTC)
            except (TypeError, ValueError, OSError):
                published_at = datetime.now(UTC)
        else:
            published_at = datetime.now(UTC)

        return {
            "platform_post_id": str(raw_data.get("id", "")),
            "content": (raw_data.get("desc") or "")[:10_000],
            "post_type": post_type.value,
            "published_at": published_at,
            "likes": _safe_int(stats.get("diggCount", 0)),
            "comments": _safe_int(stats.get("commentCount", 0)),
            "shares": _safe_int(stats.get("shareCount", 0)),
            "views": _safe_int(stats.get("playCount", 0)),
            "raw_data": _sanitise_raw(raw_data),
        }

    def scrape(self, profile_id: int) -> dict[str, Any]:
        """Full scrape pipeline: fetch -> parse -> dedup -> store."""
        errors: list[str] = []
        new_posts = 0
        updated_profile = False

        with Session(self._engine) as session:
            profile = session.get(SocialProfile, profile_id)
            if profile is None:
                return {
                    "new_posts": 0,
                    "updated_profile": False,
                    "errors": [f"Profile {profile_id} not found"],
                }

            handle = profile.handle.lstrip("@")
            logger.info(
                "Starting TikTok scrape for profile_id=%d handle=@%s",
                profile_id,
                handle,
            )

            # 1. Fetch.
            raw_videos = self.fetch_raw(handle)
            if not raw_videos:
                logger.warning("No raw videos returned for @%s", handle)

            # 2. Parse and dedup.
            for raw in raw_videos:
                try:
                    parsed = self.parse(raw)
                except Exception as exc:
                    errors.append(f"Parse error: {exc}")
                    continue

                platform_post_id = parsed["platform_post_id"]
                if not platform_post_id:
                    continue

                existing = session.execute(
                    select(SocialPost).where(
                        SocialPost.platform_post_id == platform_post_id
                    )
                ).scalar_one_or_none()

                if existing is not None:
                    existing.likes = parsed["likes"]
                    existing.comments = parsed["comments"]
                    existing.shares = parsed["shares"]
                    existing.views = parsed["views"]
                    continue

                post = SocialPost(
                    profile_id=profile_id,
                    platform_post_id=platform_post_id,
                    content=parsed["content"],
                    post_type=parsed["post_type"],
                    published_at=parsed["published_at"],
                    likes=parsed["likes"],
                    comments=parsed["comments"],
                    shares=parsed["shares"],
                    views=parsed["views"],
                    raw_data=parsed["raw_data"],
                    scraped_at=datetime.now(UTC),
                )
                session.add(post)
                new_posts += 1

            # 3. Update profile stats.
            try:
                stats = self.update_profile_stats(handle)
                if stats.get("followers_count", 0) > 0:
                    profile.followers_count = stats["followers_count"]
                    updated_profile = True
                if stats.get("following_count", 0) > 0:
                    profile.following_count = stats["following_count"]
                    updated_profile = True
                if stats.get("posts_count", 0) > 0:
                    profile.posts_count = stats["posts_count"]
                    updated_profile = True
            except Exception as exc:
                errors.append(f"Profile stats error: {exc}")

            profile.last_scraped_at = datetime.now(UTC)
            session.commit()

        logger.info(
            "TikTok scrape complete: profile_id=%d new_posts=%d errors=%d",
            profile_id,
            new_posts,
            len(errors),
        )
        return {
            "new_posts": new_posts,
            "updated_profile": updated_profile,
            "errors": errors,
        }

    def update_profile_stats(self, handle: str) -> dict[str, int]:
        """Fetch TikTok user profile statistics (followers, following, videos)."""
        handle = handle.lstrip("@")

        try:
            user_data = asyncio.run(
                asyncio.wait_for(
                    self._fetch_user_info(handle),
                    timeout=_ASYNC_TIMEOUT,
                )
            )
        except Exception as exc:
            logger.warning("Could not fetch TikTok stats for @%s: %s", handle, exc)
            return {"followers_count": 0, "following_count": 0, "posts_count": 0}

        if not user_data:
            return {"followers_count": 0, "following_count": 0, "posts_count": 0}

        # TikTokApi nests stats under "userInfo" -> "stats".
        stats = (
            user_data.get("userInfo", {}).get("stats", {})
            or user_data.get("stats", {})
        )

        return {
            "followers_count": _safe_int(stats.get("followerCount", 0)),
            "following_count": _safe_int(stats.get("followingCount", 0)),
            "posts_count": _safe_int(stats.get("videoCount", 0)),
        }


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _safe_int(value: Any) -> int:
    """Coerce a value to int, returning 0 on failure."""
    if value is None:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _sanitise_raw(raw: dict[str, Any]) -> dict[str, Any]:
    """Strip non-serialisable objects before storing as JSONB.

    TikTokApi ``as_dict`` usually produces clean JSON, but edge cases
    with nested objects or datetime values can occur.
    """
    import json

    try:
        json.dumps(raw)
        return raw
    except (TypeError, ValueError):
        pass

    clean: dict[str, Any] = {}
    for key, value in raw.items():
        if isinstance(value, datetime):
            clean[key] = value.isoformat()
        elif isinstance(value, (str, int, float, bool, type(None))):
            clean[key] = value
        elif isinstance(value, (list, dict)):
            try:
                json.dumps(value)
                clean[key] = value
            except (TypeError, ValueError):
                clean[key] = str(value)
        else:
            clean[key] = str(value)
    return clean
