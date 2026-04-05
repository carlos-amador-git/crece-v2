from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Competidor(Base):
    __tablename__ = "competidores"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    partido: Mapped[str] = mapped_column(String(50), nullable=False)
    cargo: Mapped[str] = mapped_column(String(255), nullable=False)
    es_rival: Mapped[bool] = mapped_column(Boolean, nullable=False)

    # relationships
    social_profiles = relationship(
        "CompetidorSocialProfile",
        back_populates="competidor",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class CompetidorSocialProfile(Base):
    __tablename__ = "competidor_social_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    competidor_id: Mapped[int] = mapped_column(
        ForeignKey("competidores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    handle: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    followers_count: Mapped[int] = mapped_column(Integer, nullable=False)
    following_count: Mapped[int] = mapped_column(Integer, nullable=False)
    posts_count: Mapped[int] = mapped_column(Integer, nullable=False)
    last_scraped_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # relationships
    competidor = relationship("Competidor", back_populates="social_profiles", lazy="selectin")
