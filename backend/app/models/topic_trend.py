from __future__ import annotations

from datetime import UTC, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TopicTrend(Base):
    """Cluster de posts sociales agrupados por similitud semántica y alcaldía.

    Sprint 4 — Motor de Trends MVP. Producido por el worker Celery
    `trends_detector` cada 1h sobre la ventana de 24h de `social_posts`.

    Multi-tenant: `org_id` es obligatorio y hay policy RLS que filtra por
    `current_setting('app.current_org_id')`. El worker DEBE setear el
    org_id antes de la query HNSW (ver S4.8).
    """

    __tablename__ = "topic_trends"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizaciones.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alcaldia_id: Mapped[int | None] = mapped_column(
        ForeignKey("alcaldias_cdmx.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    topic_label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    topic_embedding = mapped_column(Vector(384), nullable=True)
    time_bucket: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    post_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sentiment_avg: Mapped[float | None] = mapped_column(Float, nullable=True)
    growth_rate_24h: Mapped[float | None] = mapped_column(Float, nullable=True)
    sample_posts: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    alcaldia = relationship("AlcaldiaCDMX", lazy="noload")
