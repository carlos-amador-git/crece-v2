"""Tests S3 · YouTubePrivilegedScraper (PLAN-2026-05-13).

Cubre:
- Constructor rechaza tokens stub.
- Constructor rechaza tokens de otra plataforma.
- ``upsert_subscribers`` escribe filas correctas en social_followers.
- ``record_comment_engagements`` solo crea engagement si autor está en
  social_followers Y video_id mapea a post conocido.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dirigente import Dirigente
from app.models.follower import FollowerEngagement, SocialFollower
from app.models.oauth_token import OAuthTokenByPlatform
from app.models.social import Platform, PostType, SocialPost, SocialProfile
from app.scrapers.youtube_privileged import (
    YouTubePrivilegedScraper,
    YouTubePrivilegedScraperError,
)


async def _seed_dirigente_with_token(
    db: AsyncSession, *, is_stub: bool = False, expired: bool = False
) -> tuple[Dirigente, OAuthTokenByPlatform]:
    d = Dirigente(full_name="Piña", cargo="Diputado", partido="MC", estado="CDMX")
    db.add(d)
    await db.commit()
    await db.refresh(d)
    expires = datetime.now(UTC) + (
        timedelta(seconds=-60) if expired else timedelta(hours=1)
    )
    token = OAuthTokenByPlatform(
        dirigente_id=d.id,
        platform="youtube",
        token_hash="ya29.fake",
        refresh_token_hash="1//fake",
        is_stub=is_stub,
        status="active",
        scopes=["youtube.readonly"],
        expires_at=expires,
    )
    db.add(token)
    await db.commit()
    await db.refresh(token)
    return d, token


@pytest.mark.asyncio
async def test_rejects_stub_token(db_session: AsyncSession) -> None:
    _, tok = await _seed_dirigente_with_token(db_session, is_stub=True)
    with pytest.raises(YouTubePrivilegedScraperError, match="stub"):
        YouTubePrivilegedScraper(tok)


@pytest.mark.asyncio
async def test_rejects_wrong_platform(db_session: AsyncSession) -> None:
    _, tok = await _seed_dirigente_with_token(db_session)
    tok.platform = "tiktok"
    with pytest.raises(ValueError, match="platform"):
        YouTubePrivilegedScraper(tok)


@pytest.mark.asyncio
async def test_upsert_subscribers(db_session: AsyncSession) -> None:
    _, tok = await _seed_dirigente_with_token(db_session)
    scraper = YouTubePrivilegedScraper(tok)

    response = {
        "items": [
            {
                "subscriberSnippet": {
                    "channelId": "UC_abc123",
                    "title": "Juan Pueblo",
                    "thumbnails": {"default": {"url": "https://yt.example/avatar.jpg"}},
                }
            },
            {
                "subscriberSnippet": {
                    "channelId": "UC_xyz789",
                    "title": "Maria Ciudad",
                    "thumbnails": {"default": {"url": "https://yt.example/m.jpg"}},
                }
            },
        ]
    }
    n = await scraper.upsert_subscribers(db_session, response)
    assert n == 2

    rows = (await db_session.execute(select(SocialFollower))).scalars().all()
    assert len(rows) == 2
    assert {r.follower_external_id for r in rows} == {"UC_abc123", "UC_xyz789"}
    assert all(r.source == "oauth" for r in rows)
    assert all(r.platform == "youtube" for r in rows)

    # Re-upsert: actualiza last_seen_at sin crear filas nuevas
    n2 = await scraper.upsert_subscribers(db_session, response)
    assert n2 == 2  # operación lógica
    rows_after = (await db_session.execute(select(SocialFollower))).scalars().all()
    assert len(rows_after) == 2


@pytest.mark.asyncio
async def test_record_comment_engagements_filters_unknown_authors(
    db_session: AsyncSession,
) -> None:
    d, tok = await _seed_dirigente_with_token(db_session)
    scraper = YouTubePrivilegedScraper(tok)

    # Seed 1 follower y 1 post conocidos
    follower = SocialFollower(
        dirigente_id=d.id,
        platform="youtube",
        follower_external_id="UC_known",
        follower_handle="known",
        source="oauth",
    )
    profile = SocialProfile(
        dirigente_id=d.id,
        platform=Platform.YOUTUBE,
        handle="@channel",
        url="https://youtube.com/@channel",
        followers_count=0,
    )
    db_session.add_all([follower, profile])
    await db_session.commit()
    await db_session.refresh(profile)
    post = SocialPost(
        profile_id=profile.id,
        platform_post_id="video-1",
        post_type=PostType.VIDEO,
        published_at=datetime.now(UTC),
    )
    db_session.add(post)
    await db_session.commit()
    await db_session.refresh(post)

    threads = {
        "items": [
            {
                "snippet": {
                    "topLevelComment": {
                        "snippet": {
                            "authorChannelId": {"value": "UC_known"},
                            "videoId": "video-1",
                            "publishedAt": "2026-05-13T01:23:45Z",
                            "textOriginal": "buen video",
                        }
                    }
                }
            },
            {
                # Autor desconocido (no en social_followers) → ignorado
                "snippet": {
                    "topLevelComment": {
                        "snippet": {
                            "authorChannelId": {"value": "UC_unknown"},
                            "videoId": "video-1",
                            "publishedAt": "2026-05-13T01:23:46Z",
                        }
                    }
                }
            },
            {
                # Video desconocido → ignorado
                "snippet": {
                    "topLevelComment": {
                        "snippet": {
                            "authorChannelId": {"value": "UC_known"},
                            "videoId": "video-ghost",
                            "publishedAt": "2026-05-13T01:23:47Z",
                        }
                    }
                }
            },
        ]
    }

    n = await scraper.record_comment_engagements(
        db_session, threads, post_external_to_internal={"video-1": post.id}
    )
    assert n == 1
    engagements = (
        await db_session.execute(select(FollowerEngagement))
    ).scalars().all()
    assert len(engagements) == 1
    assert engagements[0].engagement_type == "comment"
    assert engagements[0].post_id == post.id
