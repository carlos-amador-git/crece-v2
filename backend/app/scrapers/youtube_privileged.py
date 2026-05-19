"""Scraper privilegiado YouTube · usa OAuth token de dirigente (S3 PLAN-2026-05-13).

A diferencia de ``YouTubeScraper`` (no autenticado, basado en yt-dlp/scrapetube
sobre canal público), este scraper opera con **OAuth token del propio dirigente**
y accede a endpoints privilegiados de la YouTube Data API v3:

- ``subscriptions.list?mySubscribers=true`` — devuelve suscriptores que han
  hecho opt-in para ser visibles. **No es la lista completa** — YouTube
  oculta por defecto los suscriptores; típicamente ≤10% son visibles.
- ``commentThreads.list?allThreadsRelatedToChannelId=...`` — comentarios
  recientes en cualquier video del canal.

El scraper escribe a ``social_followers`` (UPSERT por
``dirigente_id × platform × follower_external_id``) y a ``follower_engagement``
(UPSERT por la unique constraint definida en S1).

NO se ejecuta E2E real hasta que CEO complete GCP setup
(B-OAUTH-YT-GCP-1) y haya al menos un dirigente con
``OAuthTokenByPlatform.is_stub=False`` para YouTube. Mientras tanto, los
tests con httpx mock validan el contrato de inserción.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.follower import FollowerEngagement, SocialFollower
from app.models.oauth_token import OAuthTokenByPlatform
from app.services.bot_detection import score_follower
from app.services.onboarding import youtube_oauth_real

logger = logging.getLogger(__name__)

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


class YouTubePrivilegedScraperError(RuntimeError):
    """Falla al consumir API privilegiada YouTube (token, cuota, etc.)."""


class YouTubePrivilegedScraper:
    """Scraper privilegiado que consume YouTube Data API v3 con OAuth token."""

    def __init__(self, oauth_token: OAuthTokenByPlatform):
        if oauth_token.platform != "youtube":
            raise ValueError(
                f"Token platform es '{oauth_token.platform}', se esperaba 'youtube'"
            )
        if oauth_token.is_stub:
            raise YouTubePrivilegedScraperError(
                "Cannot scrape: token is stub · dirigente no ha completado OAuth real"
            )
        if not oauth_token.token_hash:
            raise YouTubePrivilegedScraperError(
                "Cannot scrape: token sin access_token persistido"
            )
        self._token = oauth_token

    def _is_expired(self) -> bool:
        if self._token.expires_at is None:
            return False
        return datetime.now(UTC) >= self._token.expires_at

    async def _ensure_fresh_token(
        self, db: AsyncSession, client: httpx.AsyncClient | None = None
    ) -> str:
        """Si expiró, refresca usando refresh_token y persiste el nuevo access."""
        if not self._is_expired():
            return self._token.token_hash  # type: ignore[return-value]
        if not self._token.refresh_token_hash:
            raise YouTubePrivilegedScraperError(
                "Token expirado y sin refresh_token · dirigente debe reconectar"
            )
        new_tokens = await youtube_oauth_real.refresh_access_token(
            self._token.refresh_token_hash, client=client
        )
        self._token.token_hash = new_tokens["access_token"]
        expires_in = int(new_tokens.get("expires_in") or 3600)
        from datetime import timedelta

        self._token.expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)
        self._token.last_refreshed_at = datetime.now(UTC)
        await db.commit()
        return self._token.token_hash

    async def _api_get(
        self,
        path: str,
        params: dict[str, Any],
        client: httpx.AsyncClient,
    ) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self._token.token_hash}"}
        resp = await client.get(
            f"{YOUTUBE_API_BASE}/{path}", params=params, headers=headers
        )
        if resp.status_code == 401:
            raise YouTubePrivilegedScraperError(
                "401 · token rechazado · marcar status='refresh_failed'"
            )
        if resp.status_code != 200:
            raise YouTubePrivilegedScraperError(
                f"YouTube API {path} → {resp.status_code}: {resp.text[:200]}"
            )
        return resp.json()

    async def list_my_subscribers(
        self, *, client: httpx.AsyncClient, page_token: str | None = None
    ) -> dict[str, Any]:
        """``subscriptions.list?mySubscribers=true`` paginado."""
        params: dict[str, Any] = {
            "part": "subscriberSnippet",
            "mySubscribers": "true",
            "maxResults": 50,
        }
        if page_token:
            params["pageToken"] = page_token
        return await self._api_get("subscriptions", params, client)

    async def list_recent_comment_threads(
        self,
        *,
        channel_id: str,
        client: httpx.AsyncClient,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        """``commentThreads.list`` de cualquier video del canal."""
        params: dict[str, Any] = {
            "part": "snippet",
            "allThreadsRelatedToChannelId": channel_id,
            "maxResults": 100,
        }
        if page_token:
            params["pageToken"] = page_token
        return await self._api_get("commentThreads", params, client)

    async def upsert_subscribers(
        self, db: AsyncSession, subs_response: dict[str, Any]
    ) -> int:
        """Inserta/actualiza filas en ``social_followers`` desde la lista de subs.

        Retorna número de filas afectadas (insert + update).
        """
        items = subs_response.get("items") or []
        if not items:
            return 0

        rows = []
        now = datetime.now(UTC)
        for it in items:
            snip = (it.get("subscriberSnippet") or {})
            chan = (snip.get("channelId") or "")
            if not chan:
                continue
            title = snip.get("title") or ""
            # B-FOLLOWERS-BOT-1 (2026-05-16): score handle pattern-based.
            # YT subs solo trae title (no profile completo) → score por username solo.
            bot_score, is_real = score_follower(handle=title, platform="youtube")
            rows.append(
                {
                    "dirigente_id": self._token.dirigente_id,
                    "org_id": self._token.org_id,
                    "platform": "youtube",
                    "follower_external_id": chan,
                    "follower_handle": title,
                    "follower_display_name": title,
                    "follower_avatar_url": (
                        snip.get("thumbnails", {}).get("default", {}).get("url")
                    ),
                    "follower_is_verified": False,
                    "is_real": is_real,
                    "bot_score": bot_score,
                    "first_seen_at": now,
                    "last_seen_at": now,
                    "source": "oauth",
                    "raw_data": it,
                }
            )

        if not rows:
            return 0

        stmt = pg_insert(SocialFollower).values(rows)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_followers_dirigente_platform_external",
            set_={
                "follower_handle": stmt.excluded.follower_handle,
                "follower_display_name": stmt.excluded.follower_display_name,
                "follower_avatar_url": stmt.excluded.follower_avatar_url,
                "last_seen_at": stmt.excluded.last_seen_at,
                "raw_data": stmt.excluded.raw_data,
            },
        )
        await db.execute(stmt)
        await db.commit()
        return len(rows)

    async def record_comment_engagements(
        self,
        db: AsyncSession,
        threads_response: dict[str, Any],
        *,
        post_external_to_internal: dict[str, int],
    ) -> int:
        """Inserta ``follower_engagement`` por cada comment thread cuyo
        ``authorChannelId`` exista en social_followers y cuyo videoId mapee a
        un ``social_posts.platform_post_id`` conocido (vía
        ``post_external_to_internal``).

        El cross-reference autor↔follower es lo que hace este scraper más
        valioso que un comment scrape genérico — sabemos QUIÉN del público
        del dirigente comentó.
        """
        items = threads_response.get("items") or []
        if not items:
            return 0

        # 1) Mapa author_channel_id → follower_id (de social_followers)
        author_ids = []
        for it in items:
            snip = ((it.get("snippet") or {}).get("topLevelComment") or {}).get("snippet") or {}
            auth = (snip.get("authorChannelId") or {}).get("value")
            if auth:
                author_ids.append(auth)
        if not author_ids:
            return 0

        followers = (
            await db.execute(
                select(SocialFollower.id, SocialFollower.follower_external_id).where(
                    SocialFollower.dirigente_id == self._token.dirigente_id,
                    SocialFollower.platform == "youtube",
                    SocialFollower.follower_external_id.in_(author_ids),
                )
            )
        ).all()
        author_to_follower = {row.follower_external_id: row.id for row in followers}

        rows = []
        now = datetime.now(UTC)
        for it in items:
            snip = ((it.get("snippet") or {}).get("topLevelComment") or {}).get("snippet") or {}
            auth = (snip.get("authorChannelId") or {}).get("value")
            video_id = snip.get("videoId")
            if not auth or not video_id:
                continue
            follower_id = author_to_follower.get(auth)
            if follower_id is None:
                continue
            post_id = post_external_to_internal.get(video_id)
            if post_id is None:
                continue
            published = snip.get("publishedAt")
            try:
                engaged_at = (
                    datetime.fromisoformat(published.replace("Z", "+00:00"))
                    if published
                    else now
                )
            except ValueError:
                engaged_at = now
            rows.append(
                {
                    "follower_id": follower_id,
                    "post_id": post_id,
                    "engagement_type": "comment",
                    "comment_id": None,
                    "engaged_at": engaged_at,
                    "raw_data": it,
                }
            )

        if not rows:
            return 0

        stmt = pg_insert(FollowerEngagement).values(rows)
        stmt = stmt.on_conflict_do_nothing(
            constraint="uq_engagement_follower_post_type_comment"
        )
        await db.execute(stmt)
        await db.commit()
        return len(rows)
