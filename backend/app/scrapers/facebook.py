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

# Timeout for all facebook-scraper network operations (seconds).
_REQUEST_TIMEOUT = 30
# Maximum pages of posts to retrieve per scrape run.
_MAX_PAGES = 5


class FacebookScraper(BaseScraper):
    """Facebook scraper for public pages using the facebook-scraper library.

    Operates in degraded mode (returns empty results) when the library is
    unavailable or Facebook blocks the request.  An optional cookies file
    (``settings.FACEBOOK_COOKIES_FILE``) can be supplied to improve access
    reliability.
    """

    platform = "facebook"

    def __init__(self) -> None:
        self._engine = create_engine(
            settings.DATABASE_URL_SYNC,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=2,
        )

    # ------------------------------------------------------------------
    # BaseScraper interface
    # ------------------------------------------------------------------

    def fetch_raw(self, handle: str, **kwargs: Any) -> list[dict[str, Any]]:
        """Scrape public posts from a Facebook page via *facebook-scraper*.

        Args:
            handle: The Facebook page username or numeric ID.

        Returns:
            A list of raw post dicts as emitted by ``get_posts()``.
        """
        try:
            from facebook_scraper import get_posts, set_cookies
        except ImportError:
            logger.error(
                "facebook-scraper is not installed. "
                "Install with: pip install facebook-scraper"
            )
            return []

        pages = kwargs.get("pages", _MAX_PAGES)

        # Optional: load cookies for better access to restricted pages.
        cookies_path = settings.FACEBOOK_COOKIES_FILE
        if cookies_path:
            try:
                set_cookies(cookies_path)
                logger.debug("Loaded Facebook cookies from %s", cookies_path)
            except Exception:
                logger.warning(
                    "Failed to load Facebook cookies from %s — proceeding without",
                    cookies_path,
                )

        raw_posts: list[dict[str, Any]] = []
        try:
            for post in get_posts(
                handle,
                pages=pages,
                timeout=_REQUEST_TIMEOUT,
                options={
                    "comments": True,
                    "reactors": False,
                    "allow_extra_requests": False,
                },
            ):
                raw_posts.append(dict(post))
        except Exception as exc:
            logger.error(
                "facebook-scraper failed for handle=%s: %s",
                handle,
                exc,
            )

        logger.info(
            "Fetched %d raw posts from Facebook for handle=%s",
            len(raw_posts),
            handle,
        )
        return raw_posts

    def parse(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Normalise a single facebook-scraper post dict into SocialPost fields.

        Field mapping
        ~~~~~~~~~~~~~
        * ``post_id`` -> ``platform_post_id``
        * ``text`` -> ``content``
        * ``likes`` -> ``likes``  (integer reaction count)
        * ``comments`` (int) or len(``comments_full``) -> ``comments``
        * ``shares`` -> ``shares``
        * ``images`` / ``video`` presence determines ``post_type``
        * ``time`` -> ``published_at``
        """
        # Determine post type from media presence.
        post_type = PostType.TEXT
        if raw_data.get("video"):
            post_type = PostType.VIDEO
        elif raw_data.get("images"):
            post_type = PostType.IMAGE

        # Comment count: prefer the structured list length when available.
        comments_full = raw_data.get("comments_full")
        if isinstance(comments_full, list):
            comments_count = len(comments_full)
        else:
            comments_count = _safe_int(raw_data.get("comments", 0))

        # Published timestamp — facebook-scraper returns a datetime or None.
        published_at = raw_data.get("time")
        if published_at is None:
            published_at = datetime.now(UTC)
        elif isinstance(published_at, datetime) and published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=UTC)

        return {
            "platform_post_id": str(raw_data.get("post_id", "")),
            "content": (raw_data.get("text") or "")[:10_000],
            "post_type": post_type.value,
            "published_at": published_at,
            "likes": _safe_int(raw_data.get("likes", 0)),
            "comments": comments_count,
            "shares": _safe_int(raw_data.get("shares", 0)),
            "views": 0,
            "raw_data": _sanitise_raw(raw_data),
        }

    def scrape(self, profile_id: int) -> dict[str, Any]:
        """Full scrape pipeline: fetch -> parse -> dedup -> store.

        Returns:
            ``{"new_posts": int, "updated_profile": bool, "errors": list[str]}``
        """
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
            logger.info("Starting Facebook scrape for profile_id=%d handle=%s", profile_id, handle)

            # 1. Fetch raw posts.
            raw_posts = self.fetch_raw(handle)
            if not raw_posts:
                logger.warning("No raw posts returned for %s", handle)

            # 2. Parse and deduplicate.
            for raw in raw_posts:
                try:
                    parsed = self.parse(raw)
                except Exception as exc:
                    errors.append(f"Parse error: {exc}")
                    continue

                platform_post_id = parsed["platform_post_id"]
                if not platform_post_id:
                    continue

                # Check for existing post (dedup).
                existing = session.execute(
                    select(SocialPost).where(
                        SocialPost.platform_post_id == platform_post_id
                    )
                ).scalar_one_or_none()

                if existing is not None:
                    # Update engagement metrics on existing post.
                    existing.likes = parsed["likes"]
                    existing.comments = parsed["comments"]
                    existing.shares = parsed["shares"]
                    continue

                # 3. Create new post.
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

            # 4. Update profile stats.
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
            "Facebook scrape complete: profile_id=%d new_posts=%d errors=%d",
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
        """Attempt to extract page-level stats from the first scraped post.

        The facebook-scraper library does not provide a dedicated endpoint for
        page metadata, so we pull whatever is available from a single-page
        scrape.  Returns zeros when nothing is available.
        """
        try:
            from facebook_scraper import get_posts
        except ImportError:
            return {"followers_count": 0, "following_count": 0, "posts_count": 0}

        followers = 0
        try:
            # Fetch just one page to inspect page_info metadata if available.
            posts = list(
                get_posts(
                    handle,
                    pages=1,
                    timeout=_REQUEST_TIMEOUT,
                    options={"allow_extra_requests": False},
                )
            )
            if posts:
                # Some versions of facebook-scraper include page likes.
                first = posts[0]
                followers = _safe_int(first.get("page_likes", 0))
        except Exception as exc:
            logger.warning("Could not fetch profile stats for %s: %s", handle, exc)

        return {
            "followers_count": followers,
            "following_count": 0,
            "posts_count": 0,
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
    """Strip non-serialisable objects from a raw post dict before storing as JSONB.

    facebook-scraper can return datetime objects, sets, and other types that
    are not directly JSON-serialisable.  We convert them to strings.
    """
    clean: dict[str, Any] = {}
    for key, value in raw.items():
        if isinstance(value, datetime):
            clean[key] = value.isoformat()
        elif isinstance(value, set):
            clean[key] = list(value)
        elif isinstance(value, (str, int, float, bool, type(None))):
            clean[key] = value
        elif isinstance(value, (list, dict)):
            # Shallow pass-through; nested non-serialisable objects may still
            # cause issues on very edge-case posts — acceptable trade-off.
            try:
                import json

                json.dumps(value)
                clean[key] = value
            except (TypeError, ValueError):
                clean[key] = str(value)
        else:
            clean[key] = str(value)
    return clean
