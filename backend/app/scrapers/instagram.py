"""Instagram scraper using ensta (Guest mode) with instaloader fallback.

Design decisions:
- Primary: ensta Guest mode — no authentication needed, works reliably in 2026.
- Fallback: instaloader with auth (INSTAGRAM_USERNAME / INSTAGRAM_PASSWORD env vars)
  in case ensta is unavailable or fails for a particular profile.
- Both libraries work synchronously, matching the Celery worker context.
- Deduplication by platform_post_id (Instagram shortcode).
- Private profiles are detected and skipped gracefully.
"""

from __future__ import annotations

import logging
import os
import time
from datetime import UTC, datetime
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
    """Instagram scraper powered by ensta (Guest mode) with instaloader fallback.

    Primary mode requires no credentials. Set environment variables
    INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD to enable the instaloader
    fallback (used when ensta fails).
    """

    platform = "instagram"

    # ------------------------------------------------------------------
    # ensta (primary)
    # ------------------------------------------------------------------
    @staticmethod
    def _fetch_with_ensta(
        handle: str,
        limit: int,
    ) -> tuple[list[dict[str, Any]], dict[str, int]]:
        """Fetch posts and profile stats via ensta Guest mode.

        Returns (raw_posts, profile_stats).
        Raises on any failure so the caller can fall through to the fallback.
        """
        from ensta import Guest  # type: ignore[import-untyped]

        guest = Guest()
        profile = guest.profile(handle)

        profile_stats = {
            "followers_count": profile.follower_count or 0,
            "following_count": profile.following_count or 0,
            "posts_count": profile.total_post_count or 0,
        }

        if profile.is_private:
            logger.warning(
                "Profile @%s is private — returning stats only (no posts)",
                handle,
            )
            return [], profile_stats

        raw_posts: list[dict[str, Any]] = []
        for i, post in enumerate(guest.posts(handle, count=limit)):
            if i >= limit:
                break
            raw_posts.append(
                {
                    "shortcode": post.code or "",
                    "caption": post.caption_text or "",
                    "likes": post.like_count or 0,
                    "comments": post.comment_count or 0,
                    "taken_at": post.taken_at,  # unix timestamp
                }
            )

        return raw_posts, profile_stats

    # ------------------------------------------------------------------
    # instaloader (fallback)
    # ------------------------------------------------------------------
    @staticmethod
    def _fetch_with_instaloader(
        handle: str,
        limit: int,
    ) -> tuple[list[dict[str, Any]], dict[str, int]]:
        """Fetch posts and profile stats via instaloader with auth.

        Requires INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD env vars.
        Raises on any failure.
        """
        import instaloader  # type: ignore[import-untyped]

        username = os.environ.get("INSTAGRAM_USERNAME", "").strip()
        password = os.environ.get("INSTAGRAM_PASSWORD", "").strip()

        if not username or not password:
            raise RuntimeError(
                "instaloader fallback requires INSTAGRAM_USERNAME and "
                "INSTAGRAM_PASSWORD environment variables"
            )

        loader = instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            quiet=True,
            max_connection_attempts=3,
        )
        loader.login(username, password)

        ig_profile = instaloader.Profile.from_username(loader.context, handle)

        profile_stats = {
            "followers_count": ig_profile.followers,
            "following_count": ig_profile.followees,
            "posts_count": ig_profile.mediacount,
        }

        if ig_profile.is_private and not ig_profile.followed_by_viewer:
            logger.warning(
                "Profile @%s is private (instaloader fallback) — stats only",
                handle,
            )
            return [], profile_stats

        raw_posts: list[dict[str, Any]] = []
        for i, post in enumerate(ig_profile.get_posts()):
            if i >= limit:
                break
            raw_posts.append(
                {
                    "shortcode": post.shortcode or "",
                    "caption": post.caption or "",
                    "likes": post.likes or 0,
                    "comments": post.comments or 0,
                    "taken_at": (int(post.date_utc.timestamp()) if post.date_utc else None),
                }
            )

        return raw_posts, profile_stats

    # ------------------------------------------------------------------
    # BaseScraper interface
    # ------------------------------------------------------------------
    def fetch_raw(self, handle: str, **kwargs: Any) -> list[dict[str, Any]]:
        """Fetch recent posts for an Instagram handle.

        Tries ensta Guest mode first, falls back to instaloader with auth.
        """
        handle = handle.lstrip("@").strip()
        limit = kwargs.get("limit", _MAX_POSTS_PER_SCRAPE)

        if not handle:
            logger.error("Empty handle provided to InstagramScraper.fetch_raw")
            return []

        # Store profile stats for later use by scrape()
        self._last_profile_stats: dict[str, int] | None = None

        for attempt in range(_MAX_RETRIES):
            try:
                posts, stats = self._fetch_with_ensta(handle, limit)
                self._last_profile_stats = stats
                logger.info(
                    "ensta: fetched %d posts for @%s (attempt %d)",
                    len(posts),
                    handle,
                    attempt + 1,
                )
                return posts

            except Exception as exc:
                logger.warning(
                    "ensta failed for @%s (attempt %d/%d): %s",
                    handle,
                    attempt + 1,
                    _MAX_RETRIES,
                    exc,
                )
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(5 * (attempt + 1))

        # All ensta retries exhausted — try instaloader fallback once
        logger.info("Falling back to instaloader for @%s", handle)
        try:
            posts, stats = self._fetch_with_instaloader(handle, limit)
            self._last_profile_stats = stats
            logger.info(
                "instaloader fallback: fetched %d posts for @%s",
                len(posts),
                handle,
            )
            return posts
        except Exception as exc:
            logger.error(
                "instaloader fallback also failed for @%s: %s",
                handle,
                exc,
            )

        return []

    def parse(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Parse a raw Instagram post dict into normalized SocialPost fields."""
        content = raw_data.get("caption") or ""
        likes = raw_data.get("likes", 0) or 0
        comments = raw_data.get("comments", 0) or 0

        # Parse taken_at (unix timestamp)
        taken_at = raw_data.get("taken_at")
        published_at: datetime | None = None
        if taken_at is not None:
            try:
                published_at = datetime.fromtimestamp(int(taken_at), tz=UTC)
            except (ValueError, TypeError, OSError):
                published_at = None

        # ensta does not expose post type metadata; default to IMAGE.
        # Downstream NLP/content pipelines can refine this.
        post_type = PostType.IMAGE

        return {
            "platform_post_id": raw_data.get("shortcode", ""),
            "content": content,
            "post_type": post_type,
            "published_at": published_at,
            "likes": int(likes),
            "comments": int(comments),
            "shares": 0,  # Instagram does not expose share counts publicly
            "views": 0,
            "raw_data": raw_data,
        }

    def update_profile_stats(self, handle: str) -> dict[str, int]:
        """Return profile statistics.

        If fetch_raw was called first (normal scrape flow), reuses cached
        stats to avoid a redundant API call. Otherwise fetches fresh.
        """
        default = {"followers_count": 0, "following_count": 0, "posts_count": 0}

        # Reuse stats from fetch_raw if available
        cached = getattr(self, "_last_profile_stats", None)
        if cached is not None:
            return cached

        # Standalone call — fetch stats only via ensta
        handle = handle.lstrip("@").strip()
        if not handle:
            return default

        try:
            from ensta import Guest  # type: ignore[import-untyped]

            guest = Guest()
            profile = guest.profile(handle)
            stats = {
                "followers_count": profile.follower_count or 0,
                "following_count": profile.following_count or 0,
                "posts_count": profile.total_post_count or 0,
            }
            logger.info(
                "Instagram stats for @%s: %d followers, %d following, %d posts",
                handle,
                stats["followers_count"],
                stats["following_count"],
                stats["posts_count"],
            )
            return stats
        except Exception as exc:
            logger.error("Failed to fetch stats for @%s: %s", handle, exc)
            return default

    def scrape(self, profile_id: int) -> dict[str, Any]:
        """Full scrape pipeline for an Instagram profile.

        1. Load profile from DB
        2. Fetch raw posts (ensta -> instaloader fallback)
        3. Parse and deduplicate by platform_post_id (shortcode)
        4. Store new posts
        5. Update profile stats
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

            # 2. Fetch raw posts (also caches profile stats)
            try:
                raw_posts = self.fetch_raw(handle)
            except Exception as exc:
                msg = f"fetch_raw failed for @{handle}: {exc}"
                logger.error(msg)
                errors.append(msg)
                raw_posts = []

            # 3 & 4. Parse, deduplicate, and store
            if raw_posts:
                existing_ids_query = select(SocialPost.platform_post_id).where(
                    SocialPost.profile_id == profile_id
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
                            .on_conflict_do_nothing(index_elements=["platform_post_id"])
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

            # 5. Update profile stats
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
