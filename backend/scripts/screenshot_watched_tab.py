#!/usr/bin/env python3
"""Screenshot del tab Perfiles Observados con Playwright dentro del container.

Login Saymi → inyecta token+org en localStorage → navega → screenshot.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
import urllib.parse

LOGIN_URL = "http://crece-backend:8000/api/v1/auth/login"
FRONTEND_BASE = "http://crece-frontend:3000"
EMAIL = "pineda@crece.mx"
PASSWORD = "demo2026!"

# Login
data = urllib.parse.urlencode({"username": EMAIL, "password": PASSWORD}).encode()
req = urllib.request.Request(
    LOGIN_URL,
    data=data,
    headers={"Content-Type": "application/x-www-form-urlencoded"},
)
with urllib.request.urlopen(req, timeout=10) as resp:
    payload = json.load(resp)
TOKEN = payload["access_token"]
print(f"Token obtenido (len {len(TOKEN)})")

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        executable_path="/usr/bin/chromium",
        args=["--no-sandbox", "--disable-dev-shm-usage"],
    )
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})

    # Inyectar token + org_id en localStorage ANTES de navegar
    ctx.add_init_script(
        f"""
        window.localStorage.setItem('crece_access_token', '{TOKEN}');
        window.localStorage.setItem('crece_active_org_id', '2');
        document.cookie = 'crece_access_token={TOKEN}; path=/; SameSite=Lax';
        """
    )
    # Cookie también via API (por si init_script corre tarde)
    ctx.add_cookies([
        {
            "name": "crece_access_token",
            "value": TOKEN,
            "domain": "crece-frontend",
            "path": "/",
            "httpOnly": False,
            "secure": False,
            "sameSite": "Lax",
        }
    ])

    page = ctx.new_page()
    page.on("console", lambda msg: print(f"  [console.{msg.type}] {msg.text}"))
    page.on("pageerror", lambda exc: print(f"  [pageerror] {exc}"))

    # Login via UI form
    print("Login via UI form...")
    page.goto(f"{FRONTEND_BASE}/login", wait_until="domcontentloaded", timeout=30000)
    page.locator('input[type="email"]').fill(EMAIL)
    page.locator('input[type="password"]').fill(PASSWORD)
    # Click submit (más confiable que Enter)
    page.locator('button[type="submit"]').click()
    time.sleep(7)
    print(f"  url after submit: {page.url}")
    # Screenshot de la página post-submit para debug
    page.screenshot(path="/app/.context/screenshot-post-login.png", full_page=False)

    print("Navigating /dashboard/aceptacion/fantasmas...")
    page.goto(f"{FRONTEND_BASE}/dashboard/aceptacion/fantasmas", wait_until="domcontentloaded", timeout=30000)
    time.sleep(5)
    print(f"  url after navigate: {page.url}")

    # Screenshot tab default (resumen)
    out1 = "/app/.context/screenshot-fantasmas-resumen.png"
    page.screenshot(path=out1, full_page=False)
    print(f"  → {out1}")

    # Click tab "Perfiles Observados"
    page.get_by_role("tab", name="Perfiles Observados").click()
    time.sleep(2)

    out2 = "/app/.context/screenshot-fantasmas-observados.png"
    page.screenshot(path=out2, full_page=False)
    print(f"  → {out2}")

    out3 = "/app/.context/screenshot-fantasmas-observados-full.png"
    page.screenshot(path=out3, full_page=True)
    print(f"  → {out3}")

    # Click en una row para abrir el drawer (Mariel Villatoro debe estar visible)
    try:
        page.get_by_text("Mariel Villatoro").first.click(timeout=5000)
        time.sleep(2)
        out4 = "/app/.context/screenshot-watched-drawer.png"
        page.screenshot(path=out4, full_page=False)
        print(f"  → {out4}")
    except Exception as e:
        print(f"  drawer click skipped: {e}")

    browser.close()
print("Done")
