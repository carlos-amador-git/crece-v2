from __future__ import annotations

from typing import Any

import redis.asyncio as aioredis
from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.core.config import settings
from app.core.database import async_session_factory

router = APIRouter()


@router.get("/")
async def health_check() -> dict[str, Any]:
    """Basic health check."""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
    }


@router.get("/db")
async def health_db() -> dict[str, Any]:
    """Check database connectivity and PostGIS availability."""
    try:
        async with async_session_factory() as session:
            # Check basic connectivity
            result = await session.execute(text("SELECT 1"))
            result.scalar_one()

            # Check PostGIS
            postgis_result = await session.execute(text("SELECT PostGIS_Version()"))
            postgis_version = postgis_result.scalar_one_or_none()

            return {
                "status": "healthy",
                "database": "connected",
                "postgis_version": postgis_version,
            }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {e}")


@router.get("/redis")
async def health_redis() -> dict[str, Any]:
    """Check Redis connectivity."""
    try:
        r = aioredis.from_url(settings.REDIS_URL)
        await r.ping()
        info = await r.info("server")
        await r.aclose()
        return {
            "status": "healthy",
            "redis": "connected",
            "redis_version": info.get("redis_version", "unknown"),
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Redis unavailable: {e}")
