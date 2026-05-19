"""Context variable para asociar ops de BD con el user_id de la request.

S8 audit log (LFPDPPP art. 32). Sprint dedicado 2026-05-15.

Los SQLAlchemy event listeners en ``audit_listeners.py`` no tienen acceso
directo al ``current_user`` de FastAPI — se ejecutan en el flush de la sesión,
no en el contexto de la request. Usamos ``contextvars.ContextVar`` que es
seguro para asyncio (cada task tiene su propia copia).

El middleware ``AuditContextMiddleware`` setea ``current_user_id`` al inicio
de cada request y lo resetea al final. Los listeners lo leen sin acoplarse
al request.
"""
from __future__ import annotations

from contextvars import ContextVar

# None = op de BD ejecutada fuera de request HTTP (script, celery, migración).
# En esos casos el audit log queda con user_id=NULL — auditable como
# "operación de sistema" (válido para Celery beat tasks).
current_user_id: ContextVar[int | None] = ContextVar("current_user_id", default=None)
current_request_path: ContextVar[str | None] = ContextVar(
    "current_request_path", default=None
)
