from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.models.plan_ia import EstadoTarea, TipoPlan


class PlanGenerateRequest(BaseModel):
    dirigente_id: int
    tipo: TipoPlan
    contexto_adicional: str | None = None
    estructurado: bool = False  # Sprint 3: si True, genera PlanEstructurado JSON


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


# ── Sprint 3: plan estructurado con tareas editables ─────────────────


PlataformaLiteral = Literal[
    "INSTAGRAM", "TWITTER", "FACEBOOK", "TIKTOK", "YOUTUBE",
    "WHATSAPP", "LINKEDIN", "BLUESKY", "THREADS", "TELEGRAM", "CROSS"
]

FormatoLiteral = Literal[
    "post_texto", "post_imagen", "video_corto", "video_largo",
    "reel", "story", "live", "hilo", "carousel", "articulo",
    "comentario", "respuesta", "evento", "otro"
]


class PlanTareaBase(BaseModel):
    """Base de una tarea estructurada. Constraints reflejan los mismos límites
    que tendrá el JSON schema que se envía al LLM como function calling.
    """

    titulo: str = Field(..., min_length=5, max_length=200)
    descripcion: str = Field(..., min_length=20, max_length=2000)
    plataforma: PlataformaLiteral | None = None
    formato: FormatoLiteral | None = None
    frecuencia: str | None = Field(
        None, max_length=100,
        description="Ej: '3 veces por semana', '1 vez al día', 'una sola vez'"
    )
    responsable: str | None = Field(None, max_length=100)
    deadline: datetime | None = None
    metrica_objetivo: str | None = Field(
        None, max_length=200,
        description="Nombre de la métrica (ej: 'engagement rate')"
    )
    metrica_valor_objetivo: float | None = Field(
        None, ge=0,
        description="Valor numérico esperado al completar la tarea"
    )


class PlanTareaCreate(PlanTareaBase):
    orden: int = 0


class PlanTareaUpdate(BaseModel):
    titulo: str | None = Field(None, min_length=5, max_length=200)
    descripcion: str | None = Field(None, min_length=20, max_length=2000)
    plataforma: PlataformaLiteral | None = None
    formato: FormatoLiteral | None = None
    frecuencia: str | None = Field(None, max_length=100)
    responsable: str | None = Field(None, max_length=100)
    deadline: datetime | None = None
    metrica_objetivo: str | None = Field(None, max_length=200)
    metrica_valor_objetivo: float | None = Field(None, ge=0)
    estado: EstadoTarea | None = None


class PlanTareaCompleteRequest(BaseModel):
    metrica_valor_real: float = Field(
        ..., ge=0,
        description="Valor real alcanzado al completar la tarea"
    )
    nota: str | None = Field(None, max_length=500)


class PlanTareaResponse(PlanTareaBase):
    id: int
    plan_id: int
    orden: int
    estado: EstadoTarea
    metrica_valor_real: float | None
    completado_at: datetime | None
    cambios_historial: list[dict[str, Any]] | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PlanEstructurado(BaseModel):
    """Schema que el LLM debe producir vía function calling / JSON mode.
    Usado como constraint en `plan_generator.generate_structured()`.
    """

    titulo_campana: str = Field(..., min_length=5, max_length=200)
    tesis_central: str = Field(..., min_length=50, max_length=1000)
    problematicas_direccionadas: list[str] = Field(..., min_length=1, max_length=10)
    tareas: list[PlanTareaCreate] = Field(..., min_length=5, max_length=20)

    @field_validator("tareas")
    @classmethod
    def _tareas_unique_titles(cls, v: list[PlanTareaCreate]) -> list[PlanTareaCreate]:
        titles = [t.titulo.strip().lower() for t in v]
        if len(set(titles)) != len(titles):
            raise ValueError("Las tareas deben tener títulos únicos")
        return v

    @classmethod
    def json_schema_for_llm(cls) -> dict[str, Any]:
        """Return a JSON schema suitable for OpenAI/Anthropic function calling."""
        return cls.model_json_schema()


class PlanProgresoResponse(BaseModel):
    """Agregado de progreso de un plan con tareas."""

    plan_id: int
    total_tareas: int
    tareas_todo: int
    tareas_in_progress: int
    tareas_done: int
    porcentaje_ejecutado: float
    impacto_acumulado: dict[str, float]  # {metrica_objetivo: delta_total}
