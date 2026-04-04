from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.solicitud import CanalOrigen, EstadoSolicitud, TipoSolicitud


class SolicitudCreate(BaseModel):
    tipo: TipoSolicitud
    titulo: str = Field(..., min_length=1, max_length=255)
    descripcion: str = Field(..., min_length=1)
    canal: CanalOrigen
    latitud: float | None = None
    longitud: float | None = None
    direccion: str | None = Field(None, max_length=500)
    colonia: str | None = Field(None, max_length=255)
    ciudadano_id: int | None = None
    seccion_id: int | None = None
    org_id: int | None = None
    categoria: str | None = Field(None, max_length=100)
    prioridad: int | None = Field(None, ge=1, le=5)
    chatwoot_conversation_id: str | None = None

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


class SolicitudUpdate(BaseModel):
    titulo: str | None = Field(None, min_length=1, max_length=255)
    descripcion: str | None = Field(None, min_length=1)
    tipo: TipoSolicitud | None = None
    latitud: float | None = None
    longitud: float | None = None
    direccion: str | None = Field(None, max_length=500)
    colonia: str | None = Field(None, max_length=255)
    seccion_id: int | None = None
    categoria: str | None = Field(None, max_length=100)
    prioridad: int | None = Field(None, ge=1, le=5)
    estado: EstadoSolicitud | None = None

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


class SolicitudAssign(BaseModel):
    asignado_a_id: int | None = None
    dirigente_responsable_id: int | None = None


class SolicitudRespond(BaseModel):
    respuesta: str = Field(..., min_length=1)


class SeguimientoResponse(BaseModel):
    id: int
    accion: str
    detalle: str
    estado_anterior: str | None
    estado_nuevo: str | None
    usuario_nombre: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SolicitudResponse(BaseModel):
    id: int
    org_id: int | None
    ciudadano_id: int | None
    seccion_id: int | None
    tipo: TipoSolicitud
    titulo: str
    descripcion: str
    canal: CanalOrigen
    direccion: str | None
    colonia: str | None
    categoria: str | None
    prioridad: int
    asignado_a_id: int | None
    dirigente_responsable_id: int | None
    estado: EstadoSolicitud
    respuesta: str | None
    fecha_respuesta: datetime | None
    chatwoot_conversation_id: str | None
    seguimientos: list[SeguimientoResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SolicitudListItem(BaseModel):
    """Lightweight response for list views (no seguimientos)."""

    id: int
    org_id: int | None
    ciudadano_id: int | None
    seccion_id: int | None
    tipo: TipoSolicitud
    titulo: str
    canal: CanalOrigen
    colonia: str | None
    categoria: str | None
    prioridad: int
    estado: EstadoSolicitud
    asignado_a_id: int | None
    dirigente_responsable_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ParticipacionDashboardStats(BaseModel):
    total: int
    by_tipo: dict[str, int]
    by_estado: dict[str, int]
    by_prioridad: dict[str, int]
    avg_resolution_hours: float | None
    top_colonias: list[dict[str, int | str]]


class HeatmapPoint(BaseModel):
    lat: float
    lon: float
    tipo: str
    prioridad: int
    titulo: str


class ChatwootWebhookPayload(BaseModel):
    """Payload from Chatwoot-MX webhook.

    Chatwoot sends event-based webhooks. We handle 'conversation_created'
    and 'message_created' events to intake citizen requests.
    """

    event: str | None = None
    id: int | None = None
    content: str | None = None
    conversation: dict | None = None
    sender: dict | None = None
    account: dict | None = None
    # Allow extra fields from Chatwoot
    model_config = {"extra": "allow"}
