from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.campana import EstadoCampana, EstadoMensaje, TipoCampana


# ── CampanaSegmento schemas ─────────────────────────────


class CampanaSegmentoCreate(BaseModel):
    filtro_seccion_id: int | None = None
    filtro_intencion_voto: str | None = None
    filtro_edad_rango: str | None = None
    filtro_escolaridad: str | None = None
    filtro_es_simpatizante: bool | None = None
    filtro_es_promotor: bool | None = None
    filtro_score_min: float | None = Field(None, ge=0.0, le=1.0)
    filtro_score_max: float | None = Field(None, ge=0.0, le=1.0)


class CampanaSegmentoResponse(BaseModel):
    id: int
    campana_id: int
    filtro_seccion_id: int | None
    filtro_intencion_voto: str | None
    filtro_edad_rango: str | None
    filtro_escolaridad: str | None
    filtro_es_simpatizante: bool | None
    filtro_es_promotor: bool | None
    filtro_score_min: float | None
    filtro_score_max: float | None
    ciudadanos_count: int

    model_config = {"from_attributes": True}


# ── Campana schemas ──────────────────────────────────────


class CampanaCreate(BaseModel):
    org_id: int
    nombre: str = Field(..., min_length=1, max_length=255)
    descripcion: str | None = None
    tipo: TipoCampana
    plantilla_mensaje: str = Field(..., min_length=1)
    variables_plantilla: dict | None = None
    fecha_programada: datetime | None = None
    dirigente_id: int | None = None


class CampanaUpdate(BaseModel):
    nombre: str | None = Field(None, min_length=1, max_length=255)
    descripcion: str | None = None
    tipo: TipoCampana | None = None
    plantilla_mensaje: str | None = Field(None, min_length=1)
    variables_plantilla: dict | None = None
    estado: EstadoCampana | None = None
    fecha_programada: datetime | None = None
    dirigente_id: int | None = None


class CampanaResponse(BaseModel):
    id: int
    org_id: int
    nombre: str
    descripcion: str | None
    tipo: TipoCampana
    plantilla_mensaje: str
    variables_plantilla: dict | None
    estado: EstadoCampana
    fecha_programada: datetime | None
    fecha_envio: datetime | None
    fecha_completada: datetime | None
    creado_por_id: int
    dirigente_id: int | None
    total_destinatarios: int
    total_enviados: int
    total_entregados: int
    total_leidos: int
    total_respondidos: int
    segmentos: list[CampanaSegmentoResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── CampanaMensaje schemas ──────────────────────────────


class CampanaMensajeResponse(BaseModel):
    id: int
    campana_id: int
    ciudadano_id: int
    telefono: str
    estado: EstadoMensaje
    chatwoot_message_id: str | None
    enviado_at: datetime | None
    entregado_at: datetime | None
    leido_at: datetime | None
    error_mensaje: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Analytics schemas ────────────────────────────────────


class CampanaAnalytics(BaseModel):
    campana_id: int
    nombre: str
    estado: EstadoCampana
    total_destinatarios: int
    total_enviados: int
    total_entregados: int
    total_leidos: int
    total_respondidos: int
    total_fallidos: int
    tasa_envio: float = Field(description="Sent / Total recipients")
    tasa_entrega: float = Field(description="Delivered / Sent")
    tasa_lectura: float = Field(description="Read / Delivered")
    tasa_respuesta: float = Field(description="Replied / Delivered")
    tasa_fallo: float = Field(description="Failed / Total recipients")


class CampanaPreviewResponse(BaseModel):
    campana_id: int
    total_destinatarios: int
    sample_mensajes: list[dict]


# ── Webhook schemas ──────────────────────────────────────


class DeliveryWebhookPayload(BaseModel):
    mensaje_id: int
    status: EstadoMensaje
    chatwoot_message_id: str | None = None
    error: str | None = None
