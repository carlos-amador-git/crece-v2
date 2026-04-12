from __future__ import annotations

import enum
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Platform(str, enum.Enum):
    TWITTER = "TWITTER"
    INSTAGRAM = "INSTAGRAM"
    FACEBOOK = "FACEBOOK"
    TIKTOK = "TIKTOK"
    YOUTUBE = "YOUTUBE"
    BLUESKY = "BLUESKY"
    THREADS = "THREADS"
    TELEGRAM = "TELEGRAM"
    NEWS = "NEWS"

    @classmethod
    def from_url(cls, url: str) -> "Platform | None":
        """Detect the platform of a given URL.

        Returns the matching Platform or None if no known pattern matches.
        Unifies ad-hoc regex detection previously scattered across services.
        """
        if not url:
            return None

        u = url.lower().strip()
        if u.startswith(("http://", "https://")):
            u = u.split("://", 1)[1]
        u = u.split("/", 1)[0] if "/" in u else u
        if u.startswith("www."):
            u = u[4:]

        host_map: dict[str, "Platform"] = {
            "twitter.com": cls.TWITTER,
            "x.com": cls.TWITTER,
            "mobile.twitter.com": cls.TWITTER,
            "nitter.net": cls.TWITTER,
            "instagram.com": cls.INSTAGRAM,
            "instagr.am": cls.INSTAGRAM,
            "facebook.com": cls.FACEBOOK,
            "fb.com": cls.FACEBOOK,
            "fb.watch": cls.FACEBOOK,
            "m.facebook.com": cls.FACEBOOK,
            "tiktok.com": cls.TIKTOK,
            "vm.tiktok.com": cls.TIKTOK,
            "youtube.com": cls.YOUTUBE,
            "m.youtube.com": cls.YOUTUBE,
            "youtu.be": cls.YOUTUBE,
            "bsky.app": cls.BLUESKY,
            "bsky.social": cls.BLUESKY,
            "threads.net": cls.THREADS,
            "t.me": cls.TELEGRAM,
            "telegram.me": cls.TELEGRAM,
            "telegram.org": cls.TELEGRAM,
        }
        if u in host_map:
            return host_map[u]

        for host, platform in host_map.items():
            if u.endswith("." + host):
                return platform

        return None


class SentimentLabel(str, enum.Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"
    MIXED = "MIXED"


class PostType(str, enum.Enum):
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    REEL = "REEL"
    STORY = "STORY"
    CAROUSEL = "CAROUSEL"


class SocialProfile(Base):
    __tablename__ = "social_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dirigente_id: Mapped[int] = mapped_column(
        ForeignKey("dirigentes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    platform: Mapped[Platform] = mapped_column(
        Enum(Platform, name="platform_enum", create_type=False),
        nullable=False,
    )
    handle: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    followers_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    following_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    posts_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_scraped_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    dirigente = relationship("Dirigente", back_populates="social_profiles")
    posts: Mapped[list[SocialPost]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )


class SocialPost(Base):
    __tablename__ = "social_posts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("social_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    platform_post_id: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    post_type: Mapped[PostType] = mapped_column(
        Enum(PostType, name="post_type_enum", create_type=False),
        nullable=False,
    )
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    likes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comments: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    shares: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    engagement_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    sentiment_label: Mapped[SentimentLabel | None] = mapped_column(
        Enum(SentimentLabel, name="sentiment_label_enum", create_type=False),
        nullable=True,
    )
    emotions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_political: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    raw_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    profile: Mapped[SocialProfile] = relationship(back_populates="posts")
    sentiment_analyses: Mapped[list[SentimentAnalysis]] = relationship(
        back_populates="post", cascade="all, delete-orphan"
    )


class SentimentAnalysis(Base):
    __tablename__ = "sentiment_analyses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(
        ForeignKey("social_posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    model_used: Mapped[str] = mapped_column(String(100), nullable=False)
    sentiment_score: Mapped[float] = mapped_column(Float, nullable=False)
    sentiment_label: Mapped[SentimentLabel] = mapped_column(
        Enum(SentimentLabel, name="sentiment_label_enum", create_type=False),
        nullable=False,
    )
    emotions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    topics: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_toxic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    toxicity_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    propaganda_labels: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    post: Mapped[SocialPost] = relationship(back_populates="sentiment_analyses")
