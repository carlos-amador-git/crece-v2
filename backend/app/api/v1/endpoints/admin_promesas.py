"""Admin endpoint minimal para gestionar promesas de dirigentes (Sprint S4 T-1.1).

MD Consultoría añade/edita promesas post-seed para:
- Arranque fixture Piña (dirigente_id=1) vía `scripts/seed_promesas_pina_s4.py`
- Casos ad-hoc antes del Onboarding Wizard S5 que mueve esta responsabilidad al cliente

Solo role=ADMIN. Scope S4 — no sprint separado.
"""
from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.dirigente import Dirigente
from app.models.promesa_dirigente import PromesaDirigente, PromesaEstado
from app.models.user import User

router = APIRouter()


class PromesaCreateReq(BaseModel):
    dirigente_id: int = Field(..., gt=0)
    texto_promesa: str = Field(..., min_length=10, max_length=2000)
    fecha_compromiso: date | None = None
    estado: PromesaEstado = PromesaEstado.PENDIENTE
    evidencia_url: str | None = Field(None, max_length=500)


class PromesaResp(BaseModel):
    id: int
    dirigente_id: int
    texto_promesa: str
    fecha_compromiso: date | None
    estado: str
    evidencia_url: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


def _require_admin(user: User) -> None:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo admin MD Consultoría",
        )


@router.post("", response_model=PromesaResp, status_code=status.HTTP_201_CREATED)
async def crear_promesa(
    body: PromesaCreateReq,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> PromesaResp:
    _require_admin(current_user)

    dirigente = await db.get(Dirigente, body.dirigente_id)
    if dirigente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dirigente {body.dirigente_id} no existe",
        )

    promesa = PromesaDirigente(
        dirigente_id=body.dirigente_id,
        texto_promesa=body.texto_promesa,
        fecha_compromiso=body.fecha_compromiso,
        estado=body.estado,
        evidencia_url=body.evidencia_url,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db.add(promesa)
    await db.commit()
    await db.refresh(promesa)
    return PromesaResp.model_validate(promesa)


@router.get("/{dirigente_id}", response_model=list[PromesaResp])
async def listar_promesas(
    dirigente_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[PromesaResp]:
    _require_admin(current_user)
    result = await db.execute(
        select(PromesaDirigente)
        .where(PromesaDirigente.dirigente_id == dirigente_id)
        .order_by(PromesaDirigente.id)
    )
    return [PromesaResp.model_validate(r) for r in result.scalars().all()]
