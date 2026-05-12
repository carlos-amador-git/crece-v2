from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator

from app.models.ciudadano import (
    Escolaridad,
    Genero,
    IntencionVotoCiudadano,
    NivelInteres,
    RangoEdad,
)


class CiudadanoCreate(BaseModel):
    nombre: str
    apellido_paterno: str
    apellido_materno: str | None = None
    seccion_id: int
    direccion: str | None = None
    telefono: str | None = None
    email: EmailStr | None = None
    edad_rango: RangoEdad
    genero: Genero = Genero.NO_ESPECIFICADO
    nivel_interes: NivelInteres = NivelInteres.DESCONOCIDO
    es_simpatizante_mc: bool = False
    es_promotor: bool = False
    notas: str | None = None
    # ── New fields ──────────────────────────────────────
    intencion_voto: IntencionVotoCiudadano | None = None
    programas_sociales: list[dict] | None = None
    problematicas: list[dict] | None = None
    latitud: float | None = None
    longitud: float | None = None
    colonia: str | None = None
    codigo_postal: str | None = None
    escolaridad: Escolaridad | None = None
    foto_ine_url: str | None = None
    org_id: int | None = None

    @field_validator("latitud")
    @classmethod
    def validate_latitud(cls, v: float | None) -> float | None:
        if v is not None and not (14.5 <= v <= 32.7):
            raise ValueError("Latitude must be within Mexico bounds (14.5-32.7)")
        return v

    @field_validator("longitud")
    @classmethod
    def validate_longitud(cls, v: float | None) -> float | None:
        if v is not None and not (-118.4 <= v <= -86.7):
            raise ValueError("Longitude must be within Mexico bounds (-118.4 to -86.7)")
        return v


class CiudadanoUpdate(BaseModel):
    nombre: str | None = None
    apellido_paterno: str | None = None
    apellido_materno: str | None = None
    seccion_id: int | None = None
    direccion: str | None = None
    telefono: str | None = None
    email: EmailStr | None = None
    edad_rango: RangoEdad | None = None
    genero: Genero | None = None
    nivel_interes: NivelInteres | None = None
    es_simpatizante_mc: bool | None = None
    es_promotor: bool | None = None
    notas: str | None = None
    # ── New fields ──────────────────────────────────────
    intencion_voto: IntencionVotoCiudadano | None = None
    programas_sociales: list[dict] | None = None
    problematicas: list[dict] | None = None
    latitud: float | None = None
    longitud: float | None = None
    colonia: str | None = None
    codigo_postal: str | None = None
    escolaridad: Escolaridad | None = None
    foto_ine_url: str | None = None
    org_id: int | None = None

    @field_validator("latitud")
    @classmethod
    def validate_latitud(cls, v: float | None) -> float | None:
        if v is not None and not (14.5 <= v <= 32.7):
            raise ValueError("Latitude must be within Mexico bounds (14.5-32.7)")
        return v

    @field_validator("longitud")
    @classmethod
    def validate_longitud(cls, v: float | None) -> float | None:
        if v is not None and not (-118.4 <= v <= -86.7):
            raise ValueError("Longitude must be within Mexico bounds (-118.4 to -86.7)")
        return v


class CiudadanoResponse(BaseModel):
    id: int
    nombre: str
    apellido_paterno: str
    apellido_materno: str | None
    seccion_id: int
    direccion: str | None
    telefono: str | None
    email: str | None
    edad_rango: RangoEdad
    genero: Genero
    nivel_interes: NivelInteres
    es_simpatizante_mc: bool
    es_promotor: bool
    notas: str | None
    registrado_por_id: int
    # ── New fields ──────────────────────────────────────
    intencion_voto: IntencionVotoCiudadano | None
    programas_sociales: list | dict | None
    problematicas: list | dict | None
    colonia: str | None
    codigo_postal: str | None
    escolaridad: Escolaridad | None
    foto_ine_url: str | None
    org_id: int | None
    data_source: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
