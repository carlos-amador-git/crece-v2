from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DirigenteSyncStatus(StrEnum):
    PENDING = "pending"
    SCRAPING = "scraping"
    ANALYZING = "analyzing"
    CALCULATING_IPD = "calculating_ipd"
    READY = "ready"
    ERROR = "error"


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
    sync_status: Mapped[DirigenteSyncStatus] = mapped_column(
        Enum(
            DirigenteSyncStatus,
            name="dirigente_sync_status",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=DirigenteSyncStatus.READY,
    )
    sync_task_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    sync_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Sprint S1 — data fidelity + estrato + competidores (MASTER §5 S1 T1/T2)
    data_fidelity_tier: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    estrato_politico: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Lista de IDs de competidores directos declarados por el cliente.
    # Durante Sprint S2 se pobla vía fixture de desarrollo D-22:
    #   backend/scripts/seed_proxies_desarrollo_s2.py
    # En Sprint S5 este campo será declarado por el cliente en el Onboarding
    # Wizard (pantalla "¿Contra quién compites?"). El fixture S2 es DESCARTABLE.
    competidor_directo_ids: Mapped[list[int]] = mapped_column(
        ARRAY(Integer),
        nullable=False,
        server_default="{}",
        default=list,
    )
    data_origin: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        server_default="T3",
        default="T3",
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
