from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter()


@router.get("/tiles/{z}/{x}/{y}.mvt")
async def get_vector_tile(
    z: int,
    x: int,
    y: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    """Return Mapbox Vector Tiles (MVT) for secciones_electorales.

    Uses PostGIS ST_AsMVT to generate binary protobuf tiles compatible
    with MapLibre GL JS and other vector tile consumers.
    """
    query = text("""
        WITH
        bounds AS (
            SELECT ST_TileEnvelope(:z, :x, :y) AS geom
        ),
        mvtgeom AS (
            SELECT
                ST_AsMVTGeom(
                    s.geometry,
                    bounds.geom,
                    4096,
                    256,
                    true
                ) AS geom,
                s.id,
                s.seccion,
                s.distrito_federal,
                s.distrito_local,
                s.municipio,
                s.estado
            FROM secciones_electorales s, bounds
            WHERE s.geometry IS NOT NULL
              AND ST_Intersects(s.geometry, bounds.geom)
        )
        SELECT ST_AsMVT(mvtgeom.*, 'secciones') AS mvt
        FROM mvtgeom
    """)

    result = await db.execute(query, {"z": z, "x": x, "y": y})
    row = result.scalar_one_or_none()

    mvt_bytes = bytes(row) if row else b""

    return Response(
        content=mvt_bytes,
        media_type="application/vnd.mapbox-vector-tile",
        headers={
            "Cache-Control": "public, max-age=3600",
            "Access-Control-Allow-Origin": "*",
        },
    )
