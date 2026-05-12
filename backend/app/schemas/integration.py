from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, field_validator

# ── Campaign Schemas ─────────────────────────────────────


class CampaignSegmentRequest(BaseModel):
    """Filters to segment ciudadanos for a WhatsApp or outreach campaign."""

    secciones: list[int] | None = None
    intencion_voto: list[str] | None = None
    rango_edad: list[str] | None = None
    genero: list[str] | None = None
    programa_social: str | None = None
    excluir_contactados_dias: int | None = None
    limit: int = 1000


class CiudadanoSegmentado(BaseModel):
    id: int
    nombre: str
    apellido_paterno: str
    telefono: str
    colonia: str | None
    seccion_id: int
    intencion_voto: str | None

    model_config = {"from_attributes": True}


class CampaignSegmentResponse(BaseModel):
    total: int
    ciudadanos: list[CiudadanoSegmentado]


class CampaignCreateRequest(BaseModel):
    nombre: str
    tipo: str = "whatsapp"
    segmentacion: dict = {}
    tipo_nudge: str | None = None
    programado_para: datetime | None = None


class CampaignResponse(BaseModel):
    id: str  # UUID as string
    nombre: str
    tipo: str
    segmentacion: dict
    tipo_nudge: str | None
    total_destinatarios: int
    enviados: int
    entregados: int
    leidos: int
    respondidos: int
    estado: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Content Factory Schemas ──────────────────────────────


class ContentGenerateRequest(BaseModel):
    """Request to generate multi-platform content for a dirigente."""

    dirigente_id: int
    tema: str
    contexto: str | None = None
    tono: str = "propositivo"
    plataformas: list[str] = ["twitter", "instagram_reel", "facebook"]


class ContentPieceResponse(BaseModel):
    id: str
    dirigente_id: int
    tema: str
    tono: str
    variantes: dict
    modelo_ia: str
    estado: str
    created_at: datetime

    @field_validator("id", mode="before")
    @classmethod
    def coerce_uuid_to_str(cls, v: object) -> str:
        return str(v)

    model_config = {"from_attributes": True}


class VariantUpdateRequest(BaseModel):
    contenido: str


# ── Alert Schemas ────────────────────────────────────────


class AlertaCrisisResponse(BaseModel):
    id: int
    tipo: str
    severidad: str
    descripcion: str
    post_ids: list
    estado: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertaStatusUpdate(BaseModel):
    estado: str  # vista, atendida, descartada


# ── CRM Schemas ──────────────────────────────────────────


class InteraccionCreateRequest(BaseModel):
    ciudadano_id: int
    tipo: str
    canal: str | None = None
    resultado: str | None = None
    notas: str | None = None
    referencia_tipo: str | None = None
    referencia_id: str | None = None


class InteraccionResponse(BaseModel):
    id: int
    ciudadano_id: int
    tipo: str
    canal: str | None
    resultado: str | None
    notas: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class VoterScoreResponse(BaseModel):
    ciudadano_id: int
    score_favorable: float
    score_persuadible: float
    score_asistencia: float
    features: dict
    modelo_version: str
    calculated_at: datetime

    model_config = {"from_attributes": True}


# ── Webhook Schemas ──────────────────────────────────────


class ChatwootWebhookPayload(BaseModel):
    tipo: str  # message_reply, contact_created, propuesta
    data: dict
    signature: str | None = None
