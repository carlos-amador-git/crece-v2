"""Regression guard: yt-dlp + Chromium + Playwright presentes en container (B-26-03).

El blocker original (2026-04-26) reportaba que TikTok/YouTube scrapers fallaban
en container Docker por ausencia de yt-dlp + Playwright. Verificado 2026-05-16:
ya están en imagen multi-stage actual. Estos tests evitan regresión silenciosa
si se modifica el Dockerfile sin testearlo.
"""
from __future__ import annotations

import os
import shutil
import subprocess

import pytest


def test_yt_dlp_binary_in_path() -> None:
    found = shutil.which("yt-dlp")
    assert found is not None, "yt-dlp no está en PATH del container"


def test_yt_dlp_runs() -> None:
    result = subprocess.run(
        ["yt-dlp", "--version"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert result.stdout.strip(), "yt-dlp --version produjo output vacío"


def test_chrome_bin_env_set() -> None:
    chrome_bin = os.environ.get("CHROME_BIN")
    assert chrome_bin, "CHROME_BIN env no está seteado"
    assert os.path.exists(chrome_bin), f"CHROME_BIN apunta a archivo inexistente: {chrome_bin}"


def test_chromium_executable_runs() -> None:
    chrome_bin = os.environ.get("CHROME_BIN", "/usr/bin/chromium")
    result = subprocess.run(
        [chrome_bin, "--version"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, f"Chromium --version falló: {result.stderr}"


def test_playwright_async_api_importable() -> None:
    from playwright.async_api import async_playwright  # noqa: F401


def test_playwright_sync_api_importable() -> None:
    from playwright.sync_api import sync_playwright  # noqa: F401


@pytest.mark.asyncio
async def test_playwright_launch_chromium_via_chrome_bin() -> None:
    """Smoke test: Playwright puede arrancar Chromium del SO via CHROME_BIN.

    Patrón que usa tiktok.py:200-211 (executable_path=$CHROME_BIN).
    """
    from playwright.async_api import async_playwright

    chrome_bin = os.environ.get("CHROME_BIN", "/usr/bin/chromium")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path=chrome_bin,
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        try:
            page = await browser.new_page()
            await page.set_content("<h1>test</h1>")
            content = await page.content()
            assert "test" in content
        finally:
            await browser.close()
