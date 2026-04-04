from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.gasto_electoral import (
    CategoriaGastoINE,
    SeveridadAlerta,
    TipoAlertaCompliance,
)


# ── Gasto Electoral ──────────────────────────────────────────


class GastoElectoralCreate(BaseModel):
    concepto: str = Field(..., max_length=500)
    categoria: CategoriaGastoINE
    monto: float = Field(..., gt=0)
    fecha_gasto: date
    proveedor: str | None = Field(None, max_length=255)
    factura_uuid: str | None = Field(None, max_length=36)
    evidencia_url: str | None = Field(None, max_length=500)
    dirigente_id: int | None = None
    evento_id: int | None = None
    org_id: int


class GastoElectoralUpdate(BaseModel):
    concepto: str | None = Field(None, max_length=500)
    categoria: CategoriaGastoINE | None = None
    monto: float | None = Field(None, gt=0)
    fecha_gasto: date | None = None
    proveedor: str | None = Field(None, max_length=255)
    factura_uuid: str | None = Field(None, max_length=36)
    evidencia_url: str | None = Field(None, max_length=500)
    dirigente_id: int | None = None
    evento_id: int | None = None
    notas: str | None = None


class GastoElectoralResponse(BaseModel):
    id: int
    org_id: int
    dirigente_id: int | None
    evento_id: int | None
    concepto: str
    categoria: CategoriaGastoINE
    monto: float
    fecha_gasto: date
    proveedor: str | None
    factura_uuid: str | None
    evidencia_url: str | None
    aprobado: bool
    aprobado_por_id: int | None
    notas: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Alerta Compliance ────────────────────────────────────────


class AlertaComplianceResponse(BaseModel):
    id: int
    org_id: int
    tipo: TipoAlertaCompliance
    severidad: SeveridadAlerta
    titulo: str
    descripcion: str
    referencia_tipo: str
    referencia_id: int | None
    resuelta: bool
    resuelta_por_id: int | None
    resuelta_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Bot Analysis ─────────────────────────────────────────────


class BotAnalysisResult(BaseModel):
    post_id: int
    is_suspicious: bool
    indicators: list[str]
    confidence: float = Field(..., ge=0.0, le=1.0)


# ── Compliance Report ────────────────────────────────────────


class ComplianceReportResponse(BaseModel):
    gastos_por_categoria: dict[str, float]
    total_gastos: float
    tope_campana: float
    porcentaje_tope: float
    alertas_activas: dict[str, int]
    bot_posts_detectados: int
