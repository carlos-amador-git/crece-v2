from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.organizacion import TipoOrganizacion


class OrganizacionCreate(BaseModel):
    nombre: str
    slug: str
    tipo: TipoOrganizacion
    estado: str | None = None
    logo_url: str | None = None
    config: dict | None = None
    is_active: bool = True


class OrganizacionUpdate(BaseModel):
    nombre: str | None = None
    slug: str | None = None
    tipo: TipoOrganizacion | None = None
    estado: str | None = None
    logo_url: str | None = None
    config: dict | None = None
    is_active: bool | None = None


class OrganizacionResponse(BaseModel):
    id: int
    nombre: str
    slug: str
    tipo: TipoOrganizacion
    estado: str | None
    logo_url: str | None
    config: dict | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
