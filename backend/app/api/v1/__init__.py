from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin_classification,
    admin_compliance,
    admin_overview,
    admin_promesas,
    alerts_integration,
    api_keys,
    auth,
    benchmark,
    blindaje,
    bot_detection,
    campaigns_integration,
    campanas,
    canvassing,
    ciudadanos,
    ciudadanos_legacy,
    contenido,
    content_factory_integration,
    crm_integration,
    dashboard,
    diagnostico as diagnostico_tier1,
    diagnostico_tier2,
    dirigentes,
    electoral,
    encuestas,
    eventos,
    geo,
    health,
    indice_aceptacion,
    metricas_sociales,
    ops,
    organizaciones,
    privacy_arco,
    osint,
    participacion,
    plan_ia,
    plan_ia_ciclo,
    planes,
    political_framework,
    posts,
    programas,
    social,
    trends,
    voter_scoring,
    webhooks_integration,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(dirigentes.router, prefix="/dirigentes", tags=["dirigentes"])
api_router.include_router(social.router, prefix="/social", tags=["social"])
api_router.include_router(posts.router, prefix="/posts", tags=["posts"])
api_router.include_router(electoral.router, prefix="/electoral", tags=["electoral"])
api_router.include_router(benchmark.router, prefix="/benchmark", tags=["benchmark"])
api_router.include_router(planes.router, prefix="/planes", tags=["planes"])
api_router.include_router(plan_ia.router, prefix="/plan-ia", tags=["plan-ia"])
api_router.include_router(plan_ia_ciclo.router, prefix="/plan-ia", tags=["plan-ia-ciclo"])
api_router.include_router(ciudadanos.router, prefix="/ciudadanos", tags=["ciudadanos"])
api_router.include_router(
    ciudadanos_legacy.router,
    prefix="/ciudadanos-legacy",
    tags=["ciudadanos-legacy"],
)
api_router.include_router(eventos.router, prefix="/eventos", tags=["eventos"])
api_router.include_router(programas.router, prefix="/programas", tags=["programas"])
api_router.include_router(organizaciones.router, prefix="/organizaciones", tags=["organizaciones"])
api_router.include_router(encuestas.router, prefix="/encuestas", tags=["encuestas"])
api_router.include_router(
    metricas_sociales.router, prefix="/metricas-sociales", tags=["metricas-sociales"]
)
api_router.include_router(geo.router, prefix="/geo", tags=["geo"])
api_router.include_router(voter_scoring.router, prefix="/voter-scoring", tags=["voter-scoring"])
api_router.include_router(contenido.router, prefix="/contenido", tags=["contenido"])
api_router.include_router(blindaje.router, prefix="/blindaje", tags=["blindaje"])
api_router.include_router(campanas.router, prefix="/campanas", tags=["campanas"])
api_router.include_router(canvassing.router, prefix="/canvassing", tags=["canvassing"])
api_router.include_router(participacion.router, prefix="/participacion", tags=["participacion"])
api_router.include_router(campaigns_integration.router, prefix="/campaigns", tags=["campaigns"])
api_router.include_router(
    content_factory_integration.router, prefix="/content", tags=["content-factory"]
)
api_router.include_router(alerts_integration.router, prefix="/alerts", tags=["alerts"])
api_router.include_router(crm_integration.router, prefix="/crm", tags=["crm"])
api_router.include_router(webhooks_integration.router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(api_keys.router, prefix="/api-keys", tags=["api-keys"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(osint.router, prefix="/osint", tags=["osint"])
api_router.include_router(bot_detection.router, prefix="/bot-detection", tags=["bot-detection"])
api_router.include_router(trends.router, prefix="/trends", tags=["trends"])
api_router.include_router(political_framework.router, prefix="/framework", tags=["political-framework"])
api_router.include_router(admin_classification.router, prefix="/admin/classification", tags=["admin-classification"])
api_router.include_router(admin_compliance.router, prefix="/admin/compliance", tags=["admin-compliance-arco"])
api_router.include_router(admin_overview.router, prefix="/admin", tags=["admin-overview"])
api_router.include_router(admin_promesas.router, prefix="/admin/promesas", tags=["admin-promesas"])
api_router.include_router(indice_aceptacion.router, prefix="/social", tags=["indice-aceptacion"])
api_router.include_router(privacy_arco.router, prefix="", tags=["privacy-arco"])
api_router.include_router(ops.router, prefix="/ops", tags=["ops"])
api_router.include_router(
    diagnostico_tier1.router, prefix="/diagnostico", tags=["diagnostico-tier1"]
)
api_router.include_router(
    diagnostico_tier2.router,
    prefix="/diagnostico_tier2",
    tags=["diagnostico-tier2"],
)
