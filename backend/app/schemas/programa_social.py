from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel

from app.models.programa_social import NivelGobierno


class ProgramaSocialCreate(BaseModel):
    nombre: str
    descripcion: str
    dependencia: str
    nivel_gobierno: NivelGobierno
    presupuesto_anual: float | None = None


class ProgramaSocialUpdate(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None
    dependencia: str | None = None
    nivel_gobierno: NivelGobierno | None = None
    presupuesto_anual: float | None = None


class ProgramaSocialResponse(BaseModel):
    id: int
    nombre: str
    descripcion: str
    dependencia: str
    nivel_gobierno: NivelGobierno
    presupuesto_anual: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ProgramaBeneficiarioCreate(BaseModel):
    programa_id: int
    seccion_id: int
    beneficiarios_count: int
    periodo: str
    fecha_actualizacion: date
    fuente_datos: str


class ProgramaBeneficiarioResponse(BaseModel):
    id: int
    programa_id: int
    seccion_id: int
    beneficiarios_count: int
    periodo: str
    fecha_actualizacion: date
    fuente_datos: str

    model_config = {"from_attributes": True}


class ProgramaConBeneficiariosResponse(BaseModel):
    """Program with aggregated beneficiary count for a given section."""

    id: int
    nombre: str
    descripcion: str
    dependencia: str
    nivel_gobierno: NivelGobierno
    presupuesto_anual: float | None
    beneficiarios_count: int
    periodo: str
    fuente_datos: str

    model_config = {"from_attributes": True}
