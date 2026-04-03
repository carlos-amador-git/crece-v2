from __future__ import annotations

import json
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
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

    # ── MinIO ─────────────────────────────────────────────
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "crece-v2"
    MINIO_SECURE: bool = False

    # ── Claude AI ─────────────────────────────────────────
    CLAUDE_API_KEY: str = ""
    CLAUDE_MODEL: str = "claude-sonnet-4-20250514"

    # ── YouTube Data API v3 ──────────────────────────────
    YOUTUBE_API_KEY: str = ""

    # ── TikTok ───────────────────────────────────────────
    TIKTOK_MS_TOKEN: str = ""

    # ── Facebook ─────────────────────────────────────────
    FACEBOOK_COOKIES_FILE: str = ""

    # ── CORS ──────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # ── Veda Electoral ───────────────────────────────────
    VEDA_ELECTORAL_ACTIVE: bool = False
    VEDA_ELECTORAL_INICIO: str = ""
    VEDA_ELECTORAL_FIN: str = ""

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

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


settings = Settings()
