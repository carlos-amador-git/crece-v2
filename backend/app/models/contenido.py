from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class FormatoContenido(StrEnum):
    POST_TWITTER = "post_twitter"
    POST_INSTAGRAM = "post_instagram"
    POST_FACEBOOK = "post_facebook"
    REEL_SCRIPT = "reel_script"
    THREAD_TWITTER = "thread_twitter"
    INFOGRAFIA_COPY = "infografia_copy"
    COMUNICADO = "comunicado"


class EstadoContenido(StrEnum):
    BORRADOR = "borrador"
    REVISADO = "revisado"
    APROBADO = "aprobado"
    PUBLICADO = "publicado"
    RECHAZADO = "rechazado"


# Valid state transitions: borrador -> revisado -> aprobado -> publicado
#                          borrador -> rechazado
#                          revisado -> rechazado
_VALID_TRANSITIONS: dict[EstadoContenido, set[EstadoContenido]] = {
    EstadoContenido.BORRADOR: {EstadoContenido.REVISADO, EstadoContenido.RECHAZADO},
    EstadoContenido.REVISADO: {EstadoContenido.APROBADO, EstadoContenido.RECHAZADO},
    EstadoContenido.APROBADO: {EstadoContenido.PUBLICADO},
    EstadoContenido.PUBLICADO: set(),
    EstadoContenido.RECHAZADO: set(),
}


def is_valid_transition(current: EstadoContenido, target: EstadoContenido) -> bool:
    """Check whether a content state transition is allowed."""
    return target in _VALID_TRANSITIONS.get(current, set())


class ContenidoGenerado(Base):
    __tablename__ = "contenidos_generados"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    dirigente_id: Mapped[int] = mapped_column(
        ForeignKey("dirigentes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    generado_por_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    org_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizaciones.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Content fields
    formato: Mapped[FormatoContenido] = mapped_column(
        Enum(FormatoContenido, name="formato_contenido", native_enum=True),
        nullable=False,
    )
    tema: Mapped[str] = mapped_column(String(255), nullable=False)
    tono: Mapped[str] = mapped_column(String(50), nullable=False)
    contenido: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_usado: Mapped[str] = mapped_column(Text, nullable=False)

    # Metadata
    plataforma_destino: Mapped[str] = mapped_column(String(50), nullable=False)
    estado: Mapped[EstadoContenido] = mapped_column(
        Enum(EstadoContenido, name="estado_contenido", native_enum=True),
        default=EstadoContenido.BORRADOR,
        nullable=False,
    )
    modelo_ia: Mapped[str] = mapped_column(String(100), nullable=False)
    tokens_input: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_output: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # INE compliance — every AI-generated content must be labeled
    etiqueta_ia: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

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

    # Relationships
    dirigente = relationship("Dirigente", lazy="selectin")
    generado_por = relationship("User", lazy="selectin")
    organizacion = relationship("Organizacion", lazy="selectin")
