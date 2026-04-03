from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.models.ciudadano import Genero, NivelInteres, RangoEdad


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
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
