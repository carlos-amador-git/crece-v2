"""Compose public URLs for social posts without persisting a column.

Used by :class:`app.schemas.social.SocialPostResponse` to expose a clickable
URL from the ``platform_post_id`` scraped by each adapter together with the
parent profile handle.

If the platform is not yet mapped or required inputs are missing the function
returns ``None`` so the frontend can apply graceful degradation (Sprint 23-B).
"""

from __future__ import annotations

from app.models.social import Platform

_TEMPLATES: dict[Platform, str] = {
    Platform.TWITTER: "https://x.com/{handle}/status/{post_id}",
    Platform.INSTAGRAM: "https://www.instagram.com/p/{post_id}/",
    Platform.FACEBOOK: "https://www.facebook.com/{handle}/posts/{post_id}",
    Platform.YOUTUBE: "https://www.youtube.com/watch?v={post_id}",
    Platform.TIKTOK: "https://www.tiktok.com/@{handle}/video/{post_id}",
    Platform.BLUESKY: "https://bsky.app/profile/{handle}/post/{post_id}",
    Platform.THREADS: "https://www.threads.net/@{handle}/post/{post_id}",
    Platform.TELEGRAM: "https://t.me/{handle}/{post_id}",
}


def compose_post_url(
    platform: Platform | None,
    handle: str | None,
    platform_post_id: str | None,
) -> str | None:
    if not platform or not platform_post_id:
        return None

    template = _TEMPLATES.get(platform)
    if template is None:
        return None

    normalized_handle = (handle or "").lstrip("@").strip()
    if "{handle}" in template and not normalized_handle:
        return None

    return template.format(handle=normalized_handle, post_id=platform_post_id.strip())
