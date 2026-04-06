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

_MAX_RESULTS = 30  # Videos per scrape run.
_YT_DLP_TIMEOUT = 120  # Seconds before yt-dlp subprocess is killed.


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
    # Keep only the fields we care about to avoid bloating the DB.
    keep_keys = {
        "id", "title", "description", "channel", "channel_id", "channel_url",
        "upload_date", "duration", "view_count", "like_count", "comment_count",
        "thumbnail", "webpage_url", "categories", "tags",
    }
    return {k: v for k, v in raw.items() if k in keep_keys}


class YouTubeScraper(BaseScraper):
    """YouTube scraper using scrapetube + yt-dlp (primary) with YouTube Data API v3 fallback.

    Primary pipeline (no API key required):
    1. scrapetube discovers video IDs from a channel URL.
    2. yt-dlp fetches metadata (title, stats, dates) for each video.

    Fallback pipeline (requires ``settings.YOUTUBE_API_KEY``):
    Uses the official YouTube Data API v3 with quota-efficient
    playlistItems + videos.list strategy.
    """

    platform = "youtube"

    def __init__(self) -> None:
        self._engine = create_engine(
            settings.DATABASE_URL_SYNC,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=2,
        )

    # ------------------------------------------------------------------
    # Primary: scrapetube + yt-dlp
    # ------------------------------------------------------------------

    def _fetch_via_scrapetube(
        self, handle: str, max_results: int = _MAX_RESULTS
    ) -> list[dict[str, Any]]:
        """Fetch video metadata using scrapetube for discovery and yt-dlp for details."""
        try:
            import scrapetube
        except ImportError:
            logger.warning("scrapetube is not installed — skipping primary pipeline")
            return []

        clean_handle = handle.lstrip("@")

        # Step 1: Discover video IDs via scrapetube.
        video_ids: list[str] = []
        try:
            # Try channel URL first (handles @-style handles).
            channel_url = f"https://www.youtube.com/@{clean_handle}"
            videos = scrapetube.get_channel(channel_url=channel_url, limit=max_results)
            for video in videos:
                vid = video.get("videoId")
                if vid:
                    video_ids.append(vid)
        except Exception as exc:
            logger.warning(
                "scrapetube channel fetch failed for @%s: %s", clean_handle, exc
            )

        if not video_ids:
            # Fallback: try search with the handle as query.
            try:
                search_results = scrapetube.get_search(
                    f"{clean_handle}", limit=max_results
                )
                for video in search_results:
                    vid = video.get("videoId")
                    if vid:
                        video_ids.append(vid)
            except Exception as exc:
                logger.warning(
                    "scrapetube search failed for %s: %s", clean_handle, exc
                )

        if not video_ids:
            logger.info("scrapetube found no videos for @%s", clean_handle)
            return []

        logger.info(
            "scrapetube discovered %d video IDs for @%s", len(video_ids), clean_handle
        )

        # Step 2: Fetch full metadata via yt-dlp for each video.
        all_metadata: list[dict[str, Any]] = []
        # Process in batches to avoid extremely long command lines.
        batch_size = 10
        for i in range(0, len(video_ids), batch_size):
            batch = video_ids[i : i + batch_size]
            urls = [f"https://www.youtube.com/watch?v={vid}" for vid in batch]
            output = _run_yt_dlp([
                "--dump-json",
                "--no-download",
                "--no-warnings",
                "--no-playlist",
                *urls,
            ])
            if output:
                all_metadata.extend(_parse_yt_dlp_jsonl(output))

        logger.info(
            "yt-dlp fetched metadata for %d/%d videos for @%s",
            len(all_metadata),
            len(video_ids),
            clean_handle,
        )
        return all_metadata

    def _fetch_channel_stats_via_yt_dlp(self, handle: str) -> dict[str, Any]:
        """Fetch channel-level stats using yt-dlp --dump-json on the channel page."""
        clean_handle = handle.lstrip("@")
        channel_url = f"https://www.youtube.com/@{clean_handle}"

        output = _run_yt_dlp([
            "--dump-json",
            "--no-download",
            "--no-warnings",
            "--playlist-items", "0",
            channel_url,
        ], timeout=30)

        if not output:
            return {}

        entries = _parse_yt_dlp_jsonl(output)
        if not entries:
            return {}

        # yt-dlp channel metadata includes channel_follower_count.
        return entries[0]

    # ------------------------------------------------------------------
    # Fallback: YouTube Data API v3
    # ------------------------------------------------------------------

    def _get_api_client(self) -> Any:
        """Build the YouTube Data API v3 client. Returns None if unavailable."""
        api_key = settings.YOUTUBE_API_KEY
        if not api_key:
            return None

        try:
            from googleapiclient.discovery import build

            return build(
                "youtube", "v3",
                developerKey=api_key,
                cache_discovery=False,
            )
        except ImportError:
            logger.debug("google-api-python-client not installed — API fallback unavailable")
            return None
        except Exception as exc:
            logger.error("Failed to build YouTube API client: %s", exc)
            return None

    def _fetch_via_api(self, handle: str, max_results: int = _MAX_RESULTS) -> list[dict[str, Any]]:
        """Fallback: fetch videos via YouTube Data API v3."""
        youtube = self._get_api_client()
        if youtube is None:
            return []

        clean_handle = handle.lstrip("@")

        # Resolve channel ID.
        channel_id = None
        if clean_handle.startswith("UC") and len(clean_handle) == 24:
            channel_id = clean_handle
        else:
            for method_kwargs in [
                {"forHandle": clean_handle},
                {"forUsername": clean_handle},
            ]:
                try:
                    resp = youtube.channels().list(part="id", **method_kwargs).execute()
                    items = resp.get("items", [])
                    if items:
                        channel_id = items[0]["id"]
                        break
                except Exception as exc:
                    logger.debug("API channel lookup failed with %s: %s", method_kwargs, exc)

        if not channel_id:
            logger.warning("API fallback: could not resolve channel for %s", handle)
            return []

        # Derive uploads playlist: UC... -> UU...
        uploads_playlist = "UU" + channel_id[2:] if channel_id.startswith("UC") else None
        if not uploads_playlist:
            return []

        # Fetch video IDs from uploads playlist.
        video_ids: list[str] = []
        try:
            resp = (
                youtube.playlistItems()
                .list(playlistId=uploads_playlist, part="contentDetails", maxResults=min(max_results, 50))
                .execute()
            )
            for item in resp.get("items", []):
                vid = item.get("contentDetails", {}).get("videoId")
                if vid:
                    video_ids.append(vid)
        except Exception as exc:
            logger.error("API playlistItems.list failed: %s", exc)
            return []

        if not video_ids:
            return []

        # Batch-fetch video details.
        all_videos: list[dict[str, Any]] = []
        for i in range(0, len(video_ids), 50):
            chunk = video_ids[i : i + 50]
            try:
                resp = (
                    youtube.videos()
                    .list(id=",".join(chunk), part="snippet,statistics,contentDetails")
                    .execute()
                )
                all_videos.extend(resp.get("items", []))
            except Exception as exc:
                logger.error("API videos.list failed: %s", exc)

        return all_videos

    def _fetch_api_channel_stats(self, handle: str) -> dict[str, int]:
        """Fetch channel statistics via the API (1 quota unit)."""
        youtube = self._get_api_client()
        if youtube is None:
            return {}

        clean_handle = handle.lstrip("@")
        channel_id = None

        if clean_handle.startswith("UC") and len(clean_handle) == 24:
            channel_id = clean_handle
        else:
            for method_kwargs in [
                {"forHandle": clean_handle},
                {"forUsername": clean_handle},
            ]:
                try:
                    resp = youtube.channels().list(part="id,statistics", **method_kwargs).execute()
                    items = resp.get("items", [])
                    if items:
                        stats = items[0].get("statistics", {})
                        return {
                            "followers_count": _safe_int(stats.get("subscriberCount", 0)),
                            "following_count": 0,
                            "posts_count": _safe_int(stats.get("videoCount", 0)),
                        }
                except Exception:
                    continue

        return {}

    # ------------------------------------------------------------------
    # BaseScraper interface
    # ------------------------------------------------------------------

    def fetch_raw(self, handle: str, **kwargs: Any) -> list[dict[str, Any]]:
        """Fetch recent videos. Primary: scrapetube + yt-dlp. Fallback: API v3."""
        max_results = kwargs.get("max_results", _MAX_RESULTS)

        # Primary pipeline: scrapetube + yt-dlp (no API key needed).
        raw = self._fetch_via_scrapetube(handle, max_results)
        if raw:
            logger.info("Primary pipeline (scrapetube + yt-dlp) returned %d videos", len(raw))
            return raw

        # Fallback: YouTube Data API v3.
        logger.info("Primary pipeline returned nothing — falling back to YouTube Data API v3")
        api_raw = self._fetch_via_api(handle, max_results)
        if api_raw:
            logger.info("API fallback returned %d videos", len(api_raw))
        return api_raw

    def parse(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Parse a video dict into SocialPost fields.

        Handles both yt-dlp format and YouTube Data API v3 format.
        """
        # Detect format: yt-dlp uses flat keys, API nests under snippet/statistics.
        if "snippet" in raw_data:
            return self._parse_api_format(raw_data)
        return self._parse_ytdlp_format(raw_data)

    def _parse_ytdlp_format(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Parse yt-dlp --dump-json output."""
        title = raw_data.get("title", "")
        description = raw_data.get("description", "")
        content = f"{title}\n{description}".strip()

        # upload_date is YYYYMMDD string.
        upload_date_str = raw_data.get("upload_date", "")
        if upload_date_str and len(upload_date_str) == 8:
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

        return {
            "platform_post_id": str(raw_data.get("id", "")),
            "content": content[:10_000],
            "post_type": PostType.VIDEO.value,
            "published_at": published_at,
            "likes": _safe_int(raw_data.get("like_count", 0)),
            "comments": _safe_int(raw_data.get("comment_count", 0)),
            "shares": 0,  # YouTube does not expose share count.
            "views": _safe_int(raw_data.get("view_count", 0)),
            "raw_data": _sanitise_raw(raw_data),
        }

    def _parse_api_format(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Parse YouTube Data API v3 video resource."""
        snippet = raw_data.get("snippet", {})
        stats = raw_data.get("statistics", {})

        title = snippet.get("title", "")
        description = snippet.get("description", "")
        content = f"{title}\n{description}".strip()

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
            "shares": 0,
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
        """Fetch channel statistics. Primary: yt-dlp. Fallback: API v3."""
        empty = {"followers_count": 0, "following_count": 0, "posts_count": 0}

        # Primary: yt-dlp channel metadata.
        channel_meta = self._fetch_channel_stats_via_yt_dlp(handle)
        if channel_meta:
            followers = _safe_int(channel_meta.get("channel_follower_count", 0))
            if followers > 0:
                return {
                    "followers_count": followers,
                    "following_count": 0,
                    "posts_count": 0,  # yt-dlp does not expose total video count.
                }

        # Fallback: API v3.
        api_stats = self._fetch_api_channel_stats(handle)
        if api_stats:
            return api_stats

        return empty
