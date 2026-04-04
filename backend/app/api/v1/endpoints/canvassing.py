"""Smart Canvassing API — PostGIS route optimization for field operators."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import Role, RoleChecker, get_current_user
from app.models.canvassing import EstadoRuta, PuntoRuta, RutaCanvassing
from app.models.ciudadano import Ciudadano
from app.models.user import User
from app.schemas.canvassing import (
    MarkVisitadoRequest,
    NearbyCiudadanoResponse,
    OptimizeRequest,
    PuntoRutaResponse,
    RouteProgressResponse,
    RutaCanvassingResponse,
)
from app.services.canvassing import canvassing_service

router = APIRouter()


# ── Helpers ──────────────────────────────────────────────────


async def _ruta_to_response(
    db: AsyncSession, ruta: RutaCanvassing
) -> RutaCanvassingResponse:
    """Convert a RutaCanvassing ORM instance to a response schema."""
    puntos_resp = []
    for p in ruta.puntos:
        # Extract lat/lon from PostGIS geometry
        p_lat, p_lon = None, None
        if p.ubicacion is not None:
            coord_sql = text(
                "SELECT ST_Y(:geom::geometry) AS lat, ST_X(:geom::geometry) AS lon"
            )
            coord_result = await db.execute(coord_sql, {"geom": p.ubicacion})
            coords = coord_result.one()
            p_lat, p_lon = coords.lat, coords.lon

        # Fetch ciudadano name
        c_result = await db.execute(
            select(Ciudadano.nombre, Ciudadano.apellido_paterno).where(
                Ciudadano.id == p.ciudadano_id
            )
        )
        c_row = c_result.one_or_none()
        c_nombre = (
            f"{c_row.nombre} {c_row.apellido_paterno}" if c_row else None
        )

        puntos_resp.append(
            PuntoRutaResponse(
                id=p.id,
                orden=p.orden,
                ciudadano_id=p.ciudadano_id,
                ciudadano_nombre=c_nombre,
                visitado=p.visitado,
                visitado_at=p.visitado_at,
                resultado=p.resultado,
                notas=p.notas,
                lat=p_lat,
                lon=p_lon,
            )
        )

    # Build GeoJSON from route geometry
    geometry_geojson = None
    if ruta.geometry_ruta is not None:
        geojson_sql = text(
            "SELECT ST_AsGeoJSON(:geom::geometry)::json AS geojson"
        )
        geojson_result = await db.execute(
            geojson_sql, {"geom": ruta.geometry_ruta}
        )
        geometry_geojson = geojson_result.scalar_one()

    # Progress
    total = ruta.puntos_total
    completados = ruta.puntos_completados
    porcentaje = round((completados / total * 100) if total > 0 else 0.0, 2)
    distancia_restante_km = None
    if ruta.distancia_total_km is not None and total > 0:
        remaining_ratio = (total - completados) / total
        distancia_restante_km = round(
            ruta.distancia_total_km * remaining_ratio, 3
        )

    return RutaCanvassingResponse(
        id=ruta.id,
        org_id=ruta.org_id,
        encuestador_id=ruta.encuestador_id,
        seccion_id=ruta.seccion_id,
        nombre=ruta.nombre,
        fecha_asignada=ruta.fecha_asignada,
        estado=ruta.estado,
        distancia_total_km=ruta.distancia_total_km,
        tiempo_estimado_min=ruta.tiempo_estimado_min,
        puntos_total=ruta.puntos_total,
        puntos_completados=ruta.puntos_completados,
        notas=ruta.notas,
        created_at=ruta.created_at,
        updated_at=ruta.updated_at,
        puntos=puntos_resp,
        progress=RouteProgressResponse(
            total=total,
            completados=completados,
            porcentaje=porcentaje,
            distancia_restante_km=distancia_restante_km,
        ),
        geometry_geojson=geometry_geojson,
    )


# ── Endpoints ────────────────────────────────────────────────


@router.post(
    "/optimize",
    response_model=RutaCanvassingResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(RoleChecker([Role.ADMIN, Role.ANALYST, Role.FIELD_OPERATOR]))
    ],
)
async def optimize_route(
    payload: OptimizeRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RutaCanvassingResponse:
    """Generate an optimized canvassing route using PostGIS nearest-neighbor.

    Uses a recursive CTE with ST_Distance for visit ordering,
    ST_MakeLine for the route geometry, and ST_Length for distance.
    """
    try:
        ruta = await canvassing_service.optimize_route_postgis(
            db=db,
            seccion_id=payload.seccion_id,
            encuestador_id=payload.encuestador_id,
            fecha=payload.fecha,
            target_ciudadanos=payload.ciudadano_ids,
            max_puntos=payload.max_puntos,
            priorizar_score=payload.priorizar_score,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return await _ruta_to_response(db, ruta)


@router.get(
    "/routes",
    response_model=list[RutaCanvassingResponse],
)
async def list_routes(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
    encuestador_id: int | None = Query(default=None),
    fecha: date | None = Query(default=None),
    estado: EstadoRuta | None = Query(default=None),
    seccion_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[RutaCanvassingResponse]:
    """List canvassing routes with optional filters."""
    query = select(RutaCanvassing).order_by(
        RutaCanvassing.fecha_asignada.desc(),
        RutaCanvassing.created_at.desc(),
    )

    if encuestador_id is not None:
        query = query.where(RutaCanvassing.encuestador_id == encuestador_id)
    if fecha is not None:
        query = query.where(RutaCanvassing.fecha_asignada == fecha)
    if estado is not None:
        query = query.where(RutaCanvassing.estado == estado)
    if seccion_id is not None:
        query = query.where(RutaCanvassing.seccion_id == seccion_id)

    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    rutas = result.scalars().all()

    responses = []
    for ruta in rutas:
        responses.append(await _ruta_to_response(db, ruta))
    return responses


@router.get(
    "/routes/{route_id}",
    response_model=RutaCanvassingResponse,
)
async def get_route(
    route_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
) -> RutaCanvassingResponse:
    """Get a single canvassing route with points and GeoJSON."""
    result = await db.execute(
        select(RutaCanvassing).where(RutaCanvassing.id == route_id)
    )
    ruta = result.scalar_one_or_none()
    if ruta is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ruta {route_id} not found",
        )
    return await _ruta_to_response(db, ruta)


@router.patch(
    "/routes/{route_id}/punto/{punto_id}",
    response_model=PuntoRutaResponse,
    dependencies=[
        Depends(RoleChecker([Role.ADMIN, Role.ANALYST, Role.FIELD_OPERATOR]))
    ],
)
async def mark_punto_visited(
    route_id: int,
    punto_id: int,
    payload: MarkVisitadoRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PuntoRutaResponse:
    """Mark a route point as visited with the visit result."""
    # Verify punto belongs to route
    result = await db.execute(
        select(PuntoRuta).where(
            PuntoRuta.id == punto_id,
            PuntoRuta.ruta_id == route_id,
        )
    )
    punto = result.scalar_one_or_none()
    if punto is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PuntoRuta {punto_id} not found in route {route_id}",
        )

    try:
        updated_punto = await canvassing_service.mark_point_visited(
            db=db,
            punto_id=punto_id,
            resultado=payload.resultado,
            notas=payload.notas,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    # Extract lat/lon
    p_lat, p_lon = None, None
    if updated_punto.ubicacion is not None:
        coord_sql = text(
            "SELECT ST_Y(:geom::geometry) AS lat, ST_X(:geom::geometry) AS lon"
        )
        coord_result = await db.execute(
            coord_sql, {"geom": updated_punto.ubicacion}
        )
        coords = coord_result.one()
        p_lat, p_lon = coords.lat, coords.lon

    # Fetch ciudadano name
    c_result = await db.execute(
        select(Ciudadano.nombre, Ciudadano.apellido_paterno).where(
            Ciudadano.id == updated_punto.ciudadano_id
        )
    )
    c_row = c_result.one_or_none()
    c_nombre = f"{c_row.nombre} {c_row.apellido_paterno}" if c_row else None

    return PuntoRutaResponse(
        id=updated_punto.id,
        orden=updated_punto.orden,
        ciudadano_id=updated_punto.ciudadano_id,
        ciudadano_nombre=c_nombre,
        visitado=updated_punto.visitado,
        visitado_at=updated_punto.visitado_at,
        resultado=updated_punto.resultado,
        notas=updated_punto.notas,
        lat=p_lat,
        lon=p_lon,
    )


@router.get(
    "/routes/{route_id}/progress",
    response_model=RouteProgressResponse,
)
async def get_route_progress(
    route_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
) -> RouteProgressResponse:
    """Get progress statistics for a canvassing route."""
    try:
        progress = await canvassing_service.get_route_progress(db, route_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return RouteProgressResponse(**progress)


@router.get(
    "/nearby",
    response_model=list[NearbyCiudadanoResponse],
    dependencies=[
        Depends(RoleChecker([Role.ADMIN, Role.ANALYST, Role.FIELD_OPERATOR]))
    ],
)
async def get_nearby_ciudadanos(
    db: Annotated[AsyncSession, Depends(get_db)],
    lat: float = Query(ge=14.5, le=32.7),
    lon: float = Query(ge=-118.4, le=-86.7),
    radius_km: float = Query(default=1.0, gt=0, le=50),
    seccion_id: int | None = Query(default=None),
) -> list[NearbyCiudadanoResponse]:
    """Find ciudadanos near a location using ST_DWithin.

    Designed for the field operator mobile app to discover nearby citizens
    while on the ground.
    """
    try:
        results = await canvassing_service.get_nearby_ciudadanos(
            db=db,
            lat=lat,
            lon=lon,
            radius_km=radius_km,
            seccion_id=seccion_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return [NearbyCiudadanoResponse(**r) for r in results]


@router.delete(
    "/routes/{route_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RoleChecker([Role.ADMIN]))],
)
async def cancel_route(
    route_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Cancel a canvassing route. Admin only.

    Sets the route state to CANCELADA rather than deleting it,
    preserving audit trail.
    """
    result = await db.execute(
        select(RutaCanvassing).where(RutaCanvassing.id == route_id)
    )
    ruta = result.scalar_one_or_none()
    if ruta is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ruta {route_id} not found",
        )

    if ruta.estado == EstadoRuta.COMPLETADA:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot cancel a completed route",
        )

    ruta.estado = EstadoRuta.CANCELADA
    await db.flush()
