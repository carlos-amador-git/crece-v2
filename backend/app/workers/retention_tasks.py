"""LFPDPPP retention: cleanup automático de social_comments >180d.

Preserva métricas agregadas (IA scores calculados quedan en BD) pero
elimina contenido + author_hash de comments >180d. Cumple con
Aviso de Privacidad CRECE.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import text

from app.core.database import sync_session_factory
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

RETENTION_DAYS = 180


@celery_app.task(name="app.workers.retention_tasks.cleanup_old_comments")
def cleanup_old_comments() -> dict:
    """Borra social_comments con created_at < NOW - 180 días.

    Los IA scores agregados por post se mantienen porque ya fueron
    persistidos en otros lugares (agregación). Solo se borra el contenido
    individual + hash.
    """
    cutoff = datetime.now(UTC) - timedelta(days=RETENTION_DAYS)

    with sync_session_factory() as session:
        result = session.execute(
            text("DELETE FROM social_comments WHERE created_at < :cutoff"),
            {"cutoff": cutoff},
        )
        deleted = result.rowcount or 0
        session.commit()

    logger.info("LFPDPPP retention: %d comments deleted (>%dd)", deleted, RETENTION_DAYS)
    return {"deleted": deleted, "cutoff": cutoff.isoformat(), "retention_days": RETENTION_DAYS}
