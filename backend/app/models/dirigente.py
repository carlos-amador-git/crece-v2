from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Dirigente(Base):
    __tablename__ = "dirigentes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    cargo: Mapped[str] = mapped_column(String(255), nullable=False)
    partido: Mapped[str] = mapped_column(String(50), default="MC", nullable=False)
    estado: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    municipio: Mapped[str] = mapped_column(String(200), nullable=True)
    seccion_electoral: Mapped[str | None] = mapped_column(String(10), nullable=True)
    org_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizaciones.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # relationships
    organizacion = relationship("Organizacion", lazy="selectin")
    social_profiles = relationship(
        "SocialProfile",
        back_populates="dirigente",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    planes = relationship(
        "PlanIA",
        back_populates="dirigente",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
