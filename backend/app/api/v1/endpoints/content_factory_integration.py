from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.integration import (
    ContentGenerateRequest,
    ContentPieceResponse,
    VariantUpdateRequest,
)
from app.services.content_factory_integration import (
    generate_content,
    generate_content_stream,
)

router = APIRouter()


@router.post(
    "/generate",
    response_model=ContentPieceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_content_endpoint(
    payload: ContentGenerateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ContentPieceResponse:
    """Generate multi-platform content for a dirigente using Claude AI."""
    try:
        pieza = await generate_content(
            db=db,
            dirigente_id=payload.dirigente_id,
            tema=payload.tema,
            contexto=payload.contexto,
            tono=payload.tono,
            plataformas=payload.plataformas,
            user_id=current_user.id,
            org_id=current_user.org_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return ContentPieceResponse.model_validate(pieza)


@router.post("/generate/stream")
async def generate_content_stream_endpoint(
    payload: ContentGenerateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> EventSourceResponse:
    """Stream content generation via Server-Sent Events."""
    return EventSourceResponse(
        generate_content_stream(
            db=db,
            dirigente_id=payload.dirigente_id,
            tema=payload.tema,
            contexto=payload.contexto,
            tono=payload.tono,
            plataformas=payload.plataformas,
            user_id=current_user.id,
            org_id=current_user.org_id,
        )
    )


@router.get("/pieces", response_model=PaginatedResponse[ContentPieceResponse])
async def list_pieces(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    dirigente_id: int | None = None,
    estado: str | None = None,
    fecha_desde: datetime | None = None,
    fecha_hasta: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[ContentPieceResponse]:
    """List content pieces with optional filters."""
    from app.models.contenido_pieza import ContenidoPieza

    query = select(ContenidoPieza).where(ContenidoPieza.org_id == current_user.org_id)
    count_query = select(func.count(ContenidoPieza.id)).where(
        ContenidoPieza.org_id == current_user.org_id
    )

    if dirigente_id is not None:
        query = query.where(ContenidoPieza.dirigente_id == dirigente_id)
        count_query = count_query.where(ContenidoPieza.dirigente_id == dirigente_id)
    if estado:
        query = query.where(ContenidoPieza.estado == estado)
        count_query = count_query.where(ContenidoPieza.estado == estado)
    if fecha_desde:
        query = query.where(ContenidoPieza.created_at >= fecha_desde)
        count_query = count_query.where(ContenidoPieza.created_at >= fecha_desde)
    if fecha_hasta:
        query = query.where(ContenidoPieza.created_at <= fecha_hasta)
        count_query = count_query.where(ContenidoPieza.created_at <= fecha_hasta)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = (
        query.order_by(ContenidoPieza.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    items = list(result.scalars().all())

    return PaginatedResponse(
        items=[ContentPieceResponse.model_validate(p) for p in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if total > 0 else 0,
    )


@router.get("/pieces/{piece_id}", response_model=ContentPieceResponse)
async def get_piece(
    piece_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ContentPieceResponse:
    """Get a single content piece by UUID."""
    from uuid import UUID

    from app.models.contenido_pieza import ContenidoPieza

    try:
        uuid_val = UUID(piece_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid piece ID format",
        ) from None

    result = await db.execute(
        select(ContenidoPieza).where(
            ContenidoPieza.id == uuid_val,
            ContenidoPieza.org_id == current_user.org_id,
        )
    )
    pieza = result.scalar_one_or_none()
    if pieza is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content piece not found")

    return ContentPieceResponse.model_validate(pieza)


@router.put("/pieces/{piece_id}/variant/{platform}")
async def update_variant(
    piece_id: str,
    platform: str,
    payload: VariantUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Update a specific platform variant before publishing."""
    from uuid import UUID

    from app.models.contenido_pieza import ContenidoPieza

    try:
        uuid_val = UUID(piece_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid piece ID format",
        ) from None

    result = await db.execute(
        select(ContenidoPieza).where(
            ContenidoPieza.id == uuid_val,
            ContenidoPieza.org_id == current_user.org_id,
        )
    )
    pieza = result.scalar_one_or_none()
    if pieza is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content piece not found")

    if pieza.estado == "aprobado":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot edit an approved piece",
        )

    # Update the specific platform variant in JSONB
    variantes = dict(pieza.variantes) if pieza.variantes else {}
    if platform not in variantes:
        variantes[platform] = {}
    variantes[platform]["contenido"] = payload.contenido
    pieza.variantes = variantes

    await db.flush()
    await db.refresh(pieza)

    return {"message": f"Variant '{platform}' updated", "piece_id": str(pieza.id)}


@router.post("/pieces/{piece_id}/approve")
async def approve_piece(
    piece_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Approve a content piece for publishing."""
    from uuid import UUID

    from app.models.contenido_pieza import ContenidoPieza

    try:
        uuid_val = UUID(piece_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid piece ID format",
        ) from None

    result = await db.execute(
        select(ContenidoPieza).where(
            ContenidoPieza.id == uuid_val,
            ContenidoPieza.org_id == current_user.org_id,
        )
    )
    pieza = result.scalar_one_or_none()
    if pieza is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content piece not found")

    pieza.estado = "aprobado"
    pieza.aprobado_por_id = current_user.id
    pieza.aprobado_at = datetime.now(UTC)

    await db.flush()
    await db.refresh(pieza)

    return {
        "message": "Piece approved",
        "piece_id": str(pieza.id),
        "aprobado_por": current_user.full_name,
        "aprobado_at": pieza.aprobado_at.isoformat(),
    }
