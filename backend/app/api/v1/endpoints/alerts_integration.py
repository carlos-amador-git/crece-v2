from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.integration import AlertaCrisisResponse, AlertaStatusUpdate

router = APIRouter()

_VALID_ALERT_STATUSES = {"vista", "atendida", "descartada"}


@router.get("/", response_model=list[AlertaCrisisResponse])
async def list_alerts(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    severity: str | None = None,
    alert_status: str | None = Query(None, alias="status"),
    since: datetime | None = None,
) -> list[AlertaCrisisResponse]:
    """List crisis alerts filtered by severity, status, and date.

    Always scoped to the current user's org_id.
    """
    from app.models.alerta_crisis import AlertaCrisis

    query = select(AlertaCrisis).where(AlertaCrisis.org_id == current_user.org_id)

    if severity:
        query = query.where(AlertaCrisis.severidad == severity)
    if alert_status:
        query = query.where(AlertaCrisis.estado == alert_status)
    if since:
        query = query.where(AlertaCrisis.created_at >= since)

    query = query.order_by(AlertaCrisis.created_at.desc())
    result = await db.execute(query)
    items = list(result.scalars().all())

    return [AlertaCrisisResponse.model_validate(a) for a in items]


@router.patch("/{alert_id}/status")
async def update_alert_status(
    alert_id: int,
    payload: AlertaStatusUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Change alert status to: vista, atendida, or descartada."""
    from app.models.alerta_crisis import AlertaCrisis

    if payload.estado not in _VALID_ALERT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(sorted(_VALID_ALERT_STATUSES))}",
        )

    result = await db.execute(
        select(AlertaCrisis).where(
            AlertaCrisis.id == alert_id,
            AlertaCrisis.org_id == current_user.org_id,
        )
    )
    alerta = result.scalar_one_or_none()
    if alerta is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found"
        )

    alerta.estado = payload.estado
    await db.flush()
    await db.refresh(alerta)

    return {
        "message": f"Alert {alert_id} status updated to '{payload.estado}'",
        "alert_id": alerta.id,
        "estado": alerta.estado,
    }
