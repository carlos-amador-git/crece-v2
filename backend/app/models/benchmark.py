from __future__ import annotations

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Competidor(Base):
    __tablename__ = "competidores"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    partido: Mapped[str] = mapped_column(String(50), nullable=False)
    cargo: Mapped[str] = mapped_column(String(255), nullable=False)
    es_rival: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    social_profiles: Mapped[list[CompetidorSocialProfile]] = relationship(
        back_populates="competidor", cascade="all, delete-orphan", lazy="selectin"
    )


class CompetidorSocialProfile(Base):
    __tablename__ = "competidor_social_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    competidor_id: Mapped[int] = mapped_column(
        ForeignKey("competidores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    platform: Mapped[str] = mapped_column(
        Enum(
            "TWITTER",
            "INSTAGRAM",
            "FACEBOOK",
            "TIKTOK",
            "YOUTUBE",
            "BLUESKY",
            name="platform_enum",
            create_type=False,
        ),
        nullable=False,
    )
    handle: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    followers_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    following_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    posts_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    competidor: Mapped[Competidor] = relationship(back_populates="social_profiles")
