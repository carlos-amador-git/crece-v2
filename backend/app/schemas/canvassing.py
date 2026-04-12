"""Pydantic v2 schemas for Smart Canvassing module."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

from app.models.canvassing import EstadoRuta, ResultadoVisita

# ── Mexico coordinate bounds ────────────────────────────────
_MEX_LAT_MIN, _MEX_LAT_MAX = 14.5, 32.7
_MEX_LON_MIN, _MEX_LON_MAX = -118.4, -86.7


# ── Request schemas ─────────────────────────────────────────


class OptimizeRequest(BaseModel):
    """Request body for POST /canvassing/optimize."""

    seccion_id: int
    encuestador_id: int
    fecha: date
    ciudadano_ids: list[int] | None = Field(
        default=None,
        description=(
            "Specific ciudadano IDs to include. If omitted, uses voter score to prioritize."
        ),
    )
    max_puntos: int = Field(default=20, ge=1, le=100)
    priorizar_score: bool = Field(
        default=True,
        description="When True and no ciudadano_ids given, prioritize by voter score descending.",
    )


class RutaCanvassingCreate(BaseModel):
    """Direct creation (without optimization)."""

    seccion_id: int | None = None
    encuestador_id: int
    fecha_asignada: date
    ciudadano_ids: list[int] | None = None


class MarkVisitadoRequest(BaseModel):
    """Request body for PATCH punto visited."""

    resultado: ResultadoVisita
    notas: str | None = None


class NearbyRequest(BaseModel):
    """Query params for nearby ciudadanos search."""

    lat: float = Field(ge=_MEX_LAT_MIN, le=_MEX_LAT_MAX)
    lon: float = Field(ge=_MEX_LON_MIN, le=_MEX_LON_MAX)
    radius_km: float = Field(default=1.0, gt=0, le=50)
    seccion_id: int | None = None

    @field_validator("lat")
    @classmethod
    def validate_lat_mexico(cls, v: float) -> float:
        if not (_MEX_LAT_MIN <= v <= _MEX_LAT_MAX):
            msg = f"Latitude {v} outside Mexico bounds ({_MEX_LAT_MIN}-{_MEX_LAT_MAX})"
            raise ValueError(msg)
        return v

    @field_validator("lon")
    @classmethod
    def validate_lon_mexico(cls, v: float) -> float:
        if not (_MEX_LON_MIN <= v <= _MEX_LON_MAX):
            msg = f"Longitude {v} outside Mexico bounds ({_MEX_LON_MIN}-{_MEX_LON_MAX})"
            raise ValueError(msg)
        return v


# ── Response schemas ────────────────────────────────────────


class PuntoRutaResponse(BaseModel):
    id: int
    orden: int
    ciudadano_id: int
    ciudadano_nombre: str | None = None
    visitado: bool
    visitado_at: datetime | None = None
    resultado: ResultadoVisita | None = None
    notas: str | None = None
    lat: float | None = None
    lon: float | None = None

    model_config = {"from_attributes": True}


class RouteProgressResponse(BaseModel):
    total: int
    completados: int
    porcentaje: float
    distancia_restante_km: float | None = None


class RutaCanvassingResponse(BaseModel):
    id: int
    org_id: int | None = None
    encuestador_id: int
    seccion_id: int | None = None
    nombre: str
    fecha_asignada: date
    estado: EstadoRuta
    distancia_total_km: float | None = None
    tiempo_estimado_min: int | None = None
    puntos_total: int
    puntos_completados: int
    notas: str | None = None
    created_at: datetime
    updated_at: datetime
    puntos: list[PuntoRutaResponse] = []
    progress: RouteProgressResponse | None = None
    geometry_geojson: dict | None = Field(
        default=None,
        description="GeoJSON representation of the route linestring.",
    )

    model_config = {"from_attributes": True}


class NearbyCiudadanoResponse(BaseModel):
    id: int
    nombre: str
    apellido_paterno: str
    apellido_materno: str | None = None
    direccion: str | None = None
    lat: float | None = None
    lon: float | None = None
    distancia_km: float

    model_config = {"from_attributes": True}
