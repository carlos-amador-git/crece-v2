from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, field_validator

from app.models.evento import EstadoEvento, TipoEvento


class EventoCreate(BaseModel):
    titulo: str
    descripcion: str | None = None
    tipo: TipoEvento
    fecha_inicio: datetime
    fecha_fin: datetime | None = None
    lugar: str
    latitud: float | None = None
    longitud: float | None = None
    seccion_id: int | None = None
    dirigente_id: int | None = None
    asistentes_esperados: int | None = None
    notas: str | None = None
    # ── New fields ──────────────────────────────────────
    recursos: dict | None = None
    nuevos_simpatizantes: int | None = None
    costo_total: float | None = None
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


class EventoUpdate(BaseModel):
    titulo: str | None = None
    descripcion: str | None = None
    tipo: TipoEvento | None = None
    fecha_inicio: datetime | None = None
    fecha_fin: datetime | None = None
    lugar: str | None = None
    latitud: float | None = None
    longitud: float | None = None
    seccion_id: int | None = None
    dirigente_id: int | None = None
    asistentes_esperados: int | None = None
    asistentes_reales: int | None = None
    estado: EstadoEvento | None = None
    notas: str | None = None
    # ── New fields ──────────────────────────────────────
    recursos: dict | None = None
    nuevos_simpatizantes: int | None = None
    costo_total: float | None = None
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


class EventoResponse(BaseModel):
    id: int
    titulo: str
    descripcion: str | None
    tipo: TipoEvento
    fecha_inicio: datetime
    fecha_fin: datetime | None
    lugar: str
    seccion_id: int | None
    dirigente_id: int | None
    organizador_id: int
    asistentes_esperados: int | None
    asistentes_reales: int | None
    estado: EstadoEvento
    notas: str | None
    # ── New fields ──────────────────────────────────────
    recursos: dict | None
    nuevos_simpatizantes: int | None
    costo_total: float | None
    costo_por_adquisicion: float | None
    org_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EventoAsistenteCreate(BaseModel):
    ciudadano_id: int
    confirmado: bool = False


class EventoAsistenteResponse(BaseModel):
    id: int
    evento_id: int
    ciudadano_id: int
    confirmado: bool
    asistio: bool

    model_config = {"from_attributes": True}


class EventoCompletarPayload(BaseModel):
    asistentes_reales: int | None = None
    notas: str | None = None


class EventoROIResponse(BaseModel):
    """Aggregated ROI metrics for events with cost data."""

    total_eventos: int
    costo_total_sum: float
    asistentes_reales_sum: int
    nuevos_simpatizantes_sum: int
    costo_promedio_por_evento: float
    costo_promedio_por_asistente: float | None
    costo_promedio_por_simpatizante: float | None
