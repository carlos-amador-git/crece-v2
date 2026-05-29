"""Unit tests for get_scraper factory (B-26-02 fix)."""
from __future__ import annotations

import pytest

from app.scrapers.base import BaseScraper, get_scraper


@pytest.mark.parametrize(
    "platform_input",
    [
        "twitter", "TWITTER", "Twitter",
        "instagram", "INSTAGRAM",
        "facebook", "FACEBOOK",
        "tiktok", "TIKTOK",
        "youtube", "YOUTUBE",
        "bluesky", "BLUESKY",
        "threads", "THREADS",
        "telegram", "TELEGRAM",
    ],
)
def test_get_scraper_accepts_any_case(platform_input: str) -> None:
    """Registry must accept platform strings in any case (B-26-02)."""
    scraper = get_scraper(platform_input)
    assert isinstance(scraper, BaseScraper)


def test_get_scraper_unknown_platform_raises() -> None:
    with pytest.raises(ValueError, match="No scraper available"):
        get_scraper("MYSPACE")


def test_get_scraper_uppercase_was_broken_before_fix() -> None:
    """Regression: Platform.value retorna uppercase ('TWITTER'). Antes del fix,
    el dispatch periódico de scrape_all_profiles() fallaba con ValueError.
    """
    scraper_upper = get_scraper("TWITTER")
    scraper_lower = get_scraper("twitter")
    assert type(scraper_upper) is type(scraper_lower)
