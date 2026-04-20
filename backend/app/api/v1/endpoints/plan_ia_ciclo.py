"""Plan IA · T8/T9/T10/T11 endpoints — ciclo de cierre post-ejecución.

Endpoints:
- GET  /plan-ia/{id}/seguimiento          — evolución diaria métricas observadas (T8)
- PUT  /plan-ia/{id}/veredicto            — edición cliente del veredicto (T9)
- GET  /plan-ia/memoria/{dirigente_id}    — bloque #10.7 memoria dirigente (T10)
- GET  /plan-ia/reporte/{dirigente_id}    — PDF semanal dirigente (T11)

Los servicios subyacentes son síncronos (Celery usa sesión sync); las
endpoints async invocan vía anyio.to_thread.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any

from anyio import to_thread
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field

from app.core.security import Role, RoleChecker, get_current_user
from app.models.user import User
from app.services.plan_ia.cierre_service import editar_veredicto_cliente
from app.services.plan_ia.memoria_service import compute as memoria_compute
from app.services.plan_ia.reporte_semanal import generar_pdf_dirigente
from app.services.plan_ia.seguimiento_service import evolucion_diaria

router = APIRouter()


def _get_sync_session():
    """Create a synchronous SQLAlchemy session for Plan IA services."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from app.core.config import settings

    engine = create_engine(settings.DATABASE_URL_SYNC, echo=False)
    return Session(engine)


# ─────────────────────────────────────────────────────────────────────
# T8 · Seguimiento
# ─────────────────────────────────────────────────────────────────────


@router.get(
    "/{recomendacion_id}/seguimiento",
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST, Role.VIEWER]))],
)
async def get_seguimiento(
    recomendacion_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    """Devuelve la evolución diaria de métricas observadas para una recomendación."""

    def _run() -> dict[str, Any]:
        session = _get_sync_session()
        try:
            return evolucion_diaria(session, recomendacion_id)
        finally:
            session.close()

    data = await to_thread.run_sync(_run)
    if "error" in data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=data["error"])
    return data


# ─────────────────────────────────────────────────────────────────────
# T9 · Veredicto edición cliente
# ─────────────────────────────────────────────────────────────────────


class VeredictoEditRequest(BaseModel):
    """Payload para edición de veredicto por cliente."""

    veredicto: str = Field(
        ...,
        pattern=r"^(exitosa|parcial|fallida)$",
        description="Nuevo veredicto elegido por el cliente",
    )
    notas_cliente: str | None = Field(
        default=None,
        max_length=2000,
        description="Justificación opcional del cliente",
    )


@router.put(
    "/{recomendacion_id}/veredicto",
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST]))],
)
async def put_veredicto(
    recomendacion_id: int,
    payload: VeredictoEditRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    """Edita el veredicto de una recomendación preservando `veredicto_original`."""

    def _run() -> dict[str, Any]:
        session = _get_sync_session()
        try:
            return editar_veredicto_cliente(
                session,
                recomendacion_id=recomendacion_id,
                nuevo_veredicto=payload.veredicto,
                notas=payload.notas_cliente,
            )
        finally:
            session.close()

    data = await to_thread.run_sync(_run)
    if "error" in data:
        code = status.HTTP_404_NOT_FOUND if data["error"] == "recomendacion_not_found" else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=data["error"])
    return data


# ─────────────────────────────────────────────────────────────────────
# T10 · Memoria Plan IA bloque #10.7
# ─────────────────────────────────────────────────────────────────────


@router.get(
    "/memoria/{dirigente_id}",
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST, Role.VIEWER]))],
)
async def get_memoria(
    dirigente_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    org_id: int | None = Query(default=None, description="Filtrar por organización"),
) -> dict[str, Any]:
    """Bloque #10.7 Memoria Plan IA — tasa éxito + histórico del dirigente."""

    def _run() -> dict[str, Any]:
        session = _get_sync_session()
        try:
            return memoria_compute(session, dirigente_id=dirigente_id, org_id=org_id)
        finally:
            session.close()

    return await to_thread.run_sync(_run)


# ─────────────────────────────────────────────────────────────────────
# T11 · Reporte semanal PDF
# ─────────────────────────────────────────────────────────────────────


@router.get(
    "/reporte/{dirigente_id}",
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST]))],
)
async def get_reporte_semanal(
    dirigente_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    week: str | None = Query(
        default=None,
        description="Formato YYYY-WW; ej 2026-16. Default: semana actual",
        pattern=r"^\d{4}-\d{1,2}$",
    ),
) -> Response:
    """Devuelve el PDF semanal binario para el dirigente."""
    year: int | None = None
    week_num: int | None = None
    if week is not None:
        try:
            y, w = week.split("-", 1)
            year = int(y)
            week_num = int(w)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid_week_format",
            ) from exc

    if year is None or week_num is None:
        iso = datetime.now(UTC).isocalendar()
        year = iso.year
        week_num = iso.week

    def _run() -> bytes:
        session = _get_sync_session()
        try:
            return generar_pdf_dirigente(
                session,
                dirigente_id=dirigente_id,
                year=year,
                week=week_num,
            )
        finally:
            session.close()

    pdf_bytes = await to_thread.run_sync(_run)
    filename = f"reporte_plan_ia_{dirigente_id}_W{week_num}_{year}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
