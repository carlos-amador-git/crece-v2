from __future__ import annotations

import json
from typing import Any

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://crece:crece_secret@localhost:5432/crece_v2"
    DATABASE_URL_SYNC: str = "postgresql://crece:crece_secret@localhost:5432/crece_v2"

    # ── Redis ─────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── JWT ───────────────────────────────────────────────
    JWT_SECRET: str = "CHANGE-ME-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440  # 24 hours

    # ── PII encryption (D-DATA-02 LFPDPPP) ────────────────
    # pgp_sym_encrypt symmetric key for ciudadanos_legacy PII columns.
    # NEVER commit the real key. Rotation: scripts/rotate_pii_key.py (future).
    PII_ENCRYPTION_KEY: str = "CHANGE-ME-pii-dev-key-min-32-chars"

    # ── MinIO ─────────────────────────────────────────────
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "crece-v2"
    MINIO_SECURE: bool = False

    # ── Claude AI ─────────────────────────────────────────
    CLAUDE_API_KEY: str = ""
    CLAUDE_MODEL: str = "claude-sonnet-4-20250514"

    # ── Groq (tier gratuito · Llama 3.3 70B) ─────────────
    # Usado por /api/v1/reels/generate-script (D-REELS-GROQ-1, 2026-05-15)
    # Registrar en console.groq.com (gratuito, 30 req/min)
    GROQ_API_KEY: str = ""

    # ── Ollama (Coolify VPS — gemma3:12b) ────────────────
    # STATUS 2026-05-15: DORMANT. AI_PROVIDER="claude" por default →
    # plan_generator usa Claude. Para prender Ollama (cuando VPS rinda
    # mejor o el costo Claude se vuelva limitante): poner
    # AI_PROVIDER=ollama en .env, sin redeploy de código.
    # Gemma local fue removido del Mac Mini 2026-04-25. NO restaurar
    # localhost sin coordinar con el CEO.
    OLLAMA_BASE_URL: str = "http://163.245.208.96:11434"
    OLLAMA_MODEL: str = "gemma3:12b"
    AI_PROVIDER: str = "claude"  # "claude" | "ollama" — Ollama dormant
    # Master kill-switch for ALL local Ollama usage. Default off: the ~8GB
    # gemma3:12b model OOMs the shared VPS (RAM+swap exhausted → swap thrash →
    # MinIO drive offline + worker OOM). When false: plan/content generation
    # forces Claude, and the Gemma NLP enrichment (Plutchik emotions, topic
    # extraction, trend-cluster labels) plus the Ollama-only /plan-ia pipeline
    # short-circuit instead of loading the model.
    OLLAMA_ENABLED: bool = False

    # ── YouTube Data API v3 ──────────────────────────────
    YOUTUBE_API_KEY: str = ""

    # ── Twitter/X ────────────────────────────────────────
    TWITTER_AUTH_TOKEN: str = ""  # auth_token cookie from x.com browser session (for Scweet)
    # SQLite de cuentas de twscrape. Debe apuntar a un directorio escribible y
    # persistente: guarda las cookies de sesión del pool, y regenerarlas en
    # cada redeploy implicaría re-autenticar todas las cuentas.
    TWSCRAPE_DB_PATH: str = "/data/twscrape_accounts.db"

    # ── TikTok ───────────────────────────────────────────
    TIKTOK_MS_TOKEN: str = ""

    # ── Facebook ─────────────────────────────────────────
    FACEBOOK_COOKIES_FILE: str = ""  # deprecated — kept for backward compat
    FACEBOOK_C_USER: str = ""  # c_user cookie from authenticated FB session
    FACEBOOK_XS: str = ""  # xs cookie from authenticated FB session

    # ── CORS ──────────────────────────────────────────────
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://frontend-zeta-sepia-46.vercel.app",
    ]

    # ── Veda Electoral ───────────────────────────────────
    VEDA_ELECTORAL_ACTIVE: bool = False
    VEDA_ELECTORAL_INICIO: str = ""
    VEDA_ELECTORAL_FIN: str = ""

    # ── Blindaje Legal ───────────────────────────────────
    TOPE_CAMPANA_MXN: float = 500_000.0

    # ── Observability ────────────────────────────────────
    BUGSINK_DSN: str = ""  # Sentry-compatible DSN for Bugsink error tracking
    DISCORD_WEBHOOK_URL: str = ""  # F0.1 MVP · alertas 5xx/exception/429 via Discord webhook

    # ── n8n Integration ──────────────────────────────────
    N8N_WEBHOOK_SECRET: str = ""
    N8N_CAMPAIGN_WEBHOOK_URL: str = ""  # n8n webhook URL for campaign dispatch
    N8N_CRECE_TOKEN: str = ""  # shared secret for CRECE→n8n auth (Gemini G1)

    # ── App ───────────────────────────────────────────────
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    APP_TITLE: str = "CRECE v2.0"
    APP_VERSION: str = "2.0.0"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return json.loads(v)
        return v

    @model_validator(mode="after")
    def _guard_production_secrets(self) -> Settings:
        """E.5 — Refuse to start in production/staging with default secrets.

        F-ALTO-02 (AUDIT-SECURITY-RBAC-2026-05-15): default JWT_SECRET could
        be reused across stacks. Now `production` and `staging` both reject
        defaults. `development` logs a stderr warning but proceeds.
        """
        _defaults = {
            "JWT_SECRET": "CHANGE-ME-in-production",
            "PII_ENCRYPTION_KEY": "CHANGE-ME-pii-dev-key-min-32-chars",
        }
        offenders = [
            name for name, default_val in _defaults.items()
            if getattr(self, name) == default_val
        ]
        if not offenders:
            return self
        if self.APP_ENV in {"production", "staging"}:
            raise ValueError(
                f"{', '.join(offenders)} still have default values. "
                f"Set real secrets before running in {self.APP_ENV}."
            )
        import sys
        print(
            f"[config] WARNING: {', '.join(offenders)} using default values. "
            f"OK for APP_ENV=development; reject in staging/production.",
            file=sys.stderr,
        )
        return self

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


settings = Settings()
