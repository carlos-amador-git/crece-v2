from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, field_validator

from app.models.ciudadano import IntencionVotoCiudadano
from app.models.encuesta import NivelCerteza


class EncuestaCreate(BaseModel):
    ciudadano_id: int
    seccion_id: int | None = None
    intencion_voto: IntencionVotoCiudadano
    nivel_certeza: NivelCerteza = NivelCerteza.MEDIA
    motivacion: str | None = None
    problematicas_detectadas: list[dict] | None = None
    latitud: float | None = None
    longitud: float | None = None
    fecha_encuesta: date
    duracion_minutos: int | None = None
    notas: str | None = None

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


class EncuestaUpdate(BaseModel):
    intencion_voto: IntencionVotoCiudadano | None = None
    nivel_certeza: NivelCerteza | None = None
    motivacion: str | None = None
    problematicas_detectadas: list[dict] | None = None
    notas: str | None = None


class EncuestaResponse(BaseModel):
    id: int
    ciudadano_id: int
    encuestador_id: int
    org_id: int | None
    seccion_id: int | None
    intencion_voto: IntencionVotoCiudadano
    nivel_certeza: NivelCerteza
    motivacion: str | None
    problematicas_detectadas: list[dict] | None
    fecha_encuesta: date
    duracion_minutos: int | None
    notas: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class EncuestaResumen(BaseModel):
    """Aggregated vote intention stats for a section or period."""

    seccion_id: int | None = None
    total_encuestas: int
    intencion_voto_breakdown: dict[str, int]
    periodo: str | None = None
