from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.social import PostType, SocialProfile
from app.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

# Threads web profile endpoint — serves public profile HTML.
# Meta has not released a public Threads API as of 2026-04.
# This scraper extracts what it can from the public web page and
# is structured to be upgraded once an official API becomes available.
_THREADS_BASE = "https://www.threads.net"
_HTTP_TIMEOUT = 30  # seconds
_MAX_POSTS = 30

# NOTE: Platform.THREADS does not exist in the Platform enum yet.
# This scraper uses platform="threads" internally. A migration adding
# THREADS to the enum is required before storing SocialProfile records
# with this platform value.  Until then, this scraper works with
# profiles whose handle is their Instagram/Threads username.


def _safe_int(value: Any) -> int:
    """Coerce a value to int, returning 0 on failure."""
    if value is None:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _clean_handle(handle: str) -> str:
    """Normalize a Threads handle — strip leading @ and whitespace."""
    return handle.strip().lstrip("@")


def _extract_meta_content(html: str, property_name: str) -> str | None:
    """Extract the content attribute from a <meta> tag by property name."""
    pattern = rf'<meta\s+[^>]*property=["\']og:{property_name}["\'][^>]*content=["\']([^"\']*)["\']'
    match = re.search(pattern, html, re.IGNORECASE)
    if match:
        return match.group(1)
    # Try reversed attribute order: content before property.
    pattern_alt = (
        rf'<meta\s+[^>]*content=["\']([^"\']*)["\'][^>]*property=["\']og:{property_name}["\']'
    )
    match_alt = re.search(pattern_alt, html, re.IGNORECASE)
    if match_alt:
        return match_alt.group(1)
    return None


class ThreadsScraper(BaseScraper):
    """Threads (Meta) scraper — stub with public web fallback.

    Meta has not released a public Threads API.  This scraper attempts
    to fetch basic profile information from the public web page at
    ``threads.net/@handle``.  Post-level scraping is intentionally
    limited because:

    1. Threads renders most content client-side via JavaScript, so
       server-side HTML contains minimal post data.
    2. Without an official API, aggressive scraping would violate
       Meta's Terms of Service.

    The scraper is fully structured to the ``BaseScraper`` interface so
    that when Meta opens an API (or a reliable unofficial library
    stabilises), only the HTTP/parse layer needs to change.

    Strategy:
    - ``fetch_raw`` returns an empty list (no reliable post extraction).
    - ``update_profile_stats`` extracts follower count from OG meta tags
      when available.
    - ``scrape`` logs the attempt and returns zero new posts.
    """

    platform = "threads"

    def __init__(self) -> None:
        self._engine = create_engine(
            settings.DATABASE_URL_SYNC,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=2,
        )

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def _get_client(self) -> httpx.Client:
        """Return a configured httpx client for Threads web requests."""
        return httpx.Client(
            timeout=_HTTP_TIMEOUT,
            headers={
                "Accept": "text/html,application/xhtml+xml",
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
            },
            follow_redirects=True,
        )

    def _fetch_profile_page(self, handle: str) -> str | None:
        """GET the public Threads profile page and return raw HTML."""
        clean = _clean_handle(handle)
        url = f"{_THREADS_BASE}/@{clean}"
        try:
            with self._get_client() as client:
                resp = client.get(url)
                resp.raise_for_status()
                return resp.text
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "Threads profile page failed for %s: HTTP %d",
                clean,
                exc.response.status_code,
            )
            return None
        except httpx.HTTPError as exc:
            logger.error("Threads network error for %s: %s", clean, exc)
            return None

    # ------------------------------------------------------------------
    # BaseScraper interface
    # ------------------------------------------------------------------

    def fetch_raw(self, handle: str, **kwargs: Any) -> list[dict[str, Any]]:
        """Fetch raw post data from Threads.

        Returns an empty list because Threads renders posts via
        client-side JavaScript and does not expose them in the
        server-rendered HTML.  This method exists to satisfy the
        BaseScraper interface and will be implemented once an API
        becomes available.
        """
        logger.info(
            "Threads fetch_raw called for %s — no public API available, returning empty result set",
            handle,
        )
        return []

    def parse(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Parse a single Threads post into SocialPost fields.

        Placeholder implementation — will be completed when post data
        becomes available via API.
        """
        return {
            "platform_post_id": raw_data.get("id", ""),
            "content": raw_data.get("text", "")[:10_000],
            "post_type": PostType.TEXT.value,
            "published_at": datetime.now(UTC),
            "likes": _safe_int(raw_data.get("likes", 0)),
            "comments": _safe_int(raw_data.get("replies", 0)),
            "shares": _safe_int(raw_data.get("reposts", 0)),
            "views": 0,
            "raw_data": raw_data,
        }

    def scrape(self, profile_id: int) -> dict[str, Any]:
        """Full scrape pipeline for a Threads profile.

        Currently limited to profile stat updates (follower count from
        OG meta tags).  Post ingestion is deferred until an API opens.
        """
        errors: list[str] = []
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
                "Starting Threads scrape for profile_id=%d handle=%s",
                profile_id,
                handle,
            )

            # Attempt to update profile stats from the web page.
            try:
                stats = self.update_profile_stats(handle)
                if stats.get("followers_count", 0) > 0:
                    profile.followers_count = stats["followers_count"]
                    updated_profile = True
            except Exception as exc:
                errors.append(f"Profile stats error: {exc}")

            # Posts: currently unavailable — log and skip.
            raw_posts = self.fetch_raw(handle)
            if not raw_posts:
                errors.append(
                    "Threads API not available — post scraping deferred. "
                    "Profile stats may have been updated from web page."
                )

            profile.last_scraped_at = datetime.now(UTC)
            session.commit()

        logger.info(
            "Threads scrape complete: profile_id=%d new_posts=0 errors=%d",
            profile_id,
            len(errors),
        )
        return {
            "new_posts": 0,
            "updated_profile": updated_profile,
            "errors": errors,
        }

    def update_profile_stats(self, handle: str) -> dict[str, int]:
        """Extract profile statistics from Threads web page OG meta tags.

        The Threads profile page sometimes includes follower count in
        the ``og:description`` meta tag (e.g. "12.3K Followers").  This
        is best-effort and may return zeros if Meta changes the markup.
        """
        empty: dict[str, int] = {
            "followers_count": 0,
            "following_count": 0,
            "posts_count": 0,
        }

        html = self._fetch_profile_page(handle)
        if not html:
            return empty

        description = _extract_meta_content(html, "description") or ""

        # Try to parse follower count from description like "12.3K Followers".
        followers = 0
        follower_match = re.search(
            r"([\d,.]+[KkMm]?)\s*[Ff]ollowers?",
            description,
        )
        if follower_match:
            raw_count = follower_match.group(1).replace(",", "")
            multiplier = 1
            if raw_count[-1].upper() == "K":
                multiplier = 1_000
                raw_count = raw_count[:-1]
            elif raw_count[-1].upper() == "M":
                multiplier = 1_000_000
                raw_count = raw_count[:-1]
            try:
                followers = int(float(raw_count) * multiplier)
            except (TypeError, ValueError):
                followers = 0

        return {
            "followers_count": followers,
            "following_count": 0,  # Not available from web page.
            "posts_count": 0,  # Not available from web page.
        }
