from __future__ import annotations

import logging
import time
from collections import defaultdict
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy.exc import IntegrityError
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.api.v1 import api_router
from app.core.alerting import send_discord_alert_bg
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


# F0.1 · 429 sostenido · alerta Discord si 10+ rate limits desde misma IP en 60s
# Envuelve el handler slowapi original · timeboxed spec (no más lógica).
_429_TRACKER: dict[str, list[float]] = defaultdict(list)
_429_WINDOW_SEC = 60
_429_THRESHOLD = 10


async def rate_limit_handler_with_alert(request: Request, exc: RateLimitExceeded):
    """Wrap slowapi handler: track 429 per IP, alert on sustained burst, then delegate."""
    ip = get_remote_address(request)
    now = time.time()
    hits = [t for t in _429_TRACKER[ip] if now - t < _429_WINDOW_SEC]
    hits.append(now)
    _429_TRACKER[ip] = hits
    # Fire alert exactly when we cross the threshold (not every subsequent hit)
    if len(hits) == _429_THRESHOLD:
        send_discord_alert_bg(
            title=f"429 sostenido: {_429_THRESHOLD} rate limits/{_429_WINDOW_SEC}s desde {ip}",
            level="429",
            details={"method": request.method, "path": request.url.path, "ip": ip},
        )
    return _rate_limit_exceeded_handler(request, exc)


app.add_exception_handler(RateLimitExceeded, rate_limit_handler_with_alert)

# E.4 — Proxy headers with restricted trusted_hosts (P1 security)
app.add_middleware(
    ProxyHeadersMiddleware,
    trusted_hosts=["*"],
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ORIGINS != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── HTTPS redirect fix for reverse proxies (Cloudflare tunnel) ──
# FastAPI's trailing-slash redirects use the request's scheme, which is
# HTTP inside the container. When behind an HTTPS proxy this produces
# mixed-content redirects (https→http) that Safari blocks.
@app.middleware("http")
async def fix_https_redirects(request: Request, call_next):
    response = await call_next(request)
    if (
        response.status_code in (301, 302, 307, 308)
        and request.headers.get("x-forwarded-proto") == "https"
    ):
        location = response.headers.get("location", "")
        if location.startswith("http://"):
            response.headers["location"] = "https://" + location[7:]
    return response


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


# F0.1 · Handler genérico de excepciones no capturadas · Sentry + Discord webhook
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Sentry capture (si init fue ejecutado con DSN válido)
    sentry_sdk.capture_exception(exc)
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    send_discord_alert_bg(
        title=f"Unhandled exception: {type(exc).__name__}",
        level="exception",
        details={
            "method": request.method,
            "path": request.url.path,
            "error_type": type(exc).__name__,
            "message": str(exc)[:500],
        },
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "internal server error"},
    )


# F0.1 · Middleware para 5xx que NO provienen de exception (e.g. raise HTTPException(500) manual)
@app.middleware("http")
async def alert_on_5xx(request: Request, call_next):
    response = await call_next(request)
    if response.status_code >= 500:
        # El exception handler ya cubre excepciones · esto captura HTTPException(500) manual
        # y cualquier 5xx producido por código downstream que construye JSONResponse directo.
        send_discord_alert_bg(
            title=f"HTTP {response.status_code} on {request.url.path}",
            level="5xx",
            details={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
            },
        )
    return response


# Routers
app.include_router(api_router)


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {"service": settings.APP_TITLE, "version": settings.APP_VERSION}
