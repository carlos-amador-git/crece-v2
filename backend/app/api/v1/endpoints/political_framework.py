"""API for political framework matrix management.

Endpoints:
- GET  /framework/matrix — effective matrix (defaults + overrides) for current org
- PATCH /framework/matrix/cell — update single cell (admin only, bounded ±1)
- GET  /framework/audit — audit log for current org
- POST /framework/matrix/reset — reset org to defaults (admin only)
"""
from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import Role, RoleChecker, get_current_user
from app.models.user import User
from app.services.political_framework import (
    get_effective_matrix,
    set_override,
)

router = APIRouter()


class MatrixCellResponse(BaseModel):
    rol: str
    tono: str
    target: str
    score_default: int
    score_effective: int
    is_override: bool
    descripcion: str | None = None


class MatrixResponse(BaseModel):
    org_id: int
    version: str
    cells: list[MatrixCellResponse]


class UpdateCellRequest(BaseModel):
    rol: Literal["oficialismo", "oposicion", "independiente"]
    tono: Literal[
        "critico", "propositivo", "celebratorio", "informativo",
        "solidario", "ataque", "personal",
    ]
    target: Literal[
        "gobierno", "oposicion", "ciudadania", "medios",
        "autopromocion", "tema_especifico", "otro",
    ]
    score: int = Field(ge=-2, le=2)
    razon: str | None = None


class UpdateCellResponse(BaseModel):
    rol: str
    tono: str
    target: str
    score_before: int | None
    score_after: int
    score_default: int


def _effective_org_id(request: Request, current_user: User) -> int:
    """Resolve effective org_id (admin via X-Org-Id header, else user's org)."""
    if current_user.role == "admin":
        header_org = request.headers.get("x-org-id")
        if header_org and header_org.isdigit():
            return int(header_org)
    if current_user.org_id is None:
        raise HTTPException(status_code=400, detail="No org_id associated with user")
    return current_user.org_id


@router.get("/matrix", response_model=MatrixResponse)
async def get_matrix(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> MatrixResponse:
    """Get effective matrix (defaults + overrides) for the current org."""
    org_id = _effective_org_id(request, current_user)
    cells = await get_effective_matrix(db, org_id)
    return MatrixResponse(
        org_id=org_id,
        version="v1",
        cells=[MatrixCellResponse(**c) for c in cells],
    )


@router.patch(
    "/matrix/cell",
    response_model=UpdateCellResponse,
    dependencies=[Depends(RoleChecker([Role.ADMIN]))],
)
async def update_cell(
    request: Request,
    payload: UpdateCellRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> UpdateCellResponse:
    """Update a single matrix cell. Bounded to ±1 from default, admin only."""
    org_id = _effective_org_id(request, current_user)
    try:
        result = await set_override(
            db=db,
            org_id=org_id,
            rol=payload.rol,
            tono=payload.tono,
            target=payload.target,
            new_score=payload.score,
            user_id=current_user.id,
            razon=payload.razon,
        )
        return UpdateCellResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/audit", response_model=list[dict])
async def get_audit_log(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = 50,
) -> list[dict]:
    """Get framework audit log for current org."""
    org_id = _effective_org_id(request, current_user)
    result = await db.execute(
        text("""
            SELECT
                fal.id, fal.rol, fal.tono, fal.target,
                fal.score_before, fal.score_after, fal.score_default,
                fal.changed_at, fal.razon,
                u.email AS changed_by_email, u.full_name AS changed_by_name
            FROM framework_audit_log fal
            JOIN users u ON u.id = fal.changed_by_user_id
            WHERE fal.org_id = :org_id
            ORDER BY fal.changed_at DESC
            LIMIT :limit
        """).bindparams(org_id=org_id, limit=limit)
    )
    return [
        {
            "id": r[0], "rol": r[1], "tono": r[2], "target": r[3],
            "score_before": r[4], "score_after": r[5], "score_default": r[6],
            "changed_at": r[7].isoformat() if r[7] else None,
            "razon": r[8],
            "changed_by_email": r[9], "changed_by_name": r[10],
        }
        for r in result.fetchall()
    ]


@router.post(
    "/matrix/reset",
    dependencies=[Depends(RoleChecker([Role.ADMIN]))],
)
async def reset_to_defaults(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    razon: str | None = None,
) -> dict:
    """Reset org matrix to all defaults. Logs each reversal in audit."""
    org_id = _effective_org_id(request, current_user)

    # Get current overrides for audit
    existing = (await db.execute(
        text("SELECT rol, tono, target, score_politico FROM framework_overrides_org WHERE org_id = :org_id")
        .bindparams(org_id=org_id)
    )).fetchall()

    # Delete all overrides
    await db.execute(
        text("DELETE FROM framework_overrides_org WHERE org_id = :org_id")
        .bindparams(org_id=org_id)
    )

    # S8 audit log centralizado · trazabilidad reset framework override
    if existing:
        from app.core.audit_listeners import log_destructive_op
        await log_destructive_op(
            db,
            action="DELETE",
            model="framework_overrides_org",
            record_id=None,
            changes_summary={
                "rows_deleted": len(existing),
                "source": "political_framework.reset_org_overrides",
                "org_id": org_id,
                "razon": razon,
            },
        )

    # Audit each reversal
    for row in existing:
        default_row = (await db.execute(
            text("""SELECT score_politico FROM framework_matrix_defaults
                    WHERE version = 'v1' AND rol = :rol AND tono = :tono AND target = :target""")
            .bindparams(rol=row[0], tono=row[1], target=row[2])
        )).fetchone()
        default_score = default_row[0] if default_row else 0

        await db.execute(
            text("""INSERT INTO framework_audit_log
                    (org_id, rol, tono, target, score_before, score_after, score_default, changed_by_user_id, razon)
                    VALUES (:org_id, :rol, :tono, :target, :score_before, :score_after, :default, :user_id, :razon)""")
            .bindparams(
                org_id=org_id, rol=row[0], tono=row[1], target=row[2],
                score_before=row[3], score_after=default_score, default=default_score,
                user_id=current_user.id, razon=razon or "RESET to defaults",
            )
        )

    await db.commit()
    return {
        "org_id": org_id,
        "reset_cells": len(existing),
        "message": f"Reset {len(existing)} override(s) to defaults",
    }
