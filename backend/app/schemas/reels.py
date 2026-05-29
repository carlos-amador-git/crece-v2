"""Schemas Pydantic v2 para generación de reels (D-REELS-GROQ-1, 2026-05-15)."""
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


Tono = Literal["informativo", "emocional", "urgente", "inspiracional"]
DuracionSegundos = Literal[15, 30, 60]


class GenerateReelScriptRequest(BaseModel):
    dirigente_id: int = Field(..., gt=0)
    tema: str | None = Field(default=None, max_length=500)
    duracion_segundos: DuracionSegundos = 30
    tono: Tono = "informativo"
    incluir_cta: bool = True
    contexto_adicional: str | None = Field(default=None, max_length=2000)


class ReelScript(BaseModel):
    hook: str
    desarrollo: str
    cta: str = ""


class ReelScriptMetadata(BaseModel):
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    elapsed_ms: int
    context_enriched: bool = False  # Feature 2 2026-05-17 · True si prompt incluyó contexto BD del dirigente


class GenerateReelScriptResponse(BaseModel):
    id: UUID
    dirigente_id: int
    dirigente_nombre: str
    tema: str | None
    duracion_segundos: int
    tono: str
    incluir_cta: bool
    script: ReelScript
    metadata: ReelScriptMetadata
    created_at: datetime


class ReelScriptListItem(BaseModel):
    """Item para listar historial reciente de un dirigente."""
    id: UUID
    tema: str | None
    duracion_segundos: int
    tono: str
    script: ReelScript
    modelo_ia: str
    created_at: datetime
