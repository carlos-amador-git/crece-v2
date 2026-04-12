"""D-DATA-01 Ruta C — modelos paralelos para snapshot del CRECE legacy.

Convivencia intencional con las tablas v2 (`ciudadanos`, `users`):
- v2 tiene constraints de enum/FK fuertes que no caben con los datos del
  Oracle APEX original (sección electoral no poblada, passwords Oracle,
  etc.).
- legacy_* preserva el snapshot 1:1 y permite query en paralelo sin
  forzar el esquema v2.
- Ambas tablas tienen RLS por `org_id` (tenant-scoped strict).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PromotorLegacy(Base):
    __tablename__ = "promotores_legacy"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    legacy_user_id: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
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
    user_name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    password_hash_legacy: Mapped[str | None] = mapped_column(String(200), nullable=True)
    project_id_legacy: Mapped[str | None] = mapped_column(String(50), nullable=True)
    enabled: Mapped[str | None] = mapped_column(String(5), nullable=True)
    super_promotor: Mapped[str | None] = mapped_column(String(5), nullable=True)
    mega_promotor: Mapped[str | None] = mapped_column(String(5), nullable=True)
    super_promotor_cdmx: Mapped[str | None] = mapped_column(String(5), nullable=True)
    distrito_federal: Mapped[str | None] = mapped_column(String(10), nullable=True)
    distritos: Mapped[str | None] = mapped_column(String(100), nullable=True)
    distrito_local: Mapped[str | None] = mapped_column(String(10), nullable=True)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class CiudadanoLegacy(Base):
    __tablename__ = "ciudadanos_legacy"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    legacy_id: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
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
    unidad_territorial_id: Mapped[int | None] = mapped_column(
        ForeignKey("unidades_territoriales.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    promotor_legacy_id: Mapped[int | None] = mapped_column(
        ForeignKey("promotores_legacy.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    nombre: Mapped[str | None] = mapped_column(String(255), nullable=True)
    apellido_paterno: Mapped[str | None] = mapped_column(String(255), nullable=True)
    apellido_materno: Mapped[str | None] = mapped_column(String(255), nullable=True)
    edad: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sexo: Mapped[str | None] = mapped_column(String(10), nullable=True)
    identidad_de_genero: Mapped[str | None] = mapped_column(String(50), nullable=True)

    calle: Mapped[str | None] = mapped_column(String(255), nullable=True)
    numero: Mapped[str | None] = mapped_column(String(50), nullable=True)
    numero_interior: Mapped[str | None] = mapped_column(String(50), nullable=True)
    colonia_texto: Mapped[str | None] = mapped_column(String(255), nullable=True)
    codigo_postal: Mapped[str | None] = mapped_column(String(10), nullable=True)
    municipio_texto: Mapped[str | None] = mapped_column(String(255), nullable=True)
    direccion_libre: Mapped[str | None] = mapped_column(Text, nullable=True)
    manzana: Mapped[str | None] = mapped_column(String(50), nullable=True)

    latitud: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitud: Mapped[float | None] = mapped_column(Float, nullable=True)
    latitud_cd: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitud_cd: Mapped[float | None] = mapped_column(Float, nullable=True)

    seccion: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    cabecera_territorial: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # clave_electoral clear column dropped (D-DATA-02c) — use clave_electoral_enc
    origen_ciudadano: Mapped[str | None] = mapped_column(String(50), nullable=True)
    rol: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ocupacion: Mapped[str | None] = mapped_column(String(255), nullable=True)
    nivel_educativo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    nivel_participacion: Mapped[str | None] = mapped_column(String(50), nullable=True)
    disposicion_tiempo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    temas_de_interes: Mapped[str | None] = mapped_column(Text, nullable=True)
    red_social: Mapped[str | None] = mapped_column(String(50), nullable=True)
    red_social_descripcion: Mapped[str | None] = mapped_column(String(500), nullable=True)
    residencia_si_no: Mapped[str | None] = mapped_column(String(5), nullable=True)

    contactado: Mapped[str | None] = mapped_column(String(10), nullable=True)
    respuesta: Mapped[str | None] = mapped_column(Text, nullable=True)
    lista: Mapped[str | None] = mapped_column(String(50), nullable=True)
    aprobado: Mapped[str | None] = mapped_column(String(10), nullable=True)
    procesado: Mapped[str | None] = mapped_column(String(10), nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    id_mc: Mapped[str | None] = mapped_column(String(50), nullable=True)

    username_legacy: Mapped[str | None] = mapped_column(String(100), nullable=True)
    project_id_legacy: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_legacy: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by_legacy: Mapped[str | None] = mapped_column(String(100), nullable=True)
    updated_legacy: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_by_legacy: Mapped[str | None] = mapped_column(String(100), nullable=True)
    raw_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    promotor = relationship("PromotorLegacy", lazy="noload")
