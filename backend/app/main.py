from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import IntegrityError
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.api.v1 import api_router
from app.core.config import settings
from app.core.database import engine
from app.core.limiter import limiter

# Bugsink error tracking (Sentry-compatible DSN)
if settings.BUGSINK_DSN:
    sentry_sdk.init(
        dsn=settings.BUGSINK_DSN,
        traces_sample_rate=0.1,
        environment=settings.APP_ENV,
        release=settings.APP_VERSION,
    )

logging.basicConfig(
    level=logging.DEBUG if settings.APP_DEBUG else logging.INFO,
    format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown hooks."""
    logger.info("Starting %s v%s [%s]", settings.APP_TITLE, settings.APP_VERSION, settings.APP_ENV)

    # Startup: verify database connectivity
    try:
        async with engine.begin() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        logger.info("Database connection verified")
    except Exception as e:
        logger.error("Database connection failed: %s", e)

    yield

    # Shutdown: dispose engine pool
    await engine.dispose()
    logger.info("Application shutdown complete")


app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    description="Political Intelligence Platform for Mexican Political Parties",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)

# E.1 — Rate limiting (P0 security)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# E.4 — Proxy headers with restricted trusted_hosts (P1 security)
app.add_middleware(
    ProxyHeadersMiddleware,
    trusted_hosts=["127.0.0.1", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"],
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True if settings.CORS_ORIGINS != ["*"] else False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Exception handlers ──────────────────────────────────────
# D-OBS-01: antes de este handler, cualquier IntegrityError levantaba un 500
# con body "Internal Server Error" plano (no JSON) y sin tipo estructurado,
# lo cual complicaba el debugging de clientes como n8n o Postman. Ahora se
# devuelve un 409 Conflict con detalle + tipo del error original de la DB.
@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    logger.warning(
        "IntegrityError on %s %s: %s",
        request.method,
        request.url.path,
        exc.orig if exc.orig else exc,
    )
    return JSONResponse(
        status_code=409,
        content={
            "detail": "Database integrity violation",
            "error_type": type(exc.orig).__name__ if exc.orig else "IntegrityError",
            "message": str(exc.orig) if exc.orig else str(exc),
        },
    )


# Routers
app.include_router(api_router)


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {"service": settings.APP_TITLE, "version": settings.APP_VERSION}
