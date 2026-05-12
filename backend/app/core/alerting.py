"""Discord webhook alerting · F0.1 MVP observability.

Plan origen: `.context/PLAN-recuperacion-post-incidente-2026-04-21.md` F0.1 caso B
(Bugsink roto → webhook Slack/Discord MVP).

Características:
- `send_discord_alert(title, level, details)` async · POST a DISCORD_WEBHOOK_URL
- Embed con color por nivel · fields con request context + tunnel_url actual
- Rate limit interno 5 min por (level, method, path, title) hash — no-spamea
- Fire-and-forget: `send_discord_alert_bg` usa asyncio.create_task
- No-op silencioso si DISCORD_WEBHOOK_URL vacío · warning una sola vez al startup
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

Level = Literal["5xx", "exception", "429", "uptime", "info"]

# In-memory rate limiter: hash → last_sent_epoch_ts
#
# KNOWN LIMITATION: Rate limit state is per-process (in-memory dict).
# With `uvicorn --workers N`, each worker has its own dedup cache.
# A storm of N identical errors distributed across workers produces
# up to N alerts instead of 1.
# Impact: negligible for current pilot load (<10 req/s · 3 users).
# Migration to Redis recommended when pilot scales beyond single-worker
# effective throughput. See B-RATE-LIMIT-01 in .context/BACKLOG.md.
_RATE_LIMIT: dict[str, float] = {}
_RATE_LIMIT_TTL_SEC = 300  # 5 min per unique alert signature

# Discord embed colors (decimal)
_COLOR_RED = 0xE74C3C     # 5xx, exception
_COLOR_ORANGE = 0xE67E22  # 429
_COLOR_YELLOW = 0xF1C40F  # uptime
_COLOR_BLUE = 0x3498DB    # info

_TUNNEL_URL_FILE = Path("/tmp/crece-tunnel.url")
_WEBHOOK_TIMEOUT_SEC = 5.0
_EMBED_TITLE_MAX = 256
_EMBED_MESSAGE_MAX = 1000

# Track warning state so startup-log fires only once per process
_missing_url_warned = False


def _color_for(level: Level) -> int:
    return {
        "5xx": _COLOR_RED,
        "exception": _COLOR_RED,
        "429": _COLOR_ORANGE,
        "uptime": _COLOR_YELLOW,
        "info": _COLOR_BLUE,
    }.get(level, _COLOR_BLUE)


def _read_tunnel_url() -> str | None:
    """Read current cloudflared tunnel URL from /tmp/crece-tunnel.url if exists.

    Read at send-time (not import-time) so rotations are captured in every alert.
    """
    try:
        if _TUNNEL_URL_FILE.exists():
            url = _TUNNEL_URL_FILE.read_text().strip()
            return url or None
    except OSError:
        pass
    return None


def _rate_limit_key(level: str, method: str, path: str, title: str) -> str:
    raw = f"{level}|{method}|{path}|{title}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _is_rate_limited(key: str) -> bool:
    """Return True if this key was sent within TTL window. GC stale entries."""
    now = time.time()
    # GC expired entries (cheap, runs at most once per call)
    expired = [k for k, ts in _RATE_LIMIT.items() if now - ts > _RATE_LIMIT_TTL_SEC]
    for k in expired:
        del _RATE_LIMIT[k]

    if key in _RATE_LIMIT:
        return True
    _RATE_LIMIT[key] = now
    return False


def _build_embed(title: str, level: Level, details: dict[str, Any]) -> dict[str, Any]:
    fields: list[dict[str, Any]] = []
    if details.get("method"):
        fields.append({"name": "Method", "value": str(details["method"]), "inline": True})
    if details.get("path"):
        fields.append({"name": "Path", "value": str(details["path"])[:100], "inline": True})
    if details.get("status_code"):
        fields.append({"name": "Status", "value": str(details["status_code"]), "inline": True})
    if details.get("user_id"):
        fields.append({"name": "User", "value": str(details["user_id"]), "inline": True})
    if details.get("ip"):
        fields.append({"name": "IP", "value": str(details["ip"]), "inline": True})
    if details.get("error_type"):
        fields.append({"name": "Error type", "value": str(details["error_type"]), "inline": True})
    if details.get("message"):
        msg = str(details["message"])[:_EMBED_MESSAGE_MAX]
        fields.append({"name": "Message", "value": msg, "inline": False})

    tunnel_url = _read_tunnel_url()
    if tunnel_url:
        fields.append({"name": "Tunnel URL", "value": tunnel_url, "inline": False})

    fields.append({"name": "Env", "value": settings.APP_ENV, "inline": True})
    fields.append(
        {"name": "Service", "value": f"{settings.APP_TITLE} v{settings.APP_VERSION}", "inline": True}
    )

    return {
        "title": title[:_EMBED_TITLE_MAX],
        "color": _color_for(level),
        "fields": fields,
        "timestamp": datetime.now(UTC).isoformat(),
    }


async def send_discord_alert(
    title: str,
    level: Level,
    details: dict[str, Any] | None = None,
) -> bool:
    """Send alert to Discord via webhook. Fire-and-forget semantics.

    Returns True if the payload was POSTed (2xx from Discord), False otherwise
    (no URL configured, rate-limited, or HTTP error — errors are logged not raised).
    """
    global _missing_url_warned

    url = settings.DISCORD_WEBHOOK_URL
    if not url:
        if not _missing_url_warned:
            logger.warning(
                "DISCORD_WEBHOOK_URL not configured — alerts will be no-op. "
                "Set in .env to enable (see F0.1 plan)."
            )
            _missing_url_warned = True
        return False

    details = details or {}
    rl_key = _rate_limit_key(
        level,
        str(details.get("method", "-")),
        str(details.get("path", "-")),
        title,
    )
    if _is_rate_limited(rl_key):
        return False

    embed = _build_embed(title, level, details)
    payload = {"embeds": [embed]}

    try:
        async with httpx.AsyncClient(timeout=_WEBHOOK_TIMEOUT_SEC) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
        return True
    except httpx.HTTPError as e:
        logger.warning("Discord webhook failed: %s", e)
        return False
    except Exception:  # noqa: BLE001 — fire-and-forget must never raise
        logger.exception("Unexpected error sending Discord alert")
        return False


def send_discord_alert_bg(
    title: str,
    level: Level,
    details: dict[str, Any] | None = None,
) -> None:
    """Schedule alert as async background task · does not block the caller.

    Safe to call from sync contexts: catches RuntimeError if no running loop.
    """
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(send_discord_alert(title, level, details))
    except RuntimeError:
        logger.debug("No running event loop — alert not scheduled")
