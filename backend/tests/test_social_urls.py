"""Unit tests for compose_post_url helper (Sprint 23-B Propuesta P1)."""

from __future__ import annotations

from app.models.social import Platform
from app.utils.social_urls import compose_post_url


class TestComposePostUrl:
    def test_twitter_with_handle_builds_x_url(self) -> None:
        url = compose_post_url(Platform.TWITTER, "alejandro_pinha", "1234567890")
        assert url == "https://x.com/alejandro_pinha/status/1234567890"

    def test_instagram_uses_shortcode_without_handle(self) -> None:
        url = compose_post_url(Platform.INSTAGRAM, "alejandro.pinha", "C1a2B3c4D5e")
        assert url == "https://www.instagram.com/p/C1a2B3c4D5e/"

    def test_facebook_composes_with_handle(self) -> None:
        url = compose_post_url(Platform.FACEBOOK, "alejandro.pinha", "posts_123")
        assert url == "https://www.facebook.com/alejandro.pinha/posts/posts_123"

    def test_youtube_uses_video_id(self) -> None:
        url = compose_post_url(Platform.YOUTUBE, None, "dQw4w9WgXcQ")
        assert url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_tiktok_with_handle(self) -> None:
        url = compose_post_url(Platform.TIKTOK, "pinha", "7200000000000000000")
        assert url == "https://www.tiktok.com/@pinha/video/7200000000000000000"

    def test_handle_at_prefix_is_stripped(self) -> None:
        url = compose_post_url(Platform.TWITTER, "@handle", "42")
        assert url == "https://x.com/handle/status/42"

    def test_missing_platform_returns_none(self) -> None:
        assert compose_post_url(None, "x", "1") is None

    def test_missing_post_id_returns_none(self) -> None:
        assert compose_post_url(Platform.TWITTER, "handle", None) is None
        assert compose_post_url(Platform.TWITTER, "handle", "") is None

    def test_missing_handle_for_handle_required_template_returns_none(self) -> None:
        # Twitter template needs {handle} — empty handle should yield None
        assert compose_post_url(Platform.TWITTER, None, "123") is None
        assert compose_post_url(Platform.TWITTER, "", "123") is None
        assert compose_post_url(Platform.TWITTER, "  ", "123") is None

    def test_youtube_works_without_handle(self) -> None:
        # YouTube template has no {handle} placeholder — should succeed
        assert (
            compose_post_url(Platform.YOUTUBE, None, "abc123")
            == "https://www.youtube.com/watch?v=abc123"
        )

    def test_unmapped_platform_returns_none(self) -> None:
        # NEWS is in Platform enum but has no template → graceful degradation
        assert compose_post_url(Platform.NEWS, "domain.com", "article-42") is None

    def test_whitespace_in_post_id_stripped(self) -> None:
        url = compose_post_url(Platform.TWITTER, "handle", "  42  ")
        assert url == "https://x.com/handle/status/42"
