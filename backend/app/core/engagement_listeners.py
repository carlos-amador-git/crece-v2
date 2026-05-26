"""SQLAlchemy event listeners: calcula engagement_rate al persistir SocialPost.

Cubre TODAS las rutas de ingest ORM (scrapers youtube/tiktok/facebook/telegram +
workers + futuros) en INSERT y UPDATE. Los scrapers actualizan likes/comments de
posts existentes sin recalcular ER — el hook de UPDATE cierra ese hueco.

Las rutas de SQL crudo (scripts de ingest RADAR/Apify) NO pasan por ORM; esas
importan ``compute_engagement_rate`` directamente.

Eficiencia: en UPDATE solo recalcula si cambió una métrica (likes/comments/shares/
views) — así un backfill NLP que solo toca tono/topics no dispara queries de
followers innecesarias.
"""
from __future__ import annotations

import logging

from sqlalchemy import event, inspect, text

from app.services.engagement import compute_engagement_rate

logger = logging.getLogger(__name__)

_METRIC_FIELDS = ("likes", "comments", "shares", "views")


def _apply_engagement_rate(connection, target) -> None:
    likes = target.likes or 0
    comments = target.comments or 0
    shares = target.shares or 0
    views = target.views or 0

    if (likes + comments + shares) == 0:
        target.engagement_rate = 0.0
        return

    followers = 0
    # followers solo se necesita para la fórmula sin-views (X/FB)
    if not (views and views > 0):
        row = connection.execute(
            text("SELECT followers_count FROM social_profiles WHERE id = :pid"),
            {"pid": target.profile_id},
        ).first()
        followers = (row[0] if row else 0) or 0

    target.engagement_rate = compute_engagement_rate(
        likes, comments, shares, views, followers
    )


def _on_before_insert(mapper, connection, target) -> None:
    _apply_engagement_rate(connection, target)


def _on_before_update(mapper, connection, target) -> None:
    insp = inspect(target)
    if any(insp.attrs[f].history.has_changes() for f in _METRIC_FIELDS):
        _apply_engagement_rate(connection, target)


def init_engagement_listeners() -> None:
    """Registra los listeners en SocialPost. Idempotente. Llamar en startup."""
    from app.models.social import SocialPost

    if not event.contains(SocialPost, "before_insert", _on_before_insert):
        event.listen(SocialPost, "before_insert", _on_before_insert)
    if not event.contains(SocialPost, "before_update", _on_before_update):
        event.listen(SocialPost, "before_update", _on_before_update)
    logger.info("engagement_rate listeners registrados en SocialPost")
