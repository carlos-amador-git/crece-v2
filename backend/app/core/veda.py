from __future__ import annotations

from datetime import UTC, datetime

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

from app.core.config import settings

# Paths blocked during veda electoral (write operations on political content)
#
# NOTA (S3.5): /api/v1/planes NO está en esta lista intencionalmente.
# Los planes IA son análisis interno (generación, edición de tareas, registro
# de métricas reales, cambio de estado en el Kanban). NO son publicaciones
# externas y deben seguir operativos durante veda — el equipo necesita poder
# planificar, delegar tareas internas y medir avance sin importar el período
# electoral. Las publicaciones externas (posts, contenido IA publicado en
# redes) quedan cubiertas por los otros prefijos de esta lista + la auditoría
# de ia_content_registry. Ver cross-audit Gemini del PLAN-current.md nota 5.
_VEDA_BLOCKED_PATHS: list[tuple[str, set[str]]] = [
    ("/api/v1/social", {"POST", "PATCH", "PUT"}),
    ("/api/v1/encuestas", {"POST"}),
    ("/api/v1/content/pieces", {"PATCH"}),  # aprobar publicaciones externas
    ("/api/v1/content/generate", {"POST"}),  # generar contenido para publicar
]

# Paths that always remain operational
_VEDA_ALLOWED_PREFIXES = (
    "/api/v1/health",
    "/api/v1/auth",
)


def _is_veda_active() -> bool:
    """Check if veda electoral is currently active based on settings."""
    if not settings.VEDA_ELECTORAL_ACTIVE:
        return False

    now = datetime.now(UTC)

    if settings.VEDA_ELECTORAL_INICIO:
        try:
            inicio = datetime.fromisoformat(settings.VEDA_ELECTORAL_INICIO)
            if inicio.tzinfo is None:
                inicio = inicio.replace(tzinfo=UTC)
            if now < inicio:
                return False
        except ValueError:
            pass

    if settings.VEDA_ELECTORAL_FIN:
        try:
            fin = datetime.fromisoformat(settings.VEDA_ELECTORAL_FIN)
            if fin.tzinfo is None:
                fin = fin.replace(tzinfo=UTC)
            if now > fin:
                return False
        except ValueError:
            pass

    return True


class VedaElectoralMiddleware(BaseHTTPMiddleware):
    """Blocks write operations on political content during veda electoral period.

    During veda, these endpoints return 403:
    - POST/PATCH/DELETE on /planes (AI-generated content)
    - POST/PATCH on /social (scraper results are OK via workers, but manual posts are blocked)
    - POST on /encuestas (field surveys cannot be conducted during veda)

    These remain operational:
    - All GET endpoints (read-only access)
    - Auth endpoints
    - Health endpoints
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Only check if veda is active
        if not _is_veda_active():
            return await call_next(request)

        # GET requests are always allowed
        if request.method == "GET":
            return await call_next(request)

        # Always allow auth and health endpoints
        path = request.url.path
        if path.startswith(_VEDA_ALLOWED_PREFIXES):
            return await call_next(request)

        # Check if this path+method combo is blocked
        method = request.method
        for blocked_path, blocked_methods in _VEDA_BLOCKED_PATHS:
            if path.startswith(blocked_path) and method in blocked_methods:
                return JSONResponse(
                    status_code=403,
                    content={
                        "detail": (
                            "Operacion bloqueada por veda electoral. "
                            "Las operaciones de escritura sobre contenido politico "
                            "estan restringidas durante el periodo de veda."
                        ),
                    },
                )

        return await call_next(request)
