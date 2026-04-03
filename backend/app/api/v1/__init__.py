from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    benchmark,
    ciudadanos,
    dirigentes,
    electoral,
    eventos,
    health,
    planes,
    programas,
    social,
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
