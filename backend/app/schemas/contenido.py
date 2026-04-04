from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.contenido import EstadoContenido, FormatoContenido


class ContenidoCreateRequest(BaseModel):
    """Request body for generating AI content."""

    dirigente_id: int
    formato: FormatoContenido
    tema: str = Field(min_length=3, max_length=255, description="Tema o asunto del contenido")
    tono: str = Field(
        min_length=2,
        max_length=50,
        description="Tono del contenido: formal, cercano, urgente, celebratorio, informativo",
    )
    plataforma_destino: str = Field(
        min_length=2,
        max_length=50,
        description="Plataforma destino: twitter, instagram, facebook, tiktok, youtube, prensa",
    )


class ContenidoResponse(BaseModel):
    """Response schema for a generated content piece."""

    id: int
    dirigente_id: int
    dirigente_name: str
    generado_por_id: int
    org_id: int | None

    formato: FormatoContenido
    tema: str
    tono: str
    contenido: str
    prompt_usado: str

    plataforma_destino: str
    estado: EstadoContenido
    modelo_ia: str
    tokens_input: int | None
    tokens_output: int | None

    etiqueta_ia: bool

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ContenidoUpdateEstado(BaseModel):
    """Request body for updating content status."""

    estado: EstadoContenido


class TemaSugerido(BaseModel):
    """A suggested topic for content generation."""

    tema: str
    relevancia_score: float = Field(ge=0.0, le=1.0)
    fuente: str = Field(description="Source of the suggestion: sentiment, trending, ciudadanos")
