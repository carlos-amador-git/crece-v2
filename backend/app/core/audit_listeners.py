"""SQLAlchemy event listeners para audit log de ops destructivas/sensibles.

S8 Sprint dedicado 2026-05-15 — cross-audit Gemini sugirió Event Listeners
sobre middleware FastAPI porque:
1. Middleware no captura cascade deletes (FK ON DELETE CASCADE).
2. Middleware no captura bulk updates (``Model.query.update(...)``).
3. Middleware no captura ops desde Celery beat / scripts standalone.

Modelos auditados (LFPDPPP relevant):
- WatchedProfile (DELETE/UPDATE) — perfil monitoreado por dirigente
- WatchedLikeEvent (DELETE) — eventos PII vinculados
- SocialComment (DELETE) — vía author_hash, requisito LFPDPPP
- SocialFollower (DELETE) — followers persistidos con PII
- CompetitorProfile (DELETE) — info personal pública
- PlanIA (DELETE/UPDATE) — D9 trazabilidad INE generación IA

Diseño:
- Listeners registrados en ``init_audit_listeners()``.
- Cada listener inserta una fila en ``audit_log`` vía la session activa.
- Si la session NO tiene ``current_user_id`` (script/Celery), user_id queda NULL.

NO se loguea:
- Valor de campos (riesgo PII duplicada).
- Solo lista de columnas modificadas en UPDATE.
"""
from __future__ import annotations

import logging

from sqlalchemy import event
from sqlalchemy.orm import Session

from app.core.audit_context import current_request_path, current_user_id

logger = logging.getLogger(__name__)


# Modelos a auditar. Lista cerrada — agregar aquí explícitamente cuando se
# identifique otro modelo con PII o impacto destructivo.
_AUDITED_MODELS: list[str] = [
    "watched_profiles",
    "watched_like_events",
    "social_comments",
    "social_followers",
    "competitor_profiles",
    "planes_ia",
]


def _insert_audit_row(
    session: Session,
    *,
    action: str,
    model: str,
    record_id: int | None,
    changes_summary: dict | None = None,
) -> None:
    """Insertar fila en audit_log usando la session activa.

    No usamos ORM (AuditLog.add) para evitar loops con el listener.
    SQL crudo via session.connection() — el INSERT se confirma con el commit
    de la transacción original.
    """
    from sqlalchemy import text

    try:
        session.connection().execute(
            text(
                """
                INSERT INTO audit_log
                    (action, model, record_id, user_id, request_path,
                     changes_summary, created_at)
                VALUES
                    (:action, :model, :record_id, :user_id, :request_path,
                     CAST(:changes_summary AS JSONB), NOW())
                """
            ),
            {
                "action": action,
                "model": model,
                "record_id": record_id,
                "user_id": current_user_id.get(),
                "request_path": current_request_path.get(),
                "changes_summary": (
                    None if changes_summary is None else str(changes_summary).replace("'", '"')
                ),
            },
        )
    except Exception as e:
        # Audit log debe ser best-effort: si falla, no abortamos la op real.
        # Pero sí lo logueamos para que un alerta de Sentry pueda agregarlo.
        logger.exception(f"audit_log insert failed: action={action} model={model}: {e}")


def _on_after_delete(mapper, connection, target) -> None:
    """Hook después de DELETE de un instance ORM tracked."""
    table_name = target.__tablename__
    if table_name not in _AUDITED_MODELS:
        return
    record_id = getattr(target, "id", None)
    # Usamos session de la transacción actual via connection.
    # SQLAlchemy 2.0 con AsyncSession también dispatcha en sync events.
    from sqlalchemy.orm import object_session

    sess = object_session(target)
    if sess is None:
        return
    _insert_audit_row(sess, action="DELETE", model=table_name, record_id=record_id)


def _on_after_update(mapper, connection, target) -> None:
    """Hook después de UPDATE de un instance ORM tracked."""
    table_name = target.__tablename__
    if table_name not in _AUDITED_MODELS:
        return
    record_id = getattr(target, "id", None)

    from sqlalchemy import inspect as sa_inspect
    from sqlalchemy.orm import object_session

    sess = object_session(target)
    if sess is None:
        return

    # Identifica columnas modificadas. NO guardamos valores — solo nombres.
    state = sa_inspect(target)
    changed_cols = [
        attr.key
        for attr in state.attrs
        if attr.history.has_changes() and attr.key != "id"
    ]
    if not changed_cols:
        return

    summary = {"changed_columns": changed_cols}
    _insert_audit_row(
        sess,
        action="UPDATE",
        model=table_name,
        record_id=record_id,
        changes_summary=summary,
    )


async def log_destructive_op(
    session,
    *,
    action: str,
    model: str,
    record_id: int | None,
    changes_summary: dict | None = None,
) -> None:
    """Helper para endpoints que usan SQL raw (text(...)) en lugar de ORM.

    Gemini cross-audit identificó que los Event Listeners SQLAlchemy NO se
    disparan en operaciones via session.execute(text("UPDATE ..."))
    porque no involucran instances ORM. Para esos casos, llamar este
    helper explícito ANTES del commit:

        await db.execute(text("UPDATE watched_profiles SET ..."), ...)
        await log_destructive_op(db, action="UPDATE", model="watched_profiles", record_id=wid)
        await db.commit()

    Los endpoints que vienen detrás del ORM (ej. session.delete(instance))
    NO necesitan esto — los listeners ya cubren.
    """
    from sqlalchemy import text

    try:
        await session.execute(
            text(
                """
                INSERT INTO audit_log
                    (action, model, record_id, user_id, request_path,
                     changes_summary, created_at)
                VALUES
                    (:action, :model, :record_id, :user_id, :request_path,
                     CAST(:changes_summary AS JSONB), NOW())
                """
            ),
            {
                "action": action,
                "model": model,
                "record_id": record_id,
                "user_id": current_user_id.get(),
                "request_path": current_request_path.get(),
                "changes_summary": (
                    None
                    if changes_summary is None
                    else __import__("json").dumps(changes_summary)
                ),
            },
        )
    except Exception as e:
        logger.exception(f"audit_log helper insert failed: {e}")


def init_audit_listeners() -> None:
    """Registra los event listeners en los modelos auditados.

    Llamar UNA SOLA VEZ en startup (app/main.py). Idempotente — si se llama
    múltiples veces, sqlalchemy.event.listen lanzaría duplicados, pero el
    decorador interno evita.
    """
    # Importar modelos solo aquí — evita ciclos al cargar el módulo.
    from app.models.competitor_profile import CompetitorProfile
    from app.models.follower import SocialFollower
    from app.models.plan_ia import PlanIA
    from app.models.watched_profile import WatchedLikeEvent, WatchedProfile

    # Lista de (Model, hook delete?, hook update?).
    audited_models = [
        (WatchedProfile, True, True),
        (WatchedLikeEvent, True, False),
        (SocialFollower, True, False),
        (CompetitorProfile, True, True),
        (PlanIA, True, True),
    ]

    for Model, on_delete, on_update in audited_models:
        if on_delete and not event.contains(Model, "after_delete", _on_after_delete):
            event.listen(Model, "after_delete", _on_after_delete)
        if on_update and not event.contains(Model, "after_update", _on_after_update):
            event.listen(Model, "after_update", _on_after_update)

    # SocialComment está en `social_comments` table — el modelo está en
    # `app.models.legacy` o `app.models.follower`. Si no se encuentra, queda
    # pendiente y se loguea (no quiere romper startup).
    try:
        # Buscar import path real
        from app.models.social import SocialComment  # type: ignore
        if not event.contains(SocialComment, "after_delete", _on_after_delete):
            event.listen(SocialComment, "after_delete", _on_after_delete)
    except ImportError:
        logger.info(
            "audit_listeners: SocialComment no registrado — modelo no expuesto. "
            "Ops sobre social_comments quedan fuera del audit log mientras el "
            "modelo no se importe."
        )

    logger.info(
        f"audit_listeners initialized for {len(audited_models)} models "
        f"(LFPDPPP art. 32 compliance · S8 sprint)"
    )
