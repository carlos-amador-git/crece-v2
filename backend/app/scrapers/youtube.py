from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.social import PostType, SocialPost, SocialProfile
from app.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

# YouTube Data API v3 quota costs:
#   channels.list   = 1 unit
#   playlistItems   = 1 unit
#   videos.list     = 1 unit per 50 IDs
#   search.list     = 100 units  (AVOID)
#
# Free tier daily quota: 10,000 units.
# Strategy: channels -> uploads playlist -> playlistItems -> videos.list
# Typical cost per scrape: 1 + 1 + ceil(N/50) units ~ 3 units for 50 videos.

_MAX_RESULTS = 50  # Videos per scrape run (max allowed by API per page).


class YouTubeScraper(BaseScraper):
    """YouTube scraper using the official YouTube Data API v3.

    Requires ``settings.YOUTUBE_API_KEY`` to be set.  When the key is
    absent the scraper degrades gracefully and returns empty results.

    Quota optimisation: uses ``playlistItems.list`` on the channel's
    uploads playlist instead of the expensive ``search.list`` endpoint,
    then batch-fetches statistics with ``videos.list`` (1 unit per 50 IDs).
    """

    platform = "youtube"

    def __init__(self) -> None:
        self._engine = create_engine(
            settings.DATABASE_URL_SYNC,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=2,
        )
        self._youtube_client: Any = None

    # ------------------------------------------------------------------
    # Client management
    # ------------------------------------------------------------------

    def _get_client(self) -> Any:
        """Build and cache the YouTube API client.

        Returns ``None`` when the API key is not configured or the
        google-api-python-client library is missing.
        """
        if self._youtube_client is not None:
            return self._youtube_client

        api_key = settings.YOUTUBE_API_KEY
        if not api_key:
            logger.warning(
                "YOUTUBE_API_KEY is not set — YouTube scraper running in degraded mode"
            )
            return None

        try:
            from googleapiclient.discovery import build

            self._youtube_client = build(
                "youtube",
                "v3",
                developerKey=api_key,
                cache_discovery=False,
            )
            return self._youtube_client
        except ImportError:
            logger.error(
                "google-api-python-client is not installed. "
                "Install with: pip install google-api-python-client"
            )
            return None
        except Exception as exc:
            logger.error("Failed to build YouTube API client: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_channel_id(self, handle: str) -> str | None:
        """Resolve a YouTube handle or custom URL to a channel ID.

        Tries ``forHandle`` first (for @-handles), then ``forUsername``
        as a fallback for legacy usernames, and finally treats the handle
        as a raw channel ID (UC...) if it already looks like one.
        """
        youtube = self._get_client()
        if youtube is None:
            return None

        # If already a channel ID, return directly.
        if handle.startswith("UC") and len(handle) == 24:
            return handle

        clean_handle = handle.lstrip("@")

        # Try forHandle (YouTube @handle).
        try:
            resp = (
                youtube.channels()
                .list(forHandle=clean_handle, part="id,contentDetails")
                .execute()
            )
            items = resp.get("items", [])
            if items:
                return items[0]["id"]
        except Exception as exc:
            logger.debug("forHandle lookup failed for %s: %s", clean_handle, exc)

        # Fallback: forUsername (legacy).
        try:
            resp = (
                youtube.channels()
                .list(forUsername=clean_handle, part="id,contentDetails")
                .execute()
            )
            items = resp.get("items", [])
            if items:
                return items[0]["id"]
        except Exception as exc:
            logger.debug("forUsername lookup failed for %s: %s", clean_handle, exc)

        logger.warning("Could not resolve channel ID for handle=%s", handle)
        return None

    def _get_uploads_playlist_id(self, channel_id: str) -> str | None:
        """Get the uploads playlist ID for a channel.

        The uploads playlist ID is the channel ID with the second character
        replaced: ``UC...`` -> ``UU...``.
        """
        # YouTube convention: uploads playlist = channel ID with UC -> UU.
        if channel_id.startswith("UC"):
            return "UU" + channel_id[2:]

        # Fallback: query the API.
        youtube = self._get_client()
        if youtube is None:
            return None

        try:
            resp = (
                youtube.channels()
                .list(id=channel_id, part="contentDetails")
                .execute()
            )
            items = resp.get("items", [])
            if items:
                return (
                    items[0]
                    .get("contentDetails", {})
                    .get("relatedPlaylists", {})
                    .get("uploads")
                )
        except Exception as exc:
            logger.error("Failed to get uploads playlist for %s: %s", channel_id, exc)

        return None

    def _fetch_playlist_video_ids(
        self,
        playlist_id: str,
        max_results: int = _MAX_RESULTS,
    ) -> list[str]:
        """Fetch video IDs from a playlist using playlistItems.list (1 unit)."""
        youtube = self._get_client()
        if youtube is None:
            return []

        video_ids: list[str] = []
        try:
            resp = (
                youtube.playlistItems()
                .list(
                    playlistId=playlist_id,
                    part="contentDetails",
                    maxResults=min(max_results, 50),
                )
                .execute()
            )
            for item in resp.get("items", []):
                vid = item.get("contentDetails", {}).get("videoId")
                if vid:
                    video_ids.append(vid)
        except Exception as exc:
            logger.error(
                "playlistItems.list failed for playlist %s: %s",
                playlist_id,
                exc,
            )

        return video_ids

    def _batch_fetch_video_details(
        self, video_ids: list[str]
    ) -> list[dict[str, Any]]:
        """Fetch full video details in batches of 50 (1 unit per batch)."""
        youtube = self._get_client()
        if youtube is None or not video_ids:
            return []

        all_videos: list[dict[str, Any]] = []

        # Process in chunks of 50 (API maximum).
        for i in range(0, len(video_ids), 50):
            chunk = video_ids[i : i + 50]
            try:
                resp = (
                    youtube.videos()
                    .list(
                        id=",".join(chunk),
                        part="snippet,statistics,contentDetails",
                    )
                    .execute()
                )
                all_videos.extend(resp.get("items", []))
            except Exception as exc:
                logger.error(
                    "videos.list failed for chunk starting at index %d: %s",
                    i,
                    exc,
                )

        return all_videos

    # ------------------------------------------------------------------
    # BaseScraper interface
    # ------------------------------------------------------------------

    def fetch_raw(self, handle: str, **kwargs: Any) -> list[dict[str, Any]]:
        """Fetch recent videos using the quota-efficient pipeline.

        Pipeline (total ~3 units for 50 videos):
        1. ``channels.list(forHandle=...)`` -> channel_id  (1 unit)
        2. Derive uploads playlist ID (0 units)
        3. ``playlistItems.list(...)`` -> video IDs       (1 unit)
        4. ``videos.list(id=...)`` -> full details         (1 unit per 50)
        """
        channel_id = self._resolve_channel_id(handle)
        if channel_id is None:
            logger.warning("Cannot fetch videos — channel ID not resolved for %s", handle)
            return []

        uploads_playlist = self._get_uploads_playlist_id(channel_id)
        if uploads_playlist is None:
            logger.warning("Cannot find uploads playlist for channel %s", channel_id)
            return []

        max_results = kwargs.get("max_results", _MAX_RESULTS)
        video_ids = self._fetch_playlist_video_ids(uploads_playlist, max_results)
        if not video_ids:
            logger.info("No video IDs found for channel %s", channel_id)
            return []

        videos = self._batch_fetch_video_details(video_ids)
        logger.info(
            "Fetched %d videos for handle=%s (channel=%s)",
            len(videos),
            handle,
            channel_id,
        )
        return videos

    def parse(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Parse a YouTube Data API video resource into SocialPost fields.

        Field mapping
        ~~~~~~~~~~~~~
        * ``id`` -> ``platform_post_id``
        * ``snippet.title`` + ``snippet.description`` -> ``content``
        * ``statistics.likeCount`` -> ``likes``
        * ``statistics.commentCount`` -> ``comments``
        * ``statistics.viewCount`` -> ``views``
        * ``snippet.publishedAt`` -> ``published_at`` (ISO 8601)
        * ``post_type`` = ``video``
        """
        snippet = raw_data.get("snippet", {})
        stats = raw_data.get("statistics", {})

        title = snippet.get("title", "")
        description = snippet.get("description", "")
        content = f"{title}\n{description}".strip()

        # Parse ISO 8601 published date.
        published_str = snippet.get("publishedAt")
        if published_str:
            try:
                published_at = datetime.fromisoformat(
                    published_str.replace("Z", "+00:00")
                )
            except (TypeError, ValueError):
                published_at = datetime.now(UTC)
        else:
            published_at = datetime.now(UTC)

        return {
            "platform_post_id": str(raw_data.get("id", "")),
            "content": content[:10_000],
            "post_type": PostType.VIDEO.value,
            "published_at": published_at,
            "likes": _safe_int(stats.get("likeCount", 0)),
            "comments": _safe_int(stats.get("commentCount", 0)),
            "shares": 0,  # YouTube API does not expose share count.
            "views": _safe_int(stats.get("viewCount", 0)),
            "raw_data": raw_data,
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

            handle = profile.handle
            logger.info(
                "Starting YouTube scrape for profile_id=%d handle=%s",
                profile_id,
                handle,
            )

            # 1. Fetch.
            raw_videos = self.fetch_raw(handle)
            if not raw_videos:
                logger.warning("No videos returned for %s", handle)

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
                    # Update engagement metrics.
                    existing.likes = parsed["likes"]
                    existing.comments = parsed["comments"]
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
                if stats.get("posts_count", 0) > 0:
                    profile.posts_count = stats["posts_count"]
                    updated_profile = True
            except Exception as exc:
                errors.append(f"Profile stats error: {exc}")

            profile.last_scraped_at = datetime.now(UTC)
            session.commit()

        logger.info(
            "YouTube scrape complete: profile_id=%d new_posts=%d errors=%d",
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
        """Fetch channel statistics (subscribers, videos, total views).

        Costs 1 quota unit via ``channels.list(part=statistics)``.
        """
        youtube = self._get_client()
        if youtube is None:
            return {"followers_count": 0, "following_count": 0, "posts_count": 0}

        channel_id = self._resolve_channel_id(handle)
        if channel_id is None:
            return {"followers_count": 0, "following_count": 0, "posts_count": 0}

        try:
            resp = (
                youtube.channels()
                .list(id=channel_id, part="statistics")
                .execute()
            )
            items = resp.get("items", [])
            if not items:
                return {"followers_count": 0, "following_count": 0, "posts_count": 0}

            stats = items[0].get("statistics", {})
            return {
                "followers_count": _safe_int(stats.get("subscriberCount", 0)),
                "following_count": 0,  # YouTube channels don't "follow" others.
                "posts_count": _safe_int(stats.get("videoCount", 0)),
            }
        except Exception as exc:
            logger.error("Failed to fetch channel stats for %s: %s", channel_id, exc)
            return {"followers_count": 0, "following_count": 0, "posts_count": 0}


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
