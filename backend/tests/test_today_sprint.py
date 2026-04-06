"""Tests for today's sprint: scrapers, OSINT, Chatwoot direct, plan generator, content factory.

Verifies:
1. Bluesky, Threads, Telegram scrapers import and have correct structure
2. Original 5 scrapers still import correctly
3. Sherlock/OSINT endpoint exists and validates input
4. Chatwoot direct webhook handler (X-Chatwoot-Signature)
5. Plan generator with IPD injection
6. Content Factory with Ollama routing
7. Platform enum includes new platforms
"""

from __future__ import annotations

import hashlib
import hmac
import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import User
from tests.conftest import auth_headers


# ── Helpers ─────────────────────────────────────────────────────

_TEST_SECRET = settings.N8N_WEBHOOK_SECRET or settings.JWT_SECRET


def _chatwoot_sign(payload_bytes: bytes) -> str:
    return hmac.new(_TEST_SECRET.encode(), payload_bytes, hashlib.sha256).hexdigest()


# ── 1. Scraper imports ──────────────────────────────────────────


class TestScraperImports:
    """Verify all scrapers import without errors."""

    def test_import_bluesky(self) -> None:
        from app.scrapers.bluesky import BlueskyScraper

        assert BlueskyScraper is not None

    def test_import_threads(self) -> None:
        from app.scrapers.threads import ThreadsScraper

        assert ThreadsScraper is not None

    def test_import_telegram(self) -> None:
        from app.scrapers.telegram import TelegramScraper

        assert TelegramScraper is not None

    def test_import_youtube(self) -> None:
        from app.scrapers.youtube import YouTubeScraper

        assert YouTubeScraper is not None

    def test_import_instagram(self) -> None:
        from app.scrapers.instagram import InstagramScraper

        assert InstagramScraper is not None

    def test_import_twitter(self) -> None:
        from app.scrapers.twitter import TwitterScraper

        assert TwitterScraper is not None

    def test_import_facebook(self) -> None:
        from app.scrapers.facebook import FacebookScraper

        assert FacebookScraper is not None

    def test_import_tiktok(self) -> None:
        from app.scrapers.tiktok import TikTokScraper

        assert TikTokScraper is not None

    def test_scraper_registry(self) -> None:
        """get_scraper() returns correct scraper for each platform."""
        from app.scrapers.base import get_scraper

        for platform in ["youtube", "instagram", "twitter", "facebook", "tiktok", "bluesky"]:
            scraper = get_scraper(platform)
            assert scraper is not None, f"get_scraper('{platform}') returned None"

    def test_scraper_registry_threads_telegram(self) -> None:
        """New scrapers are registered in the factory."""
        from app.scrapers.base import get_scraper

        for platform in ["threads", "telegram"]:
            scraper = get_scraper(platform)
            assert scraper is not None, f"get_scraper('{platform}') returned None"


# ── 2. Platform enum ────────────────────────────────────────────


class TestPlatformEnum:
    """Verify Platform enum includes all platforms."""

    def test_original_platforms(self) -> None:
        from app.models.social import Platform

        for name in ["TWITTER", "INSTAGRAM", "FACEBOOK", "TIKTOK", "YOUTUBE", "BLUESKY"]:
            assert hasattr(Platform, name), f"Platform.{name} missing"

    def test_new_platforms(self) -> None:
        from app.models.social import Platform

        for name in ["THREADS", "TELEGRAM"]:
            assert hasattr(Platform, name), f"Platform.{name} missing"


# ── 3. OSINT / Sherlock endpoint ────────────────────────────────


class TestOSINTEndpoint:
    """Test /api/v1/osint/sherlock endpoint."""

    async def test_osint_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/osint/sherlock",
            json={"username": "test"},
        )
        assert resp.status_code == 401

    async def test_osint_requires_admin_or_analyst(
        self, client: AsyncClient, viewer_token: str
    ) -> None:
        resp = await client.post(
            "/api/v1/osint/sherlock",
            json={"username": "test"},
            headers=auth_headers(viewer_token),
        )
        assert resp.status_code == 403

    async def test_osint_validates_username(
        self, client: AsyncClient, admin_token: str
    ) -> None:
        """Invalid username should return 422."""
        resp = await client.post(
            "/api/v1/osint/sherlock",
            json={"username": "test; rm -rf /"},
            headers=auth_headers(admin_token),
        )
        assert resp.status_code == 422


# ── 4. Chatwoot direct webhook ──────────────────────────────────


class TestChatwootDirectWebhook:
    """Test direct Chatwoot payload handling (not via n8n)."""

    async def test_chatwoot_signature_accepted(self, client: AsyncClient) -> None:
        """X-Chatwoot-Signature header is accepted."""
        payload = {"event": "conversation_created", "conversation": {"id": 1}}
        payload_bytes = json.dumps(payload).encode()
        sig = _chatwoot_sign(payload_bytes)

        resp = await client.post(
            "/api/v1/webhooks/chatwoot",
            content=payload_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Chatwoot-Signature": sig,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "received"

    async def test_chatwoot_message_created(self, client: AsyncClient) -> None:
        """Direct message_created event is handled."""
        payload = {
            "event": "message_created",
            "message": {"id": 1, "message_type": "incoming", "content": "Hola"},
            "conversation": {"id": 42},
        }
        payload_bytes = json.dumps(payload).encode()
        sig = _chatwoot_sign(payload_bytes)

        resp = await client.post(
            "/api/v1/webhooks/chatwoot",
            content=payload_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Chatwoot-Signature": sig,
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["event"] == "message_created"
        assert body["conversation_id"] == 42

    async def test_chatwoot_contact_created_no_phone(self, client: AsyncClient) -> None:
        """Direct contact_created without phone is skipped."""
        payload = {
            "event": "contact_created",
            "contact": {"id": 1, "name": "Sin Telefono"},
        }
        payload_bytes = json.dumps(payload).encode()
        sig = _chatwoot_sign(payload_bytes)

        resp = await client.post(
            "/api/v1/webhooks/chatwoot",
            content=payload_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Chatwoot-Signature": sig,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "skipped"


# ── 5. Plan generator IPD injection ─────────────────────────────


class TestPlanGeneratorContext:
    """Test that _gather_context includes IPD data."""

    async def test_gather_context_has_ipd(self, db_session: AsyncSession) -> None:
        """Context dict should include ipd key with score and interpretation."""
        from app.models.dirigente import Dirigente
        from app.models.organizacion import Organizacion, TipoOrganizacion

        org = Organizacion(
            nombre="MC Test",
            slug="mc-test",
            tipo=TipoOrganizacion.PARTIDO,
            estado="CDMX",
            is_active=True,
        )
        db_session.add(org)
        await db_session.flush()

        dirigente = Dirigente(
            full_name="Test Dirigente",
            cargo="Coordinador",
            partido="MC",
            estado="Ciudad de Mexico",
            org_id=org.id,
        )
        db_session.add(dirigente)
        await db_session.flush()
        await db_session.refresh(dirigente)

        from app.services.plan_generator import _gather_context

        context = await _gather_context(db_session, dirigente)

        assert "ipd" in context, "Context must include 'ipd' key"
        assert "score" in context["ipd"]
        assert "interpretation" in context["ipd"]
        assert context["ipd"]["score"] >= 0
        assert context["ipd"]["interpretation"] in (
            "CRITICO", "BAJO", "MEDIO", "BUENO", "EXCELENTE"
        )


# ── 6. Content Factory provider routing ─────────────────────────


class TestContentFactoryProvider:
    """Test that ContentFactory routes to correct provider."""

    def test_ollama_provider_in_config(self) -> None:
        """Verify AI_PROVIDER can be set to ollama."""
        # This tests the config, not the actual generation
        from app.core.config import Settings

        s = Settings(
            AI_PROVIDER="ollama",
            DATABASE_URL="postgresql+asyncpg://x:x@localhost/x",
        )
        assert s.AI_PROVIDER == "ollama"

    def test_content_factory_has_ollama_methods(self) -> None:
        """ContentFactory has Ollama generation methods."""
        from app.services.content_factory import ContentFactory

        assert hasattr(ContentFactory, "_generate_with_ollama")
        assert hasattr(ContentFactory, "_stream_with_ollama")


# ── 7. Sherlock service validation ──────────────────────────────


class TestSherlockService:
    """Test sherlock_service input validation."""

    def test_valid_username(self) -> None:
        from app.services.sherlock_service import _validate_username

        # Should not raise
        _validate_username("alejandro_pina")
        _validate_username("rafael.solano")
        _validate_username("user-name")

    def test_invalid_username_shell_injection(self) -> None:
        from app.services.sherlock_service import _validate_username

        with pytest.raises(ValueError):
            _validate_username("test; rm -rf /")

    def test_invalid_username_too_long(self) -> None:
        from app.services.sherlock_service import _validate_username

        with pytest.raises(ValueError):
            _validate_username("a" * 65)

    def test_invalid_username_empty(self) -> None:
        from app.services.sherlock_service import _validate_username

        with pytest.raises(ValueError):
            _validate_username("")
