"""Helper para conectar Playwright al Scraping Browser API de Brightdata.

Brightdata Browser API expone un Chromium headless hosted en su red, accesible
via CDP WebSocket (Playwright/Puppeteer) o Selenium. Para nuestro caso usamos
Playwright async, consistente con el resto del stack.

Ventajas vs Playwright local:
- IP residencial + rotación nativa (no Docker block).
- Anti-bot stealth incorporado (canvas fingerprint, webGL, timezone aleatorios).
- CAPTCHA solver automático (cargo extra si dispara).

Limitaciones:
- Latencia mayor que local (~500-800ms round-trip por acción).
- No resuelve problemas de cliente (lazy-load, scroll triggers) — eso es DOM,
  no red. Para eso toca código de interacción, no el proxy.

Credenciales en ``backend/.env.scraping-keys`` como ``BRIGHTDATA_BROWSER_WSS``.
NUNCA hardcodear ni commitear.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from playwright.async_api import Browser, BrowserContext, Page, async_playwright


def _load_env() -> None:
    env_file = Path(__file__).resolve().parents[2] / ".env.scraping-keys"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def get_wss_endpoint() -> str:
    _load_env()
    endpoint = os.environ.get("BRIGHTDATA_BROWSER_WSS")
    if not endpoint:
        raise RuntimeError(
            "BRIGHTDATA_BROWSER_WSS no definido en entorno ni en "
            "backend/.env.scraping-keys."
        )
    return endpoint


@asynccontextmanager
async def brightdata_page(
    *,
    user_agent: str | None = None,
    viewport: dict[str, int] | None = None,
) -> AsyncIterator[tuple[Browser, BrowserContext, Page]]:
    """Context manager: yields (browser, context, page) conectados a Brightdata CDP.

    Cierra browser al salir aunque haya excepciones. Usar siempre con ``async with``.
    """
    wss = get_wss_endpoint()
    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp(wss)
        try:
            # Brightdata normalmente expone un contexto default; intentamos reusarlo
            # y si no hay páginas vivas, creamos nueva.
            context = browser.contexts[0] if browser.contexts else await browser.new_context(
                user_agent=user_agent,
                viewport=viewport or {"width": 1280, "height": 900},
            )
            page = await context.new_page()
            try:
                yield browser, context, page
            finally:
                await page.close()
        finally:
            await browser.close()
