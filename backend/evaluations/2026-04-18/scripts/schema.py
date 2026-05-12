"""Schema unificado para triangulación NLP Layer 2.

Los 3 clasificadores (Claude Code, Gemini CLI, Gemma3:12b local) escriben
al mismo schema. Cualquier divergencia se atribuye al modelo, no al formato.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Enums canónicos — exact strings del prompt unificado
# ---------------------------------------------------------------------------

Tono = Literal[
    "elogio",
    "critica",
    "pregunta",
    "ataque",
    "informativo",
    "personal",
    "autopromocion",
]

Target = Literal[
    "dirigente_post",
    "gobierno",
    "oposicion",
    "ciudadania",
    "institucion",
    "otros",
]

Polaridad = Literal["aprobacion", "neutral", "rechazo"]

SourceModel = Literal[
    "claude-opus-4-7",
    "gemini-cli",
    "gemma3:12b",
]


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ClassificationRow(BaseModel):
    """Una fila de output clasificado por cualquiera de los 3 modelos."""

    id: str = Field(..., description="ID único del comment (ej. X_2044905890109952401)")
    source_model: SourceModel
    tono: Tono
    target: Target
    intensidad: int = Field(..., ge=-3, le=3)
    polaridad_preliminar: Polaridad
    razon_corta: str = Field(..., max_length=500)
    classified_at: str = Field(..., description="ISO-8601 UTC")

    # Campos opcionales mantenidos para trazabilidad (no usados en comparación):
    handle_dirigente: Optional[str] = None
    plataforma: Optional[str] = None

    @field_validator("classified_at")
    @classmethod
    def _iso8601(cls, v: str) -> str:
        # Validación best-effort sin bloquear si trae microsegundos raros
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError(f"classified_at debe ser ISO-8601, got: {v!r}")
        return v


class SampleRow(BaseModel):
    """Una fila del sample_60.jsonl — input para los 3 clasificadores."""

    id: str
    plataforma: str
    handle_dirigente: str
    comment_text: str
    post_text: str
    author: Optional[str] = None
    likes: Optional[int] = 0


# ---------------------------------------------------------------------------
# Fixture de ejemplo (autodocumentación)
# ---------------------------------------------------------------------------

FIXTURE_EXAMPLE = ClassificationRow(
    id="X_2044905890109952401",
    source_model="claude-opus-4-7",
    tono="informativo",
    target="dirigente_post",
    intensidad=0,
    polaridad_preliminar="neutral",
    razon_corta="El comentario es una respuesta neutral sin opinión clara.",
    classified_at="2026-04-18T18:32:18.812300",
)


if __name__ == "__main__":
    # Smoke-test: schema se valida y el fixture serializa
    import json

    row = FIXTURE_EXAMPLE
    print("Schema OK. Fixture:")
    print(json.dumps(row.model_dump(), indent=2, ensure_ascii=False))
