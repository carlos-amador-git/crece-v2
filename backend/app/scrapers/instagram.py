"""Instagram scraper using instaloader for post and profile data.

Design decisions:
- instaloader works synchronously, matching Celery worker context.
- No login required for public profiles (degraded mode).  When credentials
  are provided via INSTAGRAM_USERNAME / INSTAGRAM_PASSWORD env vars, the
  scraper logs in and caches the session file for reuse.
- Private profiles are detected and skipped gracefully.
- instaloader has built-in rate-limit handling (429 retry with backoff).
  We add our own outer retry for transient network errors.
"""

from __future__ import annotations

import logging
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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
_MAX_POSTS_PER_SCRAPE = 50
_MAX_RETRIES = 3
_SESSION_DIR = Path.home() / ".config" / "crece" / "instaloader_sessions"


def _get_sync_session() -> Session:
    """Create a synchronous SQLAlchemy session for Celery worker context."""
    engine = create_engine(
        settings.DATABASE_URL_SYNC,
        pool_size=5,
        max_overflow=2,
        pool_pre_ping=True,
    )
    return Session(bind=engine, expire_on_commit=False)


class InstagramScraper(BaseScraper):
    """Instagram scraper powered by instaloader.

    Works without credentials for public profiles.  Set environment
    variables INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD to enable
    authenticated mode (needed for private profiles and higher rate limits).
    """

    platform = "instagram"

    def __init__(self) -> None:
        self._loader: Any | None = None
        self._logged_in: bool = False

    # ------------------------------------------------------------------
    # Instaloader lifecycle
    # ------------------------------------------------------------------
    def _get_loader(self) -> Any:
        """Lazy-init the Instaloader instance with optional login."""
        if self._loader is not None:
            return self._loader

        try:
            import instaloader  # type: ignore[import-untyped]
        except ImportError:
            logger.error(
                "instaloader is not installed. "
                "Install it with: pip install instaloader"
            )
            raise

        self._loader = instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            quiet=True,
            # Lower request frequency to be polite
            max_connection_attempts=3,
        )

        # Attempt to load saved session or login
        username = os.environ.get("INSTAGRAM_USERNAME", "").strip()
        password = os.environ.get("INSTAGRAM_PASSWORD", "").strip()

        if username:
            session_file = _SESSION_DIR / username
            if session_file.exists():
                try:
                    self._loader.load_session_from_file(username, str(session_file))
                    self._logged_in = True
                    logger.info("Loaded Instagram session for @%s", username)
                    return self._loader
                except Exception as exc:
                    logger.warning(
                        "Failed to load saved session for @%s: %s — attempting fresh login",
                        username,
                        exc,
                    )

            if password:
                try:
                    self._loader.login(username, password)
                    self._logged_in = True
                    # Persist session for reuse
                    _SESSION_DIR.mkdir(parents=True, exist_ok=True)
                    self._loader.save_session_to_file(str(session_file))
                    logger.info("Logged in to Instagram as @%s (session saved)", username)
                except Exception as exc:
                    logger.warning(
                        "Instagram login failed for @%s: %s — continuing without auth",
                        username,
                        exc,
                    )
            else:
                logger.info(
                    "INSTAGRAM_USERNAME set but no INSTAGRAM_PASSWORD — running unauthenticated"
                )
        else:
            logger.info("No Instagram credentials configured — running in public-only mode")

        return self._loader

    # ------------------------------------------------------------------
    # BaseScraper interface
    # ------------------------------------------------------------------
    def fetch_raw(self, handle: str, **kwargs: Any) -> list[dict[str, Any]]:
        """Fetch recent posts for an Instagram handle.

        Returns a list of serialized post dicts.
        """
        import instaloader  # type: ignore[import-untyped]

        handle = handle.lstrip("@").strip()
        limit = kwargs.get("limit", _MAX_POSTS_PER_SCRAPE)

        if not handle:
            logger.error("Empty handle provided to InstagramScraper.fetch_raw")
            return []

        loader = self._get_loader()

        for attempt in range(_MAX_RETRIES):
            try:
                profile = instaloader.Profile.from_username(loader.context, handle)

                # Check for private profile
                if profile.is_private and not profile.followed_by_viewer:
                    logger.warning(
                        "Profile @%s is private and not followed — skipping posts",
                        handle,
                    )
                    # Still return empty list but log the profile stats
                    return []

                posts: list[dict[str, Any]] = []
                for i, post in enumerate(profile.get_posts()):
                    if i >= limit:
                        break
                    posts.append(self._serialize_post(post))

                logger.info(
                    "Fetched %d posts for @%s (is_private=%s)",
                    len(posts),
                    handle,
                    profile.is_private,
                )
                return posts

            except instaloader.exceptions.ProfileNotExistsException:
                logger.error("Instagram profile @%s does not exist", handle)
                return []

            except instaloader.exceptions.ConnectionException as exc:
                logger.warning(
                    "Connection error fetching @%s (attempt %d/%d): %s",
                    handle,
                    attempt + 1,
                    _MAX_RETRIES,
                    exc,
                )
                if attempt < _MAX_RETRIES - 1:
                    # instaloader handles 429 internally, but we retry on connection drops
                    backoff = 30 * (attempt + 1)
                    logger.info("Waiting %ds before retry...", backoff)
                    time.sleep(backoff)

            except instaloader.exceptions.LoginRequiredException:
                logger.error(
                    "Instagram requires login to access @%s — configure credentials",
                    handle,
                )
                return []

            except instaloader.exceptions.QueryReturnedBadRequestException as exc:
                logger.error("Bad request for @%s: %s", handle, exc)
                return []

            except Exception as exc:
                logger.error(
                    "Unexpected error fetching @%s (attempt %d/%d): %s",
                    handle,
                    attempt + 1,
                    _MAX_RETRIES,
                    exc,
                )
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(15 * (attempt + 1))

        logger.error("All retries exhausted for Instagram @%s", handle)
        return []

    def parse(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Parse a serialized Instagram post into normalized SocialPost fields."""
        # Determine post type
        post_type = self._determine_post_type(raw_data)

        # Parse published_at
        published_at = self._parse_post_date(raw_data)

        # Content: Instagram uses caption
        content = raw_data.get("caption") or ""

        # Metrics
        likes = raw_data.get("likes", 0) or 0
        comments = raw_data.get("comments", 0) or 0
        views = raw_data.get("video_view_count", 0) or 0

        return {
            "platform_post_id": raw_data.get("shortcode", ""),
            "content": content,
            "post_type": post_type,
            "published_at": published_at,
            "likes": int(likes),
            "comments": int(comments),
            "shares": 0,  # Instagram does not expose share counts publicly
            "views": int(views),
            "raw_data": raw_data,
        }

    def update_profile_stats(self, handle: str) -> dict[str, int]:
        """Fetch current profile statistics for an Instagram handle."""
        import instaloader  # type: ignore[import-untyped]

        handle = handle.lstrip("@").strip()
        default = {"followers_count": 0, "following_count": 0, "posts_count": 0}

        if not handle:
            return default

        loader = self._get_loader()

        for attempt in range(_MAX_RETRIES):
            try:
                profile = instaloader.Profile.from_username(loader.context, handle)
                stats = {
                    "followers_count": profile.followers,
                    "following_count": profile.followees,
                    "posts_count": profile.mediacount,
                }
                logger.info(
                    "Instagram stats for @%s: %d followers, %d following, %d posts",
                    handle,
                    stats["followers_count"],
                    stats["following_count"],
                    stats["posts_count"],
                )
                return stats

            except instaloader.exceptions.ProfileNotExistsException:
                logger.error("Instagram profile @%s does not exist", handle)
                return default

            except instaloader.exceptions.ConnectionException as exc:
                logger.warning(
                    "Connection error getting stats for @%s (attempt %d): %s",
                    handle,
                    attempt + 1,
                    exc,
                )
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(20 * (attempt + 1))

            except Exception as exc:
                logger.warning(
                    "Error getting stats for @%s (attempt %d): %s",
                    handle,
                    attempt + 1,
                    exc,
                )
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(10 * (attempt + 1))

        return default

    def scrape(self, profile_id: int) -> dict[str, Any]:
        """Full scrape pipeline for an Instagram profile.

        1. Load profile from DB
        2. Fetch raw posts
        3. Parse each post
        4. Deduplicate by platform_post_id (shortcode)
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
                "Starting Instagram scrape for @%s (profile_id=%d)",
                handle,
                profile_id,
            )

            # 2. Fetch raw posts
            try:
                raw_posts = self.fetch_raw(handle)
            except Exception as exc:
                msg = f"fetch_raw failed for @{handle}: {exc}"
                logger.error(msg)
                errors.append(msg)
                raw_posts = []

            # 3 & 4. Parse and deduplicate
            if raw_posts:
                # Load existing IDs in one query
                existing_ids_query = (
                    select(SocialPost.platform_post_id)
                    .where(SocialPost.profile_id == profile_id)
                )
                existing_ids: set[str] = {
                    row[0] for row in session.execute(existing_ids_query).all()
                }

                for raw_post in raw_posts:
                    try:
                        parsed = self.parse(raw_post)

                        if not parsed["platform_post_id"]:
                            logger.debug("Skipping post with empty shortcode")
                            continue

                        if parsed["platform_post_id"] in existing_ids:
                            continue

                        # 5. Upsert new post
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
                        msg = f"Error parsing/storing IG post: {exc}"
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
                "Instagram scrape complete for @%s: %d new posts, profile_updated=%s, errors=%d",
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
    def _serialize_post(post: Any) -> dict[str, Any]:
        """Convert an instaloader.Post to a plain dict for storage and parsing.

        We extract only the fields we need to avoid serialization issues
        with instaloader's lazy-loaded objects.
        """
        try:
            caption = post.caption or ""
        except Exception:
            caption = ""

        try:
            likes = post.likes
        except Exception:
            likes = 0

        try:
            comments = post.comments
        except Exception:
            comments = 0

        try:
            video_view_count = post.video_view_count if post.is_video else 0
        except Exception:
            video_view_count = 0

        try:
            is_video = post.is_video
        except Exception:
            is_video = False

        try:
            typename = post.typename
        except Exception:
            typename = "GraphImage"

        try:
            date_utc = post.date_utc.isoformat() if post.date_utc else None
        except Exception:
            date_utc = None

        try:
            shortcode = post.shortcode
        except Exception:
            shortcode = ""

        try:
            url = post.url
        except Exception:
            url = ""

        try:
            media_count = post.mediacount if hasattr(post, "mediacount") else 1
        except Exception:
            media_count = 1

        try:
            hashtags = list(post.caption_hashtags) if post.caption_hashtags else []
        except Exception:
            hashtags = []

        try:
            mentions = list(post.caption_mentions) if post.caption_mentions else []
        except Exception:
            mentions = []

        return {
            "shortcode": shortcode,
            "caption": caption,
            "likes": likes,
            "comments": comments,
            "video_view_count": video_view_count,
            "is_video": is_video,
            "typename": typename,
            "date_utc": date_utc,
            "url": url,
            "media_count": media_count,
            "hashtags": hashtags,
            "mentions": mentions,
        }

    @staticmethod
    def _determine_post_type(raw_data: dict[str, Any]) -> str:
        """Determine PostType from Instagram post metadata."""
        typename = raw_data.get("typename", "")
        is_video = raw_data.get("is_video", False)

        if typename == "GraphSidecar":
            return PostType.CAROUSEL

        if is_video:
            # Instagram Reels have specific indicators, but instaloader
            # does not always distinguish Reels from regular videos.
            # We classify as VIDEO; downstream consumers can refine.
            return PostType.VIDEO

        return PostType.IMAGE

    @staticmethod
    def _parse_post_date(raw_data: dict[str, Any]) -> datetime | None:
        """Parse the post publication date."""
        date_val = raw_data.get("date_utc")
        if date_val is None:
            return None

        if isinstance(date_val, datetime):
            return date_val.replace(tzinfo=UTC) if date_val.tzinfo is None else date_val

        if isinstance(date_val, str):
            for fmt in (
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%S.%f%z",
                "%Y-%m-%d %H:%M:%S",
            ):
                try:
                    dt = datetime.strptime(date_val, fmt)
                    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt
                except ValueError:
                    continue

            logger.debug("Could not parse Instagram date: %s", date_val)

        return None
