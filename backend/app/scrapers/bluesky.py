"""Bluesky scraper using the AT Protocol public API.

No authentication required. The AT Protocol is fully open and rate-limit-friendly.
Endpoint: https://public.api.bsky.app/xrpc/

As of 2026-04, Bluesky adoption in Mexican politics is minimal. This scraper
is ready for when Movimiento Ciudadano or dirigentes open accounts.
"""

from __future__ import annotations

import contextlib
import logging
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import create_engine, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.social import PostType, SocialPost, SocialProfile
from app.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

_API_BASE = "https://public.api.bsky.app/xrpc"
_TIMEOUT = 30.0
_MAX_POSTS = 50


def _get_sync_session() -> Session:
    engine = create_engine(settings.DATABASE_URL_SYNC, pool_pre_ping=True, pool_size=5)
    return Session(bind=engine, expire_on_commit=False)


class BlueskyScraper(BaseScraper):
    """Bluesky scraper via AT Protocol public API. No auth needed."""

    platform = "bluesky"

    def fetch_raw(self, handle: str, **kwargs: Any) -> list[dict[str, Any]]:
        """Fetch recent posts from a Bluesky profile."""
        handle = handle.strip().lstrip("@")
        limit = kwargs.get("limit", _MAX_POSTS)

        did = self._resolve_did(handle)
        if not did:
            return []

        try:
            with httpx.Client(timeout=_TIMEOUT) as client:
                resp = client.get(
                    f"{_API_BASE}/app.bsky.feed.getAuthorFeed",
                    params={"actor": did, "limit": min(limit, 100)},
                )
                resp.raise_for_status()
                feed = resp.json().get("feed", [])
                logger.info("Bluesky fetched %d posts for @%s", len(feed), handle)
                return [item.get("post", {}) for item in feed]
        except Exception as exc:
            logger.warning("Bluesky feed fetch failed for @%s: %s", handle, exc)
            return []

    def parse(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Parse a Bluesky post into SocialPost fields."""
        record = raw_data.get("record", {})
        uri = raw_data.get("uri", "")
        platform_post_id = uri.split("/")[-1] if uri else ""

        content = record.get("text", "")

        created = record.get("createdAt", "")
        published_at = datetime.now(UTC)
        if created:
            with contextlib.suppress(ValueError, TypeError):
                published_at = datetime.fromisoformat(created.replace("Z", "+00:00"))

        likes = raw_data.get("likeCount", 0)
        reposts = raw_data.get("repostCount", 0)
        replies = raw_data.get("replyCount", 0)

        embed = raw_data.get("embed", {})
        embed_type = embed.get("$type", "") if embed else ""
        post_type = PostType.TEXT
        if "image" in embed_type:
            post_type = PostType.IMAGE
        elif "video" in embed_type:
            post_type = PostType.VIDEO

        return {
            "platform_post_id": platform_post_id,
            "content": content[:10_000],
            "post_type": post_type.value,
            "published_at": published_at,
            "likes": int(likes or 0),
            "comments": int(replies or 0),
            "shares": int(reposts or 0),
            "views": 0,
            "raw_data": {"uri": uri, "cid": raw_data.get("cid", "")},
        }

    def update_profile_stats(self, handle: str) -> dict[str, int]:
        """Fetch Bluesky profile stats."""
        handle = handle.strip().lstrip("@")
        default = {"followers_count": 0, "following_count": 0, "posts_count": 0}

        try:
            with httpx.Client(timeout=_TIMEOUT) as client:
                resp = client.get(
                    f"{_API_BASE}/app.bsky.actor.getProfile",
                    params={"actor": handle},
                )
                if resp.status_code != 200:
                    return default
                data = resp.json()
                return {
                    "followers_count": data.get("followersCount", 0),
                    "following_count": data.get("followsCount", 0),
                    "posts_count": data.get("postsCount", 0),
                }
        except Exception as exc:
            logger.warning("Bluesky profile fetch failed for @%s: %s", handle, exc)
            return default

    def scrape(self, profile_id: int) -> dict[str, Any]:
        """Full scrape pipeline: fetch -> parse -> dedup -> store."""
        errors: list[str] = []
        new_posts = 0
        updated_profile = False

        session = _get_sync_session()
        try:
            profile = session.get(SocialProfile, profile_id)
            if profile is None:
                return {
                    "new_posts": 0,
                    "updated_profile": False,
                    "errors": [f"Profile {profile_id} not found"],
                }

            handle = profile.handle
            raw_posts = self.fetch_raw(handle)

            existing_ids = {
                row[0]
                for row in session.execute(
                    select(SocialPost.platform_post_id).where(SocialPost.profile_id == profile_id)
                ).all()
            }

            for raw in raw_posts:
                try:
                    parsed = self.parse(raw)
                    if not parsed["platform_post_id"] or parsed["platform_post_id"] in existing_ids:
                        continue

                    stmt = (
                        pg_insert(SocialPost)
                        .values(
                            profile_id=profile_id,
                            platform_post_id=parsed["platform_post_id"],
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
                        .on_conflict_do_nothing(index_elements=["platform_post_id"])
                    )
                    result = session.execute(stmt)
                    if result.rowcount and result.rowcount > 0:
                        new_posts += 1
                except Exception as exc:
                    errors.append(f"Parse/store error: {exc}")

            try:
                stats = self.update_profile_stats(handle)
                if stats["followers_count"] > 0:
                    profile.followers_count = stats["followers_count"]
                    profile.following_count = stats["following_count"]
                    profile.posts_count = stats["posts_count"]
                    updated_profile = True
            except Exception as exc:
                errors.append(f"Stats error: {exc}")

            profile.last_scraped_at = datetime.now(UTC)
            session.commit()
        except Exception as exc:
            session.rollback()
            errors.append(f"Pipeline error: {exc}")
        finally:
            session.close()

        return {"new_posts": new_posts, "updated_profile": updated_profile, "errors": errors}

    def _resolve_did(self, handle: str) -> str | None:
        """Resolve a Bluesky handle to a DID."""
        try:
            with httpx.Client(timeout=_TIMEOUT) as client:
                resp = client.get(
                    f"{_API_BASE}/com.atproto.identity.resolveHandle",
                    params={"handle": handle},
                )
                if resp.status_code == 200:
                    return resp.json().get("did")
        except Exception:
            pass
        return None
