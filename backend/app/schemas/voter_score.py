from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.voter_score import SegmentoVotante


class VoterScoreResponse(BaseModel):
    id: int
    ciudadano_id: int
    score: float = Field(ge=0, le=100)
    probabilidad_mc: float = Field(ge=0.0, le=1.0)
    segmento: SegmentoVotante
    features: dict | None
    modelo_version: str | None
    scored_at: datetime

    model_config = {"from_attributes": True}


class VoterScoreRunRequest(BaseModel):
    org_id: int | None = None
    force_retrain: bool = False


class VoterScoreRunResponse(BaseModel):
    total_scored: int
    segmento_breakdown: dict[str, int]
    modelo_version: str


class SeccionScoreSummary(BaseModel):
    seccion_id: int
    avg_score: float
    segmento_counts: dict[str, int]
    total_ciudadanos: int


class SegmentDistribution(BaseModel):
    segmento: SegmentoVotante
    count: int
    percentage: float


class TrainResponse(BaseModel):
    modelo_version: str
    accuracy: float
    f1_score: float
    confusion_matrix: list[list[int]]
    total_samples: int
    message: str
