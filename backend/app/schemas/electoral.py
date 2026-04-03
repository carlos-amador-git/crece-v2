from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, field_validator


class SeccionElectoralResponse(BaseModel):
    id: int
    seccion: str
    estado: str
    distrito_federal: str
    distrito_local: str
    municipio: str

    model_config = {"from_attributes": True}


class SeccionGeoJSONFeature(BaseModel):
    type: str = "Feature"
    properties: SeccionElectoralResponse
    geometry: dict[str, Any] | None


class SeccionGeoJSONCollection(BaseModel):
    type: str = "FeatureCollection"
    features: list[SeccionGeoJSONFeature]


class IntencionVotoCreate(BaseModel):
    seccion_id: int
    dirigente_id: int | None = None
    periodo: str
    muestra: int
    a_favor: float
    en_contra: float
    indeciso: float
    no_responde: float
    fecha_encuesta: date

    @field_validator("a_favor", "en_contra", "indeciso", "no_responde")
    @classmethod
    def validate_percentage(cls, v: float) -> float:
        if not 0.0 <= v <= 100.0:
            raise ValueError("Percentage must be between 0 and 100")
        return v


class IntencionVotoResponse(BaseModel):
    id: int
    seccion_id: int
    dirigente_id: int | None
    periodo: str
    muestra: int
    a_favor: float
    en_contra: float
    indeciso: float
    no_responde: float
    fecha_encuesta: date
    capturado_por_id: int
    created_at: datetime

    model_config = {"from_attributes": True}
