from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.plan_ia import TipoPlan


class PlanGenerateRequest(BaseModel):
    dirigente_id: int
    tipo: TipoPlan
    contexto_adicional: str | None = None


class PlanIAResponse(BaseModel):
    id: int
    dirigente_id: int
    tipo: TipoPlan
    contenido: str
    modelo_ia: str
    prompt_usado: str
    datos_entrada: dict[str, Any] | None
    generado_por_id: int
    aprobado: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PlanApproveRequest(BaseModel):
    aprobado: bool = True
