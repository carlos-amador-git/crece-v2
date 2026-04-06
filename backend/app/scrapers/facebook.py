"""Facebook scraper — Playwright (primary) + facebook-page-info-scraper (fallback).

The previous implementation used ``kevinzg/facebook-scraper`` which returns 0
results as of 2026 even with cookies.  This rewrite uses:

1. **Primary**: Playwright with session cookies (``c_user`` + ``xs``) to render
   the Facebook page in a headless Chromium browser and extract post text from
   the rendered DOM.
2. **Fallback**: ``facebook-page-info-scraper`` for metadata-only scraping
   (followers, page name) when Playwright is unavailable or fails.

Configuration (env vars / ``.env``):
    FACEBOOK_C_USER   — ``c_user`` cookie value from an authenticated session
    FACEBOOK_XS       — ``xs`` cookie value from an authenticated session
"""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.social import PostType, SocialPost, SocialProfile
from app.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────
_PAGE_LOAD_TIMEOUT_MS = 30_000
_SCROLL_PAUSE_MS = 3_000
_MAX_SCROLLS = 8
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# Regex to extract follower counts from page text.
# Matches patterns like "12K followers", "1.2M seguidores", "3,456 followers"
_FOLLOWERS_RE = re.compile(
    r"([\d,.]+)\s*(?:(mil|thousand|[KMkm]))?\s*(?:followers|seguidores|likes|me gusta)",
    re.IGNORECASE,
)

# Regex to detect relative timestamps Facebook uses for posts.
_TIME_PATTERNS = re.compile(
    r"\b(\d+)\s*(?:h|hr|hrs|hour|hours|min|m|mins|minutes|d|day|days|w|wk|week|weeks)\b",
    re.IGNORECASE,
)

# Separator heuristic: Facebook inserts the page name before each post.
# We split the body text by lines that look like a page name repeated.
_POST_SEPARATOR_MIN_LEN = 20


class FacebookScraper(BaseScraper):
    """Facebook scraper using Playwright + cookies (primary) with
    facebook-page-info-scraper fallback for metadata.

    Runs synchronously — designed for Celery worker context.
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
        """Scrape posts from a Facebook page.

        Strategy (3 tiers):
        1. curl-cffi with Chrome TLS impersonation + cookies (fast, no browser)
        2. Playwright with cookies (slower, opens headless browser)
        3. Empty list if both fail
        """
        if not self._has_cookies():
            logger.warning(
                "Facebook cookies not configured (FACEBOOK_C_USER / FACEBOOK_XS)."
            )
            return []

        # ── Tier 1: curl-cffi (fast, no browser) ──────────────────
        posts = self._fetch_with_curl_cffi(handle)
        if posts:
            return posts

        # ── Tier 2: Playwright (slow, opens browser) ──────────────
        logger.info("curl-cffi returned 0 posts, falling back to Playwright")
        posts = self._fetch_with_playwright(handle)
        return posts

    def _fetch_with_curl_cffi(self, handle: str) -> list[dict[str, Any]]:
        """Tier 1: Use curl-cffi to fetch Facebook page HTML with Chrome TLS
        fingerprint, then extract posts from embedded JSON."""
        try:
            from curl_cffi import requests as cffi_requests
        except ImportError:
            logger.debug("curl-cffi not installed — skipping tier 1")
            return []

        url = f"https://www.facebook.com/{handle}"
        cookies = {
            "c_user": settings.FACEBOOK_C_USER,
            "xs": settings.FACEBOOK_XS,
        }

        try:
            resp = cffi_requests.get(
                url,
                cookies=cookies,
                impersonate="chrome",
                timeout=30,
                allow_redirects=True,
            )

            if resp.status_code != 200 or "login" in resp.url.lower():
                logger.warning("curl-cffi Facebook request failed: status=%d url=%s", resp.status_code, resp.url[:80])
                return []

            html = resp.text
            if len(html) < 5000:
                logger.warning("curl-cffi response too short (%d chars)", len(html))
                return []

            posts = _extract_posts_from_html_json(html, handle)
            logger.info("curl-cffi extracted %d posts for handle=%s", len(posts), handle)
            return posts

        except Exception as exc:
            logger.warning("curl-cffi Facebook scrape failed for %s: %s", handle, exc)
            return []

    def _fetch_with_playwright(self, handle: str) -> list[dict[str, Any]]:
        """Tier 2: Use Playwright headless browser with cookies."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("playwright is not installed")
            return []

        url = f"https://www.facebook.com/{handle}"
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                try:
                    context = browser.new_context(
                        user_agent=_USER_AGENT,
                        viewport={"width": 1280, "height": 900},
                        locale="es-MX",
                    )
                    context.add_cookies(self._build_cookies())
                    page = context.new_page()
                    page.goto(url, wait_until="networkidle", timeout=_PAGE_LOAD_TIMEOUT_MS)

                    for _ in range(_MAX_SCROLLS):
                        page.evaluate("window.scrollBy(0, window.innerHeight)")
                        page.wait_for_timeout(_SCROLL_PAUSE_MS)

                    body_text = page.inner_text("body")
                    context.close()
                finally:
                    browser.close()

            page_name = _extract_page_name_from_body(body_text, handle)
            posts = _parse_body_into_posts(body_text, page_name, handle)
            logger.info("Playwright extracted %d posts for handle=%s", len(posts), handle)
            return posts

        except Exception as exc:
            logger.error("Playwright scrape failed for %s: %s", handle, exc)
            return []

    def parse(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Normalise a single parsed post dict into SocialPost fields."""
        content = (raw_data.get("text") or "").strip()

        # Determine post type from content hints.
        post_type = PostType.TEXT
        text_lower = content.lower()
        if any(kw in text_lower for kw in ("video", "reel", "en vivo", "live")):
            post_type = PostType.VIDEO
        elif any(kw in text_lower for kw in ("foto", "photo", "image", "imagen")):
            post_type = PostType.IMAGE

        published_at = raw_data.get("published_at") or datetime.now(UTC)
        if isinstance(published_at, datetime) and published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=UTC)

        return {
            "platform_post_id": raw_data.get("post_id", ""),
            "content": content[:10_000],
            "post_type": post_type.value,
            "published_at": published_at,
            "likes": _safe_int(raw_data.get("likes", 0)),
            "comments": _safe_int(raw_data.get("comments", 0)),
            "shares": _safe_int(raw_data.get("shares", 0)),
            "views": 0,
            "raw_data": {
                "source": "playwright",
                "handle": raw_data.get("handle", ""),
                "scraped_at": datetime.now(UTC).isoformat(),
            },
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
            logger.info(
                "Starting Facebook scrape for profile_id=%d handle=%s",
                profile_id,
                handle,
            )

            # 1. Fetch raw posts via Playwright.
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

            # 4. Update profile stats (tries Playwright page text, then fallback).
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
        """Extract page-level stats.

        Strategy:
        1. Try curl-cffi to extract follower_count from embedded JSON.
        2. Try ``facebook-page-info-scraper`` (no auth required, metadata only).
        3. Try Playwright page text regex as last resort.
        """
        # Strategy 1: curl-cffi JSON extraction (fast).
        if self._has_cookies():
            stats = self._stats_from_curl_cffi(handle)
            if stats.get("followers_count", 0) > 0:
                return stats

        # Strategy 2: facebook-page-info-scraper (no auth needed).
        stats = self._stats_from_page_info_scraper(handle)
        if stats.get("followers_count", 0) > 0:
            return stats

        # Strategy 3: Playwright (slow).
        stats = self._stats_from_playwright(handle)
        if stats.get("followers_count", 0) > 0:
            return stats

        return {"followers_count": 0, "following_count": 0, "posts_count": 0}

    def _stats_from_curl_cffi(self, handle: str) -> dict[str, int]:
        """Extract follower count from Facebook HTML via curl-cffi."""
        try:
            from curl_cffi import requests as cffi_requests
        except ImportError:
            return {"followers_count": 0, "following_count": 0, "posts_count": 0}

        try:
            resp = cffi_requests.get(
                f"https://www.facebook.com/{handle}",
                cookies={"c_user": settings.FACEBOOK_C_USER, "xs": settings.FACEBOOK_XS},
                impersonate="chrome",
                timeout=20,
            )
            if resp.status_code != 200 or "login" in resp.url.lower():
                return {"followers_count": 0, "following_count": 0, "posts_count": 0}

            html = resp.text
            # Try JSON patterns for follower count
            for pattern in [
                r'"normal_followers_count":(\d+)',
                r'"followers_count":(\d+)',
                r'"follower_count":(\d+)',
            ]:
                m = re.search(pattern, html)
                if m:
                    return {
                        "followers_count": int(m.group(1)),
                        "following_count": 0,
                        "posts_count": 0,
                    }

            return {"followers_count": 0, "following_count": 0, "posts_count": 0}
        except Exception as exc:
            logger.warning("curl-cffi stats failed for %s: %s", handle, exc)
            return {"followers_count": 0, "following_count": 0, "posts_count": 0}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _has_cookies(self) -> bool:
        """Check whether Facebook session cookies are configured."""
        return bool(settings.FACEBOOK_C_USER and settings.FACEBOOK_XS)

    def _build_cookies(self) -> list[dict[str, str]]:
        """Build Playwright cookie dicts from settings."""
        return [
            {
                "name": "c_user",
                "value": settings.FACEBOOK_C_USER,
                "domain": ".facebook.com",
                "path": "/",
            },
            {
                "name": "xs",
                "value": settings.FACEBOOK_XS,
                "domain": ".facebook.com",
                "path": "/",
            },
        ]

    def _stats_from_page_info_scraper(self, handle: str) -> dict[str, int]:
        """Attempt metadata extraction via facebook-page-info-scraper."""
        try:
            from facebook_page_info_scraper import FacebookPageInfoScraper
        except ImportError:
            logger.debug(
                "facebook-page-info-scraper not installed — skipping metadata fallback"
            )
            return {"followers_count": 0, "following_count": 0, "posts_count": 0}

        try:
            url = f"https://www.facebook.com/{handle}"
            scraper = FacebookPageInfoScraper(url)
            data = scraper.get_page_info()

            followers = 0
            if isinstance(data, dict):
                # The library returns various key names depending on page type.
                for key in ("page_followers", "followers", "page_likes", "likes"):
                    raw_val = data.get(key)
                    if raw_val:
                        followers = _parse_human_number(str(raw_val))
                        if followers > 0:
                            break

            logger.info(
                "facebook-page-info-scraper for %s: followers=%d",
                handle,
                followers,
            )
            return {
                "followers_count": followers,
                "following_count": 0,
                "posts_count": 0,
            }

        except Exception as exc:
            logger.warning(
                "facebook-page-info-scraper failed for %s: %s", handle, exc
            )
            return {"followers_count": 0, "following_count": 0, "posts_count": 0}

    def _stats_from_playwright(self, handle: str) -> dict[str, int]:
        """Quick Playwright page load to regex-extract follower count."""
        if not self._has_cookies():
            return {"followers_count": 0, "following_count": 0, "posts_count": 0}

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return {"followers_count": 0, "following_count": 0, "posts_count": 0}

        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                try:
                    context = browser.new_context(
                        user_agent=_USER_AGENT,
                        locale="es-MX",
                    )
                    context.add_cookies(self._build_cookies())
                    page = context.new_page()
                    page.goto(
                        f"https://www.facebook.com/{handle}",
                        wait_until="networkidle",
                        timeout=_PAGE_LOAD_TIMEOUT_MS,
                    )
                    body_text = page.inner_text("body")
                    context.close()
                finally:
                    browser.close()

            followers = _extract_followers_from_text(body_text)
            return {
                "followers_count": followers,
                "following_count": 0,
                "posts_count": 0,
            }

        except Exception as exc:
            logger.warning(
                "Playwright stats extraction failed for %s: %s", handle, exc
            )
            return {"followers_count": 0, "following_count": 0, "posts_count": 0}


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------


def _safe_int(value: Any) -> int:
    """Coerce a value to int, returning 0 on failure."""
    if value is None:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _parse_human_number(text: str) -> int:
    """Parse a human-readable number like '12K', '1.2M', '6.1 thousand', '6,1 mil'."""
    text = text.strip().replace(",", ".")  # Normalize decimal separator

    match = re.match(r"^([\d.]+)\s*(thousand|mil|[KMBkmb])?\s*$", text, re.IGNORECASE)
    if not match:
        # Try stripping all non-numeric except dots
        clean = re.sub(r"[^\d.]", "", text)
        return _safe_int(clean) if clean else 0

    number = float(match.group(1))
    suffix = (match.group(2) or "").lower()
    multipliers = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000, "mil": 1_000, "thousand": 1_000}
    return int(number * multipliers.get(suffix, 1))


def _extract_page_name(page_title: str, handle: str) -> str:
    """Derive the page display name from the browser title.

    Facebook titles are typically ``PageName | Facebook`` or
    ``PageName - Home | Facebook``.
    """
    if "|" in page_title:
        return page_title.split("|")[0].strip().rstrip(" - Home").strip()
    if "-" in page_title:
        return page_title.split("-")[0].strip()
    return handle


def _extract_posts_from_html_json(html: str, handle: str) -> list[dict[str, Any]]:
    """Extract posts from Facebook's embedded JSON in the HTML response.

    Facebook embeds GraphQL data as JSON inside <script> tags and inline
    JS. We regex-extract post messages, reaction counts, and share counts.
    """
    posts: list[dict[str, Any]] = []
    seen: set[str] = set()

    # Extract post texts
    messages = re.findall(r'"message":\{"text":"([^"]+)"', html)
    reactions = re.findall(r'"reaction_count":\{"count":(\d+)', html)
    shares = re.findall(r'"share_count":\{"count":(\d+)', html)
    comment_counts = re.findall(r'"comment_count":\{"total_count":(\d+)', html)

    # Extract creation times (unix timestamps)
    creation_times = re.findall(r'"creation_time":(\d{10})', html)

    for i, msg in enumerate(messages):
        # Decode unicode escapes safely (Facebook uses \uXXXX + surrogate pairs)
        try:
            text = msg.encode("utf-8").decode("unicode_escape", errors="surrogateescape")
            # Re-encode to handle surrogate pairs (emoji)
            text = text.encode("utf-16", "surrogatepass").decode("utf-16", errors="replace")
        except Exception:
            text = msg.replace(r"\n", "\n").replace(r"\u00f1", "ñ")

        # Deduplicate
        text_hash = hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]
        if text_hash in seen:
            continue
        seen.add(text_hash)

        likes = _safe_int(reactions[i]) if i < len(reactions) else 0
        share_count = _safe_int(shares[i]) if i < len(shares) else 0
        comment_count = _safe_int(comment_counts[i]) if i < len(comment_counts) else 0
        created = None
        if i < len(creation_times):
            try:
                created = datetime.fromtimestamp(int(creation_times[i]), tz=UTC)
            except (ValueError, OSError):
                pass

        posts.append({
            "post_id": f"fb_{handle}_{text_hash}",
            "text": text,
            "handle": handle,
            "published_at": created or datetime.now(UTC),
            "likes": likes,
            "comments": comment_count,
            "shares": share_count,
            "_source": "curl_cffi",
        })

    return posts


def _extract_page_name_from_body(body_text: str, handle: str) -> str:
    """Extract page display name from the first few lines of body text.

    Facebook pages show the page name near the top, followed by follower count.
    Pattern: line with a name, then "X seguidores" or "X followers".
    """
    lines = [l.strip() for l in body_text.split("\n") if l.strip() and l.strip() != "Facebook"]
    for i, line in enumerate(lines):
        if i + 1 < len(lines) and re.search(r"seguidores|followers", lines[i + 1], re.IGNORECASE):
            # This line is likely the page name
            if len(line) > 2 and line[0].isupper():
                return line
    return handle


def _extract_followers_from_text(text: str) -> int:
    """Regex-extract follower count from rendered page text."""
    match = _FOLLOWERS_RE.search(text)
    if not match:
        return 0

    number_str = match.group(1).replace(",", "")
    suffix = (match.group(2) or "").upper()

    try:
        base = float(number_str)
    except ValueError:
        return 0

    multipliers = {"K": 1_000, "M": 1_000_000, "MIL": 1_000, "THOUSAND": 1_000}
    return int(base * multipliers.get(suffix, 1))


def _parse_body_into_posts(
    body_text: str,
    page_name: str,
    handle: str,
) -> list[dict[str, Any]]:
    """Split rendered Facebook page body text into individual post dicts.

    Facebook's rendered DOM produces text where each post starts with the
    page name (sometimes followed by context like "está con X" or
    "agregó un video nuevo") and a date line.  Between posts there are
    repeated "Facebook" lines (React placeholders).

    Strategy:
    1. Pre-clean: remove noise lines ("Facebook", nav chrome).
    2. Split on lines that START with the page name.
    3. Extract date, content, and engagement from each chunk.
    """
    if not body_text or not body_text.strip():
        return []

    lines = body_text.split("\n")
    name_lower = page_name.strip().lower()

    # ── Phase 1: Pre-clean lines ──────────────────────────────
    cleaned_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Skip bare "Facebook" separators
        if stripped == "Facebook":
            continue
        # Skip single-char lines (React artifacts like "n", "t", "e")
        if len(stripped) <= 2:
            continue
        cleaned_lines.append(stripped)

    # ── Phase 2: Find post boundaries ─────────────────────────
    # A post starts when a line begins with the page name AND is followed
    # by a date-like line (e.g. "3 de octubre de 2025", "31 de marzo a las")
    _DATE_RE = re.compile(
        r"^\d{1,2}\s+de\s+\w+|"          # "3 de octubre de 2025"
        r"^(?:ayer|hoy|hace)|"            # "ayer", "hoy", "hace 2 h"
        r"^\d+\s+de\s+\w+\s+de\s+\d{4}|" # full date
        r"^\d+\s+de\s+\w+\s+a\s+las|"    # "31 de marzo a las 6:09"
        r"^\d+\s*(?:día|dias|hora|horas|min|semana|sem)|"  # "1 día", "2 horas"
        r"^\d+\s*[dhmsw]\b",             # "1d", "2h", "3m"
        re.IGNORECASE,
    )

    post_starts: list[int] = []
    for i, line in enumerate(cleaned_lines):
        if line.lower().startswith(name_lower):
            # Check if next non-empty line looks like a date
            for j in range(i + 1, min(i + 3, len(cleaned_lines))):
                if _DATE_RE.match(cleaned_lines[j]):
                    post_starts.append(i)
                    break

    # ── Phase 3: Extract posts from chunks ────────────────────
    posts: list[dict[str, Any]] = []
    seen_hashes: set[str] = set()

    for idx, start in enumerate(post_starts):
        end = post_starts[idx + 1] if idx + 1 < len(post_starts) else len(cleaned_lines)
        chunk_lines = cleaned_lines[start:end]

        # Skip the page name line itself
        content_lines = chunk_lines[1:]

        # Try to extract the date from the first line after the page name
        date_line = content_lines[0] if content_lines else ""
        if _DATE_RE.match(date_line):
            content_lines = content_lines[1:]  # skip date line from content

        # Skip lines after "Publicaciones", "Filtros" (section headers)
        content_text = []
        for cl in content_lines:
            if cl in ("Publicaciones", "Filtros", "Destacados", "Ver más", "See more"):
                break
            content_text.append(cl)

        raw_text = "\n".join(content_text).strip()
        if len(raw_text) < 10:
            continue

        # Extract engagement (look for standalone numbers at end: likes, comments, shares)
        likes, comments, shares = _extract_engagement(raw_text)
        clean_text = _clean_post_text(raw_text)
        if len(clean_text) < 10:
            continue

        content_hash = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()[:16]
        if content_hash in seen_hashes:
            continue
        seen_hashes.add(content_hash)

        post_id = f"fb_{handle}_{content_hash}"
        posts.append({
            "post_id": post_id,
            "text": clean_text,
            "handle": handle,
            "published_at": datetime.now(UTC),
            "likes": likes,
            "comments": comments,
            "shares": shares,
        })

    return posts


def _is_navigation_text(text: str) -> bool:
    """Return True if the text chunk looks like Facebook navigation/UI chrome."""
    nav_indicators = [
        "log in",
        "sign up",
        "create new account",
        "forgot password",
        "privacy policy",
        "terms of service",
        "cookie policy",
        "iniciar sesión",
        "crear cuenta nueva",
        "política de privacidad",
    ]
    text_lower = text.lower()
    matches = sum(1 for indicator in nav_indicators if indicator in text_lower)
    return matches >= 2


def _extract_engagement(text: str) -> tuple[int, int, int]:
    """Extract likes, comments, shares from engagement summary lines.

    Facebook renders engagement as lines like:
        "👍 ❤️ 42"
        "15 comments"
        "3 shares"
    or in Spanish:
        "15 comentarios"
        "3 veces compartido"
    """
    likes = 0
    comments = 0
    shares = 0

    # Likes: a line with reaction emojis followed by a number, or "N likes"
    likes_match = re.search(
        r"(?:👍|❤️|😂|😮|😢|😡)\s*(\d[\d,.]*)|(\d[\d,.]*)\s*(?:likes?|me gusta)",
        text,
        re.IGNORECASE,
    )
    if likes_match:
        likes = _safe_int((likes_match.group(1) or likes_match.group(2) or "0").replace(",", ""))

    # Comments
    comments_match = re.search(
        r"(\d[\d,.]*)\s*(?:comments?|comentarios?)",
        text,
        re.IGNORECASE,
    )
    if comments_match:
        comments = _safe_int(comments_match.group(1).replace(",", ""))

    # Shares
    shares_match = re.search(
        r"(\d[\d,.]*)\s*(?:shares?|veces compartido|compartido)",
        text,
        re.IGNORECASE,
    )
    if shares_match:
        shares = _safe_int(shares_match.group(1).replace(",", ""))

    return likes, comments, shares


def _clean_post_text(text: str) -> str:
    """Remove engagement summary lines and UI artifacts from post text."""
    lines = text.split("\n")
    cleaned: list[str] = []

    # Patterns to skip (engagement lines, action buttons).
    skip_patterns = re.compile(
        r"^(?:like|comment|share|compartir|comentar|me gusta|"
        r"👍|❤️|😂|😮|😢|😡|"
        r"\d+\s*(?:comments?|comentarios?|shares?|likes?|me gusta|veces compartido)|"
        r"all comments?|todos los comentarios|"
        r"most relevant|más relevantes|"
        r"write a comment|escribe un comentario|"
        r"see more|ver más)\s*$",
        re.IGNORECASE,
    )

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if skip_patterns.match(stripped):
            continue
        # Skip very short lines that are just numbers (reaction counts).
        if re.match(r"^\d{1,6}$", stripped):
            continue
        cleaned.append(stripped)

    return "\n".join(cleaned).strip()
