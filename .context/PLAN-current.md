# CRECE v2.0 — Plan BATCH 4: Infrastructure, Migrations, Tests, RLS

## Estado: EN EJECUCIÓN
## Fecha: 2026-04-03
## Clasificación: OPERACIONAL — pasar de código a sistema funcional

---

## Sprints

### Sprint P1: Infrastructure Setup
- Fix Alembic env.py (import 3 new models: organizacion, encuesta, metrica_social)
- Create .env from template
- Start DB (PostGIS 16) + Redis via Docker Compose
- Create virtualenv + install dependencies
- **Criterio**: `python -c "from app.models import *"` pasa

### Sprint P2: Database Migration
- Generate Alembic migration for ALL tables (initial + upgrades)
- Run migration against PostGIS
- Run seed.py to populate test data
- **Criterio**: `alembic upgrade head` sin errores

### Sprint P3: Test Suite Validation
- Run pytest against real DB
- Fix any import/runtime failures
- **Criterio**: pytest pasa (green)

### Sprint P4: Multi-tenant RLS Policies
- Write Alembic migration with RLS policies
- Enable RLS on: ciudadanos, eventos, encuestas, dirigentes, programas_sociales
- Policy: users can only see rows matching their org_id
- **Criterio**: migration applies cleanly

### Sprint P5: Final Verification
- Start backend (uvicorn)
- Hit /health, /auth/login, /dirigentes via httpx
- Chrome DevTools validation of frontend connected to backend
- **Criterio**: end-to-end request succeeds

## Asignación
| Sprint | Ejecución | Notas |
|--------|-----------|-------|
| P1 | Direct (Bash) | Infraestructura local |
| P2 | Direct (Bash) | Requiere P1 |
| P3 | Direct (Bash) | Requiere P2 |
| P4 | Agent (python-expert) | Puede paralelizar con P3 |
| P5 | Direct (Chrome DevTools) | Requiere P3 |
