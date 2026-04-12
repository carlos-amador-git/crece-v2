from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.social import PostType, SocialPost, SocialProfile
from app.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

_MAX_VIDEOS = 30  # Videos per scrape run.
_YT_DLP_TIMEOUT = 120  # Seconds before yt-dlp subprocess is killed.
_TIKTOKAPI_TIMEOUT = 60  # Seconds for TikTokApi async operations.


def _yt_dlp_path() -> str:
    """Resolve the yt-dlp binary co-located with the current Python interpreter."""
    return os.path.join(os.path.dirname(sys.executable), "yt-dlp")


def _safe_int(value: Any) -> int:
    """Coerce a value to int, returning 0 on failure."""
    if value is None:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _run_yt_dlp(args: list[str], timeout: int = _YT_DLP_TIMEOUT) -> str | None:
    """Run yt-dlp as a subprocess and return stdout, or None on failure."""
    cmd = [_yt_dlp_path(), *args]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip()
            if stderr:
                logger.warning("yt-dlp stderr: %s", stderr[:500])
            return None
        return result.stdout
    except FileNotFoundError:
        logger.error("yt-dlp binary not found at %s", _yt_dlp_path())
        return None
    except subprocess.TimeoutExpired:
        logger.error("yt-dlp timed out after %ds", timeout)
        return None
    except Exception as exc:
        logger.error("yt-dlp subprocess failed: %s", exc)
        return None


def _parse_yt_dlp_jsonl(output: str) -> list[dict[str, Any]]:
    """Parse newline-delimited JSON output from yt-dlp --dump-json."""
    results: list[dict[str, Any]] = []
    for line in output.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            results.append(json.loads(line))
        except json.JSONDecodeError as exc:
            logger.debug("Skipping malformed yt-dlp JSON line: %s", exc)
    return results


def _sanitise_raw(raw: dict[str, Any]) -> dict[str, Any]:
    """Strip non-serialisable or excessively large fields before storing as JSONB."""
    keep_keys = {
        "id", "title", "description", "uploader", "uploader_id", "uploader_url",
        "channel", "channel_id", "upload_date", "timestamp", "duration",
        "view_count", "like_count", "comment_count", "repost_count",
        "thumbnail", "webpage_url", "categories", "tags",
    }
    clean: dict[str, Any] = {}
    for k, v in raw.items():
        if k not in keep_keys:
            continue
        if isinstance(v, datetime):
            clean[k] = v.isoformat()
        elif isinstance(v, (str, int, float, bool, type(None))):
            clean[k] = v
        elif isinstance(v, (list, dict)):
            try:
                json.dumps(v)
                clean[k] = v
            except (TypeError, ValueError):
                clean[k] = str(v)
        else:
            clean[k] = str(v)
    return clean


class TikTokScraper(BaseScraper):
    """TikTok scraper using yt-dlp (primary) with TikTokApi fallback.

    Primary pipeline (no token required):
    yt-dlp fetches video metadata directly from TikTok user pages.
    Tested successfully with real handles (e.g. @rafasolanoperez).

    Fallback pipeline (requires ``settings.TIKTOK_MS_TOKEN``):
    Uses the unofficial TikTokApi library with Playwright.
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
    # Primary: yt-dlp
    # ------------------------------------------------------------------

    def _fetch_via_yt_dlp(
        self, handle: str, max_videos: int = _MAX_VIDEOS
    ) -> list[dict[str, Any]]:
        """Fetch TikTok video metadata using yt-dlp."""
        clean_handle = handle.lstrip("@")
        url = f"https://www.tiktok.com/@{clean_handle}"

        output = _run_yt_dlp([
            "--dump-json",
            "--no-download",
            "--no-warnings",
            "--playlist-items", f"1-{max_videos}",
            url,
        ])

        if not output:
            return []

        entries = _parse_yt_dlp_jsonl(output)
        logger.info(
            "yt-dlp fetched %d TikTok videos for @%s", len(entries), clean_handle
        )
        return entries

    # ------------------------------------------------------------------
    # Fallback: TikTokApi (Playwright-based)
    # ------------------------------------------------------------------

    def _fetch_via_tiktokapi(
        self, handle: str, max_videos: int = _MAX_VIDEOS
    ) -> list[dict[str, Any]]:
        """Fallback: fetch videos using the unofficial TikTokApi library."""
        import asyncio

        try:
            from TikTokApi import TikTokApi
        except ImportError:
            logger.warning("TikTokApi is not installed — fallback unavailable")
            return []

        ms_token = settings.TIKTOK_MS_TOKEN or None

        async def _fetch() -> list[dict[str, Any]]:
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
                    async for video in user.videos(count=max_videos):
                        videos.append(video.as_dict)
            except Exception as exc:
                logger.error("TikTokApi fetch failed for @%s: %s", handle, exc)
            return videos

        try:
            return asyncio.run(
                asyncio.wait_for(_fetch(), timeout=_TIKTOKAPI_TIMEOUT)
            )
        except TimeoutError:
            logger.error("TikTokApi timed out for @%s", handle)
            return []
        except RuntimeError:
            # Already running event loop — create a new one.
            try:
                loop = asyncio.new_event_loop()
                result = loop.run_until_complete(
                    asyncio.wait_for(_fetch(), timeout=_TIKTOKAPI_TIMEOUT)
                )
                loop.close()
                return result
            except Exception as exc:
                logger.error("TikTokApi fallback loop failed for @%s: %s", handle, exc)
                return []

    def _fetch_user_info_via_tiktokapi(self, handle: str) -> dict[str, Any]:
        """Fallback: fetch user profile metadata via TikTokApi."""
        import asyncio

        try:
            from TikTokApi import TikTokApi
        except ImportError:
            return {}

        ms_token = settings.TIKTOK_MS_TOKEN or None

        async def _fetch() -> dict[str, Any]:
            try:
                async with TikTokApi() as api:
                    await api.create_sessions(
                        ms_tokens=[ms_token] if ms_token else [],
                        num_sessions=1,
                        headless=True,
                        sleep_after=3,
                    )
                    user = api.user(handle)
                    return await user.info()
            except Exception as exc:
                logger.warning("TikTokApi user info failed for @%s: %s", handle, exc)
                return {}

        try:
            return asyncio.run(
                asyncio.wait_for(_fetch(), timeout=_TIKTOKAPI_TIMEOUT)
            )
        except Exception:
            return {}

    # ------------------------------------------------------------------
    # BaseScraper interface
    # ------------------------------------------------------------------

    def fetch_raw(self, handle: str, **kwargs: Any) -> list[dict[str, Any]]:
        """Fetch recent TikTok videos. Primary: yt-dlp. Fallback: TikTokApi."""
        handle = handle.lstrip("@")
        count = kwargs.get("count", _MAX_VIDEOS)

        # Primary: yt-dlp.
        raw = self._fetch_via_yt_dlp(handle, count)
        if raw:
            logger.info("Primary pipeline (yt-dlp) returned %d TikTok videos", len(raw))
            return raw

        # Fallback: TikTokApi.
        logger.info("yt-dlp returned nothing — falling back to TikTokApi")
        fallback_raw = self._fetch_via_tiktokapi(handle, count)
        if fallback_raw:
            logger.info("TikTokApi fallback returned %d videos", len(fallback_raw))
        return fallback_raw

    def parse(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Parse a video dict into SocialPost fields.

        Handles both yt-dlp format and TikTokApi format.
        """
        # Detect format: TikTokApi uses "stats" and "desc" keys.
        if "stats" in raw_data and "desc" in raw_data:
            return self._parse_tiktokapi_format(raw_data)
        return self._parse_ytdlp_format(raw_data)

    def _parse_ytdlp_format(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Parse yt-dlp --dump-json output for a TikTok video."""
        title = raw_data.get("title", "") or raw_data.get("description", "")
        content = title.strip()

        # yt-dlp provides "timestamp" (unix) or "upload_date" (YYYYMMDD).
        timestamp = raw_data.get("timestamp")
        upload_date_str = raw_data.get("upload_date", "")

        if timestamp is not None:
            try:
                published_at = datetime.fromtimestamp(int(timestamp), tz=UTC)
            except (TypeError, ValueError, OSError):
                published_at = datetime.now(UTC)
        elif upload_date_str and len(upload_date_str) == 8:
            try:
                published_at = datetime(
                    int(upload_date_str[:4]),
                    int(upload_date_str[4:6]),
                    int(upload_date_str[6:8]),
                    tzinfo=UTC,
                )
            except (ValueError, TypeError):
                published_at = datetime.now(UTC)
        else:
            published_at = datetime.now(UTC)

        # TikTok videos are typically short-form.
        duration = _safe_int(raw_data.get("duration", 0))
        post_type = PostType.REEL if 0 < duration < 180 else PostType.VIDEO

        return {
            "platform_post_id": str(raw_data.get("id", "")),
            "content": content[:10_000],
            "post_type": post_type.value,
            "published_at": published_at,
            "likes": _safe_int(raw_data.get("like_count", 0)),
            "comments": _safe_int(raw_data.get("comment_count", 0)),
            "shares": _safe_int(raw_data.get("repost_count", 0)),
            "views": _safe_int(raw_data.get("view_count", 0)),
            "raw_data": _sanitise_raw(raw_data),
        }

    def _parse_tiktokapi_format(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Parse TikTokApi video dict (fallback format)."""
        stats = raw_data.get("stats", {})
        video_meta = raw_data.get("video", {})

        duration = _safe_int(video_meta.get("duration", 0))
        music = raw_data.get("music")
        post_type = (
            PostType.REEL if (duration > 0 and duration < 60 and music) else PostType.VIDEO
        )

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
        """Fetch TikTok user profile statistics.

        Primary: extract from yt-dlp metadata of the first video (channel info).
        Fallback: TikTokApi user info endpoint.
        """
        handle = handle.lstrip("@")
        empty = {"followers_count": 0, "following_count": 0, "posts_count": 0}

        # Primary: yt-dlp -- fetch just 1 video to get channel metadata.
        output = _run_yt_dlp([
            "--dump-json",
            "--no-download",
            "--no-warnings",
            "--playlist-items", "1",
            f"https://www.tiktok.com/@{handle}",
        ], timeout=30)

        if output:
            entries = _parse_yt_dlp_jsonl(output)
            if entries:
                entry = entries[0]
                # yt-dlp sometimes includes channel_follower_count for TikTok.
                followers = _safe_int(entry.get("channel_follower_count", 0))
                if followers > 0:
                    return {
                        "followers_count": followers,
                        "following_count": 0,
                        "posts_count": 0,
                    }

        # Fallback: TikTokApi.
        user_data = self._fetch_user_info_via_tiktokapi(handle)
        if not user_data:
            return empty

        stats = (
            user_data.get("userInfo", {}).get("stats", {})
            or user_data.get("stats", {})
        )

        return {
            "followers_count": _safe_int(stats.get("followerCount", 0)),
            "following_count": _safe_int(stats.get("followingCount", 0)),
            "posts_count": _safe_int(stats.get("videoCount", 0)),
        }
