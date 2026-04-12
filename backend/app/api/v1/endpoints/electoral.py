from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from geoalchemy2.functions import ST_AsGeoJSON
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import Role, RoleChecker, get_current_user
from app.models.electoral import IntencionVoto, SeccionElectoral
from app.models.user import User
from app.schemas.electoral import (
    IntencionVotoCreate,
    IntencionVotoResponse,
    SeccionElectoralResponse,
    SeccionGeoJSONCollection,
    SeccionGeoJSONFeature,
)

router = APIRouter()


@router.get("/secciones", response_model=SeccionGeoJSONCollection)
async def list_secciones(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
    estado: str | None = None,
    municipio: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
) -> SeccionGeoJSONCollection:
    """List secciones electorales as GeoJSON FeatureCollection."""
    query = select(
        SeccionElectoral.id,
        SeccionElectoral.seccion,
        SeccionElectoral.estado,
        SeccionElectoral.distrito_federal,
        SeccionElectoral.distrito_local,
        SeccionElectoral.municipio,
        ST_AsGeoJSON(SeccionElectoral.geometry).label("geojson"),
    )

    if estado:
        query = query.where(SeccionElectoral.estado == estado)
    if municipio:
        query = query.where(SeccionElectoral.municipio == municipio)

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    rows = result.all()

    features = []
    for row in rows:
        props = SeccionElectoralResponse(
            id=row.id,
            seccion=row.seccion,
            estado=row.estado,
            distrito_federal=row.distrito_federal,
            distrito_local=row.distrito_local,
            municipio=row.municipio,
        )
        geometry = json.loads(row.geojson) if row.geojson else None
        features.append(SeccionGeoJSONFeature(properties=props, geometry=geometry))

    return SeccionGeoJSONCollection(features=features)


@router.get("/secciones/{seccion_id}/intencion-voto", response_model=list[IntencionVotoResponse])
async def get_intencion_voto(
    seccion_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
) -> list[IntencionVoto]:
    """Get all intencion de voto records for a seccion electoral."""
    result = await db.execute(
        select(IntencionVoto)
        .where(IntencionVoto.seccion_id == seccion_id)
        .order_by(IntencionVoto.fecha_encuesta.desc())
    )
    return list(result.scalars().all())


@router.post(
    "/intencion-voto",
    response_model=IntencionVotoResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST, Role.FIELD_OPERATOR]))],
)
async def create_intencion_voto(
    payload: IntencionVotoCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> IntencionVoto:
    """Record a new intencion de voto survey result."""
    # Validate seccion exists
    seccion_result = await db.execute(
        select(SeccionElectoral).where(SeccionElectoral.id == payload.seccion_id)
    )
    if seccion_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Seccion electoral not found",
        )

    # Validate percentages sum to ~100
    total_pct = payload.a_favor + payload.en_contra + payload.indeciso + payload.no_responde
    if not (99.0 <= total_pct <= 101.0):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Percentages must sum to ~100 (got {total_pct:.1f})",
        )

    record = IntencionVoto(
        **payload.model_dump(),
        capturado_por_id=current_user.id,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return record


@router.get("/mapa/mvt/{z}/{x}/{y}.pbf")
async def vector_tiles(
    z: int,
    x: int,
    y: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """Serve Mapbox Vector Tiles (MVT) for secciones electorales.

    Uses raw SQL with ST_AsMVT for maximum performance. This endpoint
    is designed to be consumed by Mapbox GL JS or MapLibre GL.
    """
    # Raw SQL for performance — ST_AsMVT is not well-supported by ORM
    sql = text("""
        WITH bounds AS (
            SELECT ST_TileEnvelope(:z, :x, :y) AS geom
        ),
        mvtgeom AS (
            SELECT
                se.id,
                se.seccion,
                se.estado,
                se.municipio,
                se.distrito_federal,
                ST_AsMVTGeom(
                    se.geometry,
                    bounds.geom,
                    4096,
                    256,
                    true
                ) AS geom
            FROM secciones_electorales se, bounds
            WHERE se.geometry IS NOT NULL
              AND ST_Intersects(se.geometry, bounds.geom)
        )
        SELECT ST_AsMVT(mvtgeom.*, 'secciones', 4096, 'geom') AS mvt
        FROM mvtgeom
    """)

    result = await db.execute(sql, {"z": z, "x": x, "y": y})
    row = result.one()
    tile_data = bytes(row.mvt) if row.mvt else b""

    return Response(
        content=tile_data,
        media_type="application/x-protobuf",
        headers={
            "Content-Disposition": "inline",
            "Cache-Control": "public, max-age=3600",
            "Access-Control-Allow-Origin": "*",
        },
    )
