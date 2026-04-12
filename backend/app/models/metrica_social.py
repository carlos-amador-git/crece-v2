from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MetricaSocial(Base):
    __tablename__ = "metricas_sociales"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("social_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Snapshot data
    followers_count: Mapped[int] = mapped_column(Integer, nullable=False)
    following_count: Mapped[int] = mapped_column(Integer, nullable=False)
    posts_count: Mapped[int] = mapped_column(Integer, nullable=False)
    engagement_rate_avg: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Calculated deltas
    followers_delta: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    posts_delta: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Time
    periodo: Mapped[str] = mapped_column(String(50), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("profile_id", "periodo", name="uq_metrica_profile_periodo"),
    )

    # relationships
    profile = relationship("SocialProfile", lazy="selectin")
