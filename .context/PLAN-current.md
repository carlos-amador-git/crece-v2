# CRECE v2.0 — Sprint: Decidim MC + Integración Participación Ciudadana
## Estado: EN PROGRESO
## Fecha: 2026-04-05

---

## Contexto
Decidim MC (#11) era el último módulo PENDIENTE con diseño de producto.
Se creó proyecto base en ~/Projects/decidim-mc/ con Dockerfile, docker-compose, config.
Ahora: hacer el build funcional + integrar con CRECE vía GraphQL.

## Sprint 1: Fix Dockerfile y build funcional (30 min)
**Objetivo:** Decidim MC buildea y levanta con docker compose.
**Archivos:**
- `decidim-mc/Dockerfile` — fix multi-stage build issues
- `decidim-mc/db/seeds.rb` — seed MC organization
- `decidim-mc/config/sidekiq.yml` — job queues config
- `decidim-mc/Makefile` — comandos de conveniencia
**Criterio:** `docker compose build` exitoso, `docker compose up` levanta health check.

## Sprint 2: Cliente GraphQL en CRECE backend (30 min)
**Objetivo:** CRECE puede consultar Decidim vía GraphQL.
**Archivos:**
- `crece-v2/backend/app/services/decidim_service.py` (nuevo)
- `crece-v2/backend/app/core/config.py` (agregar DECIDIM_URL)
**Criterio:** DecidimService.get_proposals(), .get_budgets(), .get_stats() funcionales.

## Sprint 3: Endpoint CRECE API para participación (20 min)
**Objetivo:** Frontend CRECE puede ver datos de Decidim.
**Archivos:**
- `crece-v2/backend/app/api/v1/endpoints/participacion.py` (nuevo)
- `crece-v2/backend/app/schemas/participacion.py` (nuevo)
- `crece-v2/backend/app/api/v1/__init__.py` (registrar router)
**Criterio:** GET /participacion/proposals, /participacion/budgets, /participacion/stats responden.

## Sprint 4: Contexto y documentación (10 min)
**Objetivo:** STATUS.md, DECISIONS.md actualizados.
**Criterio:** Decidim marcado como HECHO en STATUS.md.

## Dependencias
Sprint 2 depende de Sprint 1 (necesita saber el schema GraphQL real).
Sprint 3 depende de Sprint 2 (consume DecidimService).
Sprint 4 es independiente pero se hace al final.
