"""Back-off decorator para errores transitorios en scrapers (S10).

Cross-audit Gemini (2026-05-15) advirtió:
1. ``time.sleep()`` síncrono dentro de un decorator bloquea workers Celery
   → preferir ``asyncio.sleep`` cuando se aplique a coroutines.
2. Si IG/X devuelve 429 persistente, reintentar rápido provoca shadowban.
   Por eso este decorator REINTENTA SOLO transitorios (timeout + 5xx) y
   ABORTA en 429/403 (los logueamos para que un sprint de proxies futuro
   los aborde, no para enmascarar).

Uso:

    from app.scrapers.helpers.backoff import with_backoff

    class TwitterScraper(BaseScraper):
        @with_backoff(retries=2, base_delay=3.0)
        def update_profile_stats(self, handle: str) -> dict[str, int]:
            ...

Decorator funciona con funciones sync y async (detecta inspect.iscoroutinefunction).

Errores tratados como transitorios (retry):
- TimeoutError, requests.Timeout, asyncio.TimeoutError
- HTTPError con status 502/503/504
- ConnectionError

Errores no transitorios (no retry, propagan inmediato):
- HTTP 429 (rate limit) — log warn + raise
- HTTP 403 (forbidden) — log warn + raise
- Cualquier otra exception → raise inmediato
"""
from __future__ import annotations

import asyncio
import functools
import inspect
import logging
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)


_TRANSIENT_HTTP_STATUS = {500, 502, 503, 504}
_BLOCKED_HTTP_STATUS = {429, 403}


def _is_transient(exc: Exception) -> bool:
    """¿Es un error transitorio reintentable?"""
    # Timeouts genéricos
    if isinstance(exc, (TimeoutError, asyncio.TimeoutError)):
        return True
    # requests.Timeout / httpx.TimeoutException — detección por nombre
    # para no agregar dependencias.
    name = exc.__class__.__name__.lower()
    if "timeout" in name:
        return True
    if "connection" in name and "error" in name:
        return True
    # HTTPError con status — detectar via response.status_code si existe
    status = getattr(getattr(exc, "response", None), "status_code", None) or getattr(
        exc, "status_code", None
    )
    if status in _TRANSIENT_HTTP_STATUS:
        return True
    if status in _BLOCKED_HTTP_STATUS:
        # Explícitamente NO transitorio — abortamos sin retry.
        logger.warning(
            f"Backoff abort: blocked status {status} en "
            f"{exc.__class__.__name__}: {exc}. "
            f"No reintentamos para evitar shadowban. Considera proxy rotation."
        )
        return False
    return False


def with_backoff(retries: int = 2, base_delay: float = 3.0) -> Callable:
    """Decorator que reintenta funciones con errores transitorios.

    Args:
        retries: nº de reintentos DESPUÉS del primer intento.
            Total de intentos = retries + 1. Default 2 (3 total).
        base_delay: segundos base entre retries (exponencial: 1×, 2×, 4×...).

    Funciona con funciones sync y async transparentemente.
    """

    def decorator(fn: Callable) -> Callable:
        if inspect.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                last_exc: Exception | None = None
                for attempt in range(retries + 1):
                    try:
                        return await fn(*args, **kwargs)
                    except Exception as e:
                        last_exc = e
                        if not _is_transient(e):
                            raise
                        if attempt < retries:
                            delay = base_delay * (2**attempt)
                            logger.info(
                                f"Backoff retry {attempt + 1}/{retries} de "
                                f"{fn.__name__} en {delay:.1f}s: {e}"
                            )
                            await asyncio.sleep(delay)
                if last_exc is not None:
                    raise last_exc
                return None  # nunca llega — keeps mypy contento

            return async_wrapper

        @functools.wraps(fn)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: Exception | None = None
            for attempt in range(retries + 1):
                try:
                    return fn(*args, **kwargs)
                except Exception as e:
                    last_exc = e
                    if not _is_transient(e):
                        raise
                    if attempt < retries:
                        delay = base_delay * (2**attempt)
                        logger.info(
                            f"Backoff retry {attempt + 1}/{retries} de "
                            f"{fn.__name__} en {delay:.1f}s: {e}"
                        )
                        time.sleep(delay)
            if last_exc is not None:
                raise last_exc
            return None

        return sync_wrapper

    return decorator
