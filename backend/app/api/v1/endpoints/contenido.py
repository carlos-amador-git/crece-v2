from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.core.database import get_db
from app.core.security import Role, RoleChecker, get_current_user
from app.models.contenido import (
    ContenidoGenerado,
    EstadoContenido,
    FormatoContenido,
    is_valid_transition,
)
from app.models.dirigente import Dirigente
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.contenido import (
    ContenidoCreateRequest,
    ContenidoResponse,
    ContenidoUpdateEstado,
    TemaSugerido,
)
from app.services.content_factory import ContentFactory

router = APIRouter()


# ── Helpers ──────────────────────────────────────────────────────────────


def _to_response(c: ContenidoGenerado) -> ContenidoResponse:
    """Convert ORM model to response schema, injecting dirigente_name."""
    return ContenidoResponse(
        id=c.id,
        dirigente_id=c.dirigente_id,
        dirigente_name=c.dirigente.full_name if c.dirigente else "Desconocido",
        generado_por_id=c.generado_por_id,
        org_id=c.org_id,
        formato=c.formato,
        tema=c.tema,
        tono=c.tono,
        contenido=c.contenido,
        prompt_usado=c.prompt_usado,
        plataforma_destino=c.plataforma_destino,
        estado=c.estado,
        modelo_ia=c.modelo_ia,
        tokens_input=c.tokens_input,
        tokens_output=c.tokens_output,
        etiqueta_ia=c.etiqueta_ia,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


# ── POST /contenido/generate ────────────────────────────────────────────


@router.post(
    "/generate",
    response_model=ContenidoResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST]))],
)
async def generate_contenido(
    payload: ContenidoCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ContenidoResponse:
    """Generate AI-powered political content for a dirigente."""
    try:
        contenido = await ContentFactory.generate(
            db=db,
            dirigente_id=payload.dirigente_id,
            formato=payload.formato,
            tema=payload.tema,
            tono=payload.tono,
            plataforma_destino=payload.plataforma_destino,
            user_id=current_user.id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating content: {exc}",
        ) from exc

    return _to_response(contenido)


# ── POST /contenido/generate/stream ─────────────────────────────────────


@router.post(
    "/generate/stream",
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST]))],
)
async def generate_contenido_stream(
    payload: ContenidoCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> EventSourceResponse:
    """Generate AI content with Server-Sent Events streaming."""
    # Validate dirigente exists before starting stream
    result = await db.execute(select(Dirigente).where(Dirigente.id == payload.dirigente_id))
    dirigente = result.scalar_one_or_none()
    if dirigente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dirigente not found")

    return EventSourceResponse(
        ContentFactory.generate_stream(
            db=db,
            dirigente_id=payload.dirigente_id,
            formato=payload.formato,
            tema=payload.tema,
            tono=payload.tono,
            plataforma_destino=payload.plataforma_destino,
            user_id=current_user.id,
        )
    )


# ── GET /contenido/ ─────────────────────────────────────────────────────


@router.get("/", response_model=PaginatedResponse[ContenidoResponse])
async def list_contenidos(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
    dirigente_id: int | None = None,
    formato: FormatoContenido | None = None,
    estado: EstadoContenido | None = None,
    plataforma_destino: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[ContenidoResponse]:
    """List generated content with filtering and pagination."""
    query = select(ContenidoGenerado)
    count_query = select(func.count(ContenidoGenerado.id))

    if dirigente_id is not None:
        query = query.where(ContenidoGenerado.dirigente_id == dirigente_id)
        count_query = count_query.where(ContenidoGenerado.dirigente_id == dirigente_id)
    if formato is not None:
        query = query.where(ContenidoGenerado.formato == formato)
        count_query = count_query.where(ContenidoGenerado.formato == formato)
    if estado is not None:
        query = query.where(ContenidoGenerado.estado == estado)
        count_query = count_query.where(ContenidoGenerado.estado == estado)
    if plataforma_destino is not None:
        query = query.where(ContenidoGenerado.plataforma_destino == plataforma_destino)
        count_query = count_query.where(ContenidoGenerado.plataforma_destino == plataforma_destino)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = (
        query.order_by(ContenidoGenerado.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    items = list(result.scalars().all())

    return PaginatedResponse(
        items=[_to_response(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if total > 0 else 0,
    )


# ── GET /contenido/{id} ─────────────────────────────────────────────────


@router.get("/{contenido_id}", response_model=ContenidoResponse)
async def get_contenido(
    contenido_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
) -> ContenidoResponse:
    """Get a single generated content piece by ID."""
    result = await db.execute(select(ContenidoGenerado).where(ContenidoGenerado.id == contenido_id))
    contenido = result.scalar_one_or_none()
    if contenido is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contenido not found")
    return _to_response(contenido)


# ── PATCH /contenido/{id}/estado ─────────────────────────────────────────


@router.patch(
    "/{contenido_id}/estado",
    response_model=ContenidoResponse,
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST]))],
)
async def update_estado(
    contenido_id: int,
    payload: ContenidoUpdateEstado,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ContenidoResponse:
    """Update content status following valid transitions.

    Valid flow: borrador -> revisado -> aprobado -> publicado
    Rejection: borrador -> rechazado, revisado -> rechazado
    """
    result = await db.execute(select(ContenidoGenerado).where(ContenidoGenerado.id == contenido_id))
    contenido = result.scalar_one_or_none()
    if contenido is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contenido not found")

    if not is_valid_transition(contenido.estado, payload.estado):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Transicion de estado invalida: "
                f"{contenido.estado.value} -> {payload.estado.value}. "
                f"Transiciones validas desde '{contenido.estado.value}': "
                f"{', '.join(s.value for s in _get_valid_targets(contenido.estado))}"
            ),
        )

    contenido.estado = payload.estado
    await db.flush()
    await db.refresh(contenido)

    return _to_response(contenido)


def _get_valid_targets(current: EstadoContenido) -> set[EstadoContenido]:
    """Return valid target states for the current state."""
    from app.models.contenido import _VALID_TRANSITIONS

    return _VALID_TRANSITIONS.get(current, set())


# ── GET /contenido/temas-sugeridos/{dirigente_id} ────────────────────────


@router.get(
    "/temas-sugeridos/{dirigente_id}",
    response_model=list[TemaSugerido],
)
async def temas_sugeridos(
    dirigente_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
) -> list[TemaSugerido]:
    """Get suggested content topics for a dirigente based on recent activity."""
    try:
        raw_temas = await ContentFactory.list_temas_sugeridos(db=db, dirigente_id=dirigente_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return [
        TemaSugerido(
            tema=str(t["tema"]),
            relevancia_score=float(t["relevancia_score"]),
            fuente=str(t["fuente"]),
        )
        for t in raw_temas
    ]


# ── DELETE /contenido/{id} ───────────────────────────────────────────────


@router.delete(
    "/{contenido_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RoleChecker([Role.ADMIN]))],
)
async def delete_contenido(
    contenido_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a generated content piece. Admin only."""
    result = await db.execute(select(ContenidoGenerado).where(ContenidoGenerado.id == contenido_id))
    contenido = result.scalar_one_or_none()
    if contenido is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contenido not found")

    await db.delete(contenido)
    await db.flush()
