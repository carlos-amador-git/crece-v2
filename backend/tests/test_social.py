"""Tests for social media endpoints: posts listing, sentiment timeline, and scrape dispatch."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dirigente import Dirigente
from app.models.social import (
    Platform,
    PostType,
    SentimentLabel,
    SocialPost,
    SocialProfile,
)
from app.models.user import User
from tests.conftest import auth_headers

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _seed_social_data(
    db: AsyncSession,
    post_count: int = 10,
    platform: Platform = Platform.TWITTER,
) -> tuple[Dirigente, SocialProfile]:
    """Create a dirigente with a profile and posts for testing."""
    dirigente = Dirigente(
        full_name="Test Dirigente",
        cargo="Diputado",
        partido="MC",
        estado="CDMX",
    )
    db.add(dirigente)
    await db.flush()

    profile = SocialProfile(
        dirigente_id=dirigente.id,
        platform=platform,
        handle="@test_handle",
        followers_count=5000,
        posts_count=post_count,
    )
    db.add(profile)
    await db.flush()

    now = datetime.now(UTC)
    sentiments = [SentimentLabel.POSITIVE, SentimentLabel.NEGATIVE, SentimentLabel.NEUTRAL]
    for i in range(post_count):
        post = SocialPost(
            profile_id=profile.id,
            platform_post_id=f"tw_{dirigente.id}_{i}",
            content=f"Post content {i}",
            post_type=PostType.TEXT,
            published_at=now - timedelta(days=i),
            likes=50 + i * 10,
            comments=5 + i,
            shares=2 + i,
            views=500 + i * 100,
            engagement_rate=0.03 + i * 0.001,
            sentiment_score=0.3 if i % 3 == 0 else (-0.4 if i % 3 == 1 else 0.0),
            sentiment_label=sentiments[i % 3],
            is_political=i % 2 == 0,
        )
        db.add(post)

    await db.flush()
    await db.refresh(dirigente)
    await db.refresh(profile)
    return dirigente, profile


# ---------------------------------------------------------------------------
# List posts
# ---------------------------------------------------------------------------


async def test_list_posts_unfiltered(
    client: AsyncClient, db_session: AsyncSession, admin_token: str, admin_user: User
) -> None:
    """Without filters, all posts are returned paginated."""
    dirigente, _ = await _seed_social_data(db_session, post_count=5)
    await db_session.commit()

    resp = await client.get(
        "/api/v1/social/posts",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 5
    assert len(body["items"]) == 5


async def test_list_posts_filtered_by_dirigente(
    client: AsyncClient, db_session: AsyncSession, admin_token: str, admin_user: User
) -> None:
    """Filter by dirigente_id returns only that dirigente's posts."""
    d1, _ = await _seed_social_data(db_session, post_count=3)
    # Create a second dirigente with different posts
    d2 = Dirigente(full_name="Other", cargo="Otro", partido="MC", estado="Jalisco")
    db_session.add(d2)
    await db_session.flush()
    p2 = SocialProfile(
        dirigente_id=d2.id, platform=Platform.FACEBOOK, handle="@other", followers_count=100
    )
    db_session.add(p2)
    await db_session.flush()
    post2 = SocialPost(
        profile_id=p2.id,
        platform_post_id="fb_other_1",
        content="Other post",
        post_type=PostType.TEXT,
        published_at=datetime.now(UTC),
        engagement_rate=0.01,
        sentiment_score=0.0,
        sentiment_label=SentimentLabel.NEUTRAL,
    )
    db_session.add(post2)
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/social/posts?dirigente_id={d1.id}",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 3


async def test_list_posts_filtered_by_sentiment(
    client: AsyncClient, db_session: AsyncSession, admin_token: str, admin_user: User
) -> None:
    """Filter by sentiment label."""
    await _seed_social_data(db_session, post_count=9)
    await db_session.commit()

    resp = await client.get(
        "/api/v1/social/posts?sentiment=positive",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    # 9 posts, every 3rd is positive (indices 0, 3, 6) => 3
    assert body["total"] == 3


async def test_list_posts_filtered_by_platform(
    client: AsyncClient, db_session: AsyncSession, admin_token: str, admin_user: User
) -> None:
    """Filter by platform."""
    await _seed_social_data(db_session, post_count=5, platform=Platform.TWITTER)
    await db_session.commit()

    # Twitter posts exist
    resp = await client.get(
        "/api/v1/social/posts?platform=twitter",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 5

    # Instagram posts do not exist
    resp2 = await client.get(
        "/api/v1/social/posts?platform=instagram",
        headers=auth_headers(admin_token),
    )
    assert resp2.json()["total"] == 0


async def test_list_posts_filtered_is_political(
    client: AsyncClient, db_session: AsyncSession, admin_token: str, admin_user: User
) -> None:
    """Filter by is_political boolean."""
    await _seed_social_data(db_session, post_count=10)
    await db_session.commit()

    resp = await client.get(
        "/api/v1/social/posts?is_political=true",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    # Even indices are political (0, 2, 4, 6, 8) => 5
    assert resp.json()["total"] == 5


async def test_list_posts_unauthenticated(client: AsyncClient) -> None:
    """No token => 401."""
    resp = await client.get("/api/v1/social/posts")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Sentiment timeline
# ---------------------------------------------------------------------------


async def test_sentiment_timeline(
    client: AsyncClient, db_session: AsyncSession, admin_token: str, admin_user: User
) -> None:
    """Sentiment timeline groups by day with correct aggregations."""
    dirigente, _ = await _seed_social_data(db_session, post_count=6)
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/social/sentiment-timeline?dirigente_id={dirigente.id}",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    # Each entry has the required keys
    if body:
        point = body[0]
        assert "date" in point
        assert "avg_sentiment" in point
        assert "post_count" in point
        assert "positive_pct" in point
        assert "negative_pct" in point
        assert "neutral_pct" in point


async def test_sentiment_timeline_empty(
    client: AsyncClient, db_session: AsyncSession, admin_token: str, admin_user: User
) -> None:
    """Timeline for a dirigente with no posts returns empty list."""
    dirigente = Dirigente(full_name="Empty", cargo="Test", partido="MC", estado="CDMX")
    db_session.add(dirigente)
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/social/sentiment-timeline?dirigente_id={dirigente.id}",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# Trigger scrape (Celery dispatch -- mocked)
# ---------------------------------------------------------------------------


async def test_trigger_scrape(
    client: AsyncClient, db_session: AsyncSession, admin_token: str, admin_user: User
) -> None:
    """Triggering a scrape dispatches Celery tasks and returns task IDs."""
    dirigente, profile = await _seed_social_data(db_session, post_count=0)
    await db_session.commit()

    mock_task = MagicMock()
    mock_task.id = "fake-task-id-123"

    with patch("app.workers.tasks.scrape_profile") as mock_scrape:
        mock_scrape.delay.return_value = mock_task

        resp = await client.post(
            f"/api/v1/social/scrape/{dirigente.id}",
            headers=auth_headers(admin_token),
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "dispatched"
    assert isinstance(body["tasks"], dict)
    assert "twitter" in body["tasks"]


async def test_trigger_scrape_no_profiles(
    client: AsyncClient, db_session: AsyncSession, admin_token: str, admin_user: User
) -> None:
    """Scraping a dirigente with no profiles returns 404."""
    dirigente = Dirigente(full_name="NoProfils", cargo="Test", partido="MC", estado="CDMX")
    db_session.add(dirigente)
    await db_session.commit()

    with patch("app.workers.tasks.scrape_profile"):
        resp = await client.post(
            f"/api/v1/social/scrape/{dirigente.id}",
            headers=auth_headers(admin_token),
        )

    assert resp.status_code == 404
    assert "No social profiles" in resp.json()["detail"]


async def test_trigger_scrape_viewer_forbidden(
    client: AsyncClient,
    db_session: AsyncSession,
    viewer_token: str,
    viewer_user: User,
) -> None:
    """Viewers cannot trigger scrapes."""
    dirigente = Dirigente(full_name="Test", cargo="Test", partido="MC", estado="CDMX")
    db_session.add(dirigente)
    await db_session.commit()

    resp = await client.post(
        f"/api/v1/social/scrape/{dirigente.id}",
        headers=auth_headers(viewer_token),
    )
    assert resp.status_code == 403
