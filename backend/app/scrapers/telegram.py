from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.social import PostType, SocialPost, SocialProfile
from app.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

# Public Telegram channel preview endpoint — serves recent messages as
# server-rendered HTML without authentication.
_TELEGRAM_BASE = "https://t.me/s"
_HTTP_TIMEOUT = 30  # seconds
_MAX_POSTS = 30

# NOTE: Platform.TELEGRAM does not exist in the Platform enum yet.
# A migration adding TELEGRAM to the enum is required before storing
# SocialProfile records with this platform value.


def _safe_int(value: Any) -> int:
    """Coerce a value to int, returning 0 on failure."""
    if value is None:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _clean_channel(handle: str) -> str:
    """Normalize a Telegram channel handle.

    Accepts formats: ``@channel``, ``channel``, ``https://t.me/channel``.
    Returns the bare channel name without @ or URL prefix.
    """
    handle = handle.strip()
    # Strip full URL prefix.
    for prefix in ("https://t.me/s/", "https://t.me/", "http://t.me/", "t.me/"):
        if handle.startswith(prefix):
            handle = handle[len(prefix) :]
            break
    return handle.lstrip("@").rstrip("/")


def _parse_subscriber_count(text: str) -> int:
    """Parse subscriber count from Telegram's channel info header.

    Handles formats like "12 345 subscribers", "1.2K members", etc.
    """
    # Remove non-breaking spaces and normalise whitespace.
    text = text.replace("\xa0", " ").strip()

    match = re.search(
        r"([\d\s,.]+[KkMm]?)\s*(?:subscribers?|members?)",
        text,
    )
    if not match:
        return 0

    raw = match.group(1).replace(" ", "").replace(",", "")
    multiplier = 1
    if raw and raw[-1].upper() == "K":
        multiplier = 1_000
        raw = raw[:-1]
    elif raw and raw[-1].upper() == "M":
        multiplier = 1_000_000
        raw = raw[:-1]

    try:
        return int(float(raw) * multiplier)
    except (TypeError, ValueError):
        return 0


def _extract_messages(html: str) -> list[dict[str, Any]]:
    """Extract message blocks from the t.me/s/ HTML page.

    The public preview page renders each message inside a
    ``<div class="tgme_widget_message_wrap">`` with nested elements for
    text, views, date, and media.  We use regex extraction to avoid
    requiring BeautifulSoup as a dependency.
    """
    messages: list[dict[str, Any]] = []

    # Each message block is wrapped in a div with data-post="channel/ID".
    post_pattern = re.compile(
        r'<div[^>]*class="tgme_widget_message_wrap[^"]*"[^>]*>'
        r'.*?data-post="([^"]+)"',
        re.DOTALL,
    )

    # Split the HTML by message wrappers.
    # A more robust approach: find all data-post attributes.
    post_ids = re.findall(r'data-post="([^"]+)"', html)

    # Extract text blocks.  Each message's text lives in
    # <div class="tgme_widget_message_text ...">...</div>.
    text_blocks = re.findall(
        r'<div[^>]*class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>',
        html,
        re.DOTALL,
    )

    # Extract view counts: <span class="tgme_widget_message_views">1.2K</span>
    view_blocks = re.findall(
        r'<span[^>]*class="tgme_widget_message_views"[^>]*>([\d.KkMm\s]+)</span>',
        html,
    )

    # Extract dates: <time ... datetime="2026-04-01T12:00:00+00:00">
    date_blocks = re.findall(
        r'<time[^>]*datetime="([^"]+)"',
        html,
    )

    # Detect media presence per message for post type classification.
    # Look for <a class="tgme_widget_message_photo_wrap"> or video tags.
    has_photo = re.findall(
        r'data-post="([^"]+)"[^>]*>.*?tgme_widget_message_photo',
        html,
        re.DOTALL,
    )
    has_video = re.findall(
        r'data-post="([^"]+)"[^>]*>.*?tgme_widget_message_video',
        html,
        re.DOTALL,
    )
    photo_ids = set(has_photo)
    video_ids = set(has_video)

    for i, post_id in enumerate(post_ids):
        # post_id format: "channel_name/12345"
        parts = post_id.split("/")
        message_id = parts[-1] if parts else post_id

        text = ""
        if i < len(text_blocks):
            # Strip HTML tags from the text content.
            raw_text = text_blocks[i]
            text = re.sub(r"<[^>]+>", "", raw_text).strip()

        views = 0
        if i < len(view_blocks):
            views = _parse_view_count(view_blocks[i])

        published_at = datetime.now(UTC)
        if i < len(date_blocks):
            try:
                published_at = datetime.fromisoformat(
                    date_blocks[i].replace("Z", "+00:00")
                )
            except (TypeError, ValueError):
                pass

        # Determine post type.
        post_type = PostType.TEXT.value
        if post_id in video_ids:
            post_type = PostType.VIDEO.value
        elif post_id in photo_ids:
            post_type = PostType.IMAGE.value

        messages.append({
            "id": message_id,
            "post_id": post_id,
            "text": text,
            "views": views,
            "published_at": published_at,
            "post_type": post_type,
        })

    return messages


def _parse_view_count(raw: str) -> int:
    """Parse a view count string like '1.2K' or '45' into an integer."""
    raw = raw.strip().replace(" ", "")
    multiplier = 1
    if raw and raw[-1].upper() == "K":
        multiplier = 1_000
        raw = raw[:-1]
    elif raw and raw[-1].upper() == "M":
        multiplier = 1_000_000
        raw = raw[:-1]
    try:
        return int(float(raw) * multiplier)
    except (TypeError, ValueError):
        return 0


class TelegramScraper(BaseScraper):
    """Telegram public channel scraper using the t.me/s/ web preview.

    This scraper targets **public channels only**.  It fetches the
    server-rendered HTML from ``https://t.me/s/CHANNEL`` which displays
    recent messages without requiring authentication or a bot token.

    Limitations:
    - Only the most recent ~20 messages are shown on the preview page.
    - View counts are approximate (Telegram rounds them).
    - Likes/comments are not exposed on the public preview.
    - Private channels and groups are not accessible.

    For deeper scraping (full history, reactions, comments), the
    Telethon library with a user session or Bot API with a token would
    be needed.  This implementation is designed to be extended.
    """

    platform = "telegram"

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
        """Return a configured httpx client for Telegram web requests."""
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

    def _fetch_channel_page(self, channel: str) -> str | None:
        """GET the public Telegram channel preview page."""
        clean = _clean_channel(channel)
        url = f"{_TELEGRAM_BASE}/{clean}"
        try:
            with self._get_client() as client:
                resp = client.get(url)
                resp.raise_for_status()
                return resp.text
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "Telegram channel page failed for %s: HTTP %d",
                clean,
                exc.response.status_code,
            )
            return None
        except httpx.HTTPError as exc:
            logger.error("Telegram network error for %s: %s", clean, exc)
            return None

    # ------------------------------------------------------------------
    # BaseScraper interface
    # ------------------------------------------------------------------

    def fetch_raw(self, handle: str, **kwargs: Any) -> list[dict[str, Any]]:
        """Fetch recent messages from a public Telegram channel.

        Parses the t.me/s/ HTML page to extract message data including
        text, view counts, timestamps, and media type.
        """
        max_posts = kwargs.get("max_results", _MAX_POSTS)
        html = self._fetch_channel_page(handle)
        if not html:
            logger.warning("No HTML returned for Telegram channel %s", handle)
            return []

        messages = _extract_messages(html)
        logger.info(
            "Telegram channel %s returned %d messages",
            handle,
            len(messages),
        )
        return messages[:max_posts]

    def parse(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Parse a single Telegram message into SocialPost fields.

        Maps the extracted message dict to the standard SocialPost
        column structure.
        """
        message_id = str(raw_data.get("id", ""))
        text = raw_data.get("text", "")
        views = _safe_int(raw_data.get("views", 0))

        published_at = raw_data.get("published_at", datetime.now(UTC))
        if isinstance(published_at, str):
            try:
                published_at = datetime.fromisoformat(
                    published_at.replace("Z", "+00:00")
                )
            except (TypeError, ValueError):
                published_at = datetime.now(UTC)

        post_type = raw_data.get("post_type", PostType.TEXT.value)

        return {
            "platform_post_id": f"tg_{message_id}",
            "content": text[:10_000],
            "post_type": post_type,
            "published_at": published_at,
            "likes": 0,  # Not available on public preview page.
            "comments": 0,  # Not available on public preview page.
            "shares": 0,  # Not available on public preview page.
            "views": views,
            "raw_data": {
                "post_id": raw_data.get("post_id"),
                "message_id": message_id,
                "views_raw": raw_data.get("views"),
            },
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
                "Starting Telegram scrape for profile_id=%d channel=%s",
                profile_id,
                handle,
            )

            # 1. Fetch messages.
            raw_messages = self.fetch_raw(handle)
            if not raw_messages:
                logger.warning("No messages returned for channel %s", handle)

            # 2. Parse and dedup.
            for raw in raw_messages:
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
                    # Update view count (only metric available).
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
            "Telegram scrape complete: profile_id=%d new_posts=%d errors=%d",
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
        """Extract channel statistics from the public preview page.

        The t.me/s/ page includes subscriber count in the channel info
        header.  Post count is estimated from the number of messages
        visible on the page.
        """
        empty: dict[str, int] = {
            "followers_count": 0,
            "following_count": 0,
            "posts_count": 0,
        }

        html = self._fetch_channel_page(handle)
        if not html:
            return empty

        # Subscriber count: <div class="tgme_channel_info_counter">
        # or in the description area.
        subscribers = 0
        counter_match = re.search(
            r'class="tgme_channel_info_counter[^"]*"[^>]*>'
            r'.*?<span[^>]*class="counter_value"[^>]*>([\d\s,.KkMm]+)</span>'
            r'.*?<span[^>]*class="counter_type"[^>]*>(subscribers?|members?)',
            html,
            re.DOTALL | re.IGNORECASE,
        )
        if counter_match:
            subscribers = _parse_subscriber_count(
                counter_match.group(1) + " subscribers"
            )
        else:
            # Fallback: look for "N subscribers" anywhere in the page header.
            fallback = re.search(
                r'([\d\s,.]+[KkMm]?)\s*(?:subscribers?|members?)',
                html[:5000],
                re.IGNORECASE,
            )
            if fallback:
                subscribers = _parse_subscriber_count(fallback.group(0))

        return {
            "followers_count": subscribers,
            "following_count": 0,  # Not applicable for channels.
            "posts_count": 0,  # Would need full history to count.
        }
