"""Test: extraer replies de 1 tweet Piña via Brightdata Scraping Browser.

Validación de cobertura. NO ingiesta a BD.

Uso:
    python scripts/brightdata_twitter_replies_test.py [tweet_id]

Si no se pasa tweet_id, usa 1939727070705459429 (top Piña por likes en BD).

Reporta:
- HTTP status + bytes del DOM final.
- Count de replies visibles tras scroll.
- Sample de 3 replies (texto + autor + likes) si existen.
- Si aparece loginWall / suspensión / captcha.
"""

from __future__ import annotations

import asyncio
import sys
from typing import Any

from app.services.brightdata_browser import brightdata_page

DEFAULT_TWEET_ID = "1939727070705459429"


async def extract_replies(tweet_id: str) -> dict[str, Any]:
    url = f"https://x.com/Alejandro_Pinha/status/{tweet_id}"
    result: dict[str, Any] = {"url": url, "tweet_id": tweet_id}

    async with brightdata_page() as (_browser, _ctx, page):
        response = await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        result["http_status"] = response.status if response else None

        # Esperar al SPA de Twitter
        try:
            await page.wait_for_selector('article[data-testid="tweet"]', timeout=20_000)
        except Exception as exc:
            result["selector_wait_error"] = str(exc)[:200]

        html_snippet = await page.content()
        result["html_bytes"] = len(html_snippet)
        for needle in [
            "Sign in to X",
            "Iniciar sesión en X",
            "Log in to Twitter",
            "Something went wrong",
            "Nothing to see here",
            "rate limit",
            "Rate limit",
        ]:
            if needle in html_snippet:
                result.setdefault("signals", []).append(needle)

        # Guardar HTML para inspección manual offline
        from pathlib import Path
        Path("/tmp/joy-brightdata-twitter-dump.html").write_text(html_snippet)

        # Scroll para disparar lazy-load de replies
        for _ in range(6):
            await page.mouse.wheel(0, 4000)
            await page.wait_for_timeout(2000)

        # Tweets en la conversación: article data-testid="tweet" con texto dentro de div[lang]
        articles = await page.locator('article[data-testid="tweet"]').all()
        result["articles_found"] = len(articles)

        replies: list[dict[str, Any]] = []
        # El primer article suele ser el tweet principal; los siguientes son replies.
        for art in articles[1:12]:  # hasta 10 replies sample
            try:
                text_loc = art.locator('div[data-testid="tweetText"]')
                text = await text_loc.first.inner_text(timeout=3000) if await text_loc.count() else ""
                author_loc = art.locator('a[role="link"] span').first
                author = await author_loc.inner_text(timeout=3000) if await author_loc.count() else ""
                # Likes: div[data-testid="like"] contiene un span con el count
                like_loc = art.locator('[data-testid="like"] span[data-testid="app-text-transition-container"] span span')
                likes = await like_loc.first.inner_text(timeout=2000) if await like_loc.count() else "0"
                replies.append({"author": author.strip(), "text": text.strip()[:200], "likes": likes.strip()})
            except Exception as exc:  # pragma: no cover
                replies.append({"error": str(exc)[:120]})

        result["replies_extracted"] = len(replies)
        result["replies_sample"] = replies[:3]
    return result


async def main() -> int:
    tweet_id = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TWEET_ID
    report = await extract_replies(tweet_id)
    import json

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
