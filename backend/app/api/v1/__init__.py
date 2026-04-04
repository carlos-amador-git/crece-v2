from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    benchmark,
    blindaje,
    campanas,
    canvassing,
    ciudadanos,
    contenido,
    dirigentes,
    electoral,
    encuestas,
    eventos,
    geo,
    health,
    metricas_sociales,
    organizaciones,
    participacion,
    planes,
    programas,
    social,
    voter_scoring,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(dirigentes.router, prefix="/dirigentes", tags=["dirigentes"])
api_router.include_router(social.router, prefix="/social", tags=["social"])
api_router.include_router(electoral.router, prefix="/electoral", tags=["electoral"])
api_router.include_router(benchmark.router, prefix="/benchmark", tags=["benchmark"])
api_router.include_router(planes.router, prefix="/planes", tags=["planes"])
api_router.include_router(ciudadanos.router, prefix="/ciudadanos", tags=["ciudadanos"])
api_router.include_router(eventos.router, prefix="/eventos", tags=["eventos"])
api_router.include_router(programas.router, prefix="/programas", tags=["programas"])
api_router.include_router(organizaciones.router, prefix="/organizaciones", tags=["organizaciones"])
api_router.include_router(encuestas.router, prefix="/encuestas", tags=["encuestas"])
api_router.include_router(metricas_sociales.router, prefix="/metricas-sociales", tags=["metricas-sociales"])
api_router.include_router(geo.router, prefix="/geo", tags=["geo"])
api_router.include_router(voter_scoring.router, prefix="/voter-scoring", tags=["voter-scoring"])
api_router.include_router(contenido.router, prefix="/contenido", tags=["contenido"])
api_router.include_router(blindaje.router, prefix="/blindaje", tags=["blindaje"])
api_router.include_router(campanas.router, prefix="/campanas", tags=["campanas"])
api_router.include_router(canvassing.router, prefix="/canvassing", tags=["canvassing"])
api_router.include_router(participacion.router, prefix="/participacion", tags=["participacion"])
