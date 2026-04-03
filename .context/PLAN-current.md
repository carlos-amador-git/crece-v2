# CRECE v2.0 — Plan BATCH 3: Data Model Upgrade + Multi-tenant + Business Logic

## Estado: EN EJECUCIÓN
## Fecha: 2026-04-03
## Clasificación: CRÍTICA — sin estos campos no hay migración Oracle → CRECE v2

---

## Diagnóstico (validado con revisión Gemini)

### Problema central
BATCH 1+2 resolvió scrapers, NLP y tests pero dejó modelos de datos demasiado
simplificados. El sistema Oracle APEX actual ya tiene los campos que faltan —
sin ellos, MC no puede migrar.

### Gaps críticos identificados

**Ciudadano** (9 campos faltantes):
- `intencion_voto` — el dato más importante del sistema
- `programas_sociales` (JSONB) — correlación voto-programas
- `problematicas` (JSONB) — detección de campo
- `ubicacion` GEOGRAPHY(POINT, 4326) — geolocalización PostGIS
- `colonia`, `codigo_postal` — análisis por zona
- `escolaridad` — variable de segmentación
- `foto_ine_url` — captura desde app móvil
- `org_id` — multi-tenant

**Evento** (5 campos faltantes):
- `recursos` (JSONB) — logística
- `nuevos_simpatizantes` — tracking adeptos
- `costo_total` / `costo_por_adquisicion` — ROI
- `org_id` — multi-tenant

**Tablas completamente ausentes:**
- `organizaciones` — multi-tenant foundation
- `encuestas` — captura intención de voto en campo (distinto a IntencionVoto por sección)
- `metricas_sociales` — snapshots periódicos followers

**Business logic ausente:**
- Modo veda electoral
- Vector tiles ST_AsMVT()

---

## Sprints de ejecución

### BATCH 3A — Models + Schemas + Endpoints (2 agentes paralelos)

#### Sprint 3A-1: All Model Files (python-expert, worktree)
**Archivos a crear/modificar:**
- `backend/app/models/organizacion.py` — NUEVO: Organizacion table
- `backend/app/models/ciudadano.py` — UPGRADE: +9 campos
- `backend/app/models/evento.py` — UPGRADE: +5 campos
- `backend/app/models/user.py` — ADD: org_id FK
- `backend/app/models/dirigente.py` — ADD: org_id FK
- `backend/app/models/encuesta.py` — NUEVO: encuestas de campo
- `backend/app/models/metrica_social.py` — NUEVO: snapshots followers
- `backend/app/models/__init__.py` — UPDATE: importar nuevos modelos

#### Sprint 3A-2: All Schemas + Endpoints + Business Logic (python-expert, worktree)
**Archivos a crear/modificar:**
- `backend/app/schemas/organizacion.py` — NUEVO
- `backend/app/schemas/ciudadano.py` — UPGRADE
- `backend/app/schemas/evento.py` — UPGRADE
- `backend/app/schemas/encuesta.py` — NUEVO
- `backend/app/schemas/metrica_social.py` — NUEVO
- `backend/app/api/v1/endpoints/organizaciones.py` — NUEVO
- `backend/app/api/v1/endpoints/encuestas.py` — NUEVO
- `backend/app/api/v1/endpoints/metricas_sociales.py` — NUEVO
- `backend/app/api/v1/endpoints/geo.py` — NUEVO: vector tiles
- `backend/app/api/v1/endpoints/ciudadanos.py` — UPGRADE
- `backend/app/api/v1/endpoints/eventos.py` — UPGRADE
- `backend/app/api/v1/__init__.py` — UPDATE: nuevos routers
- `backend/app/core/veda.py` — NUEVO: modo veda middleware
- `backend/app/core/config.py` — ADD: VEDA_ELECTORAL_ACTIVE setting

### BATCH 3B — Frontend Cleanup (1 agente, post-merge BATCH 3A)
- Identificar y eliminar datos mock del dashboard
- Conectar componentes a API real
- Verificar con Playwright screenshots

---

## Verificación interna
1. Post-BATCH 3A: merge manual de worktrees, syntax check
2. Post-merge: commit consolidado
3. Post-BATCH 3B: Playwright screenshots de validación
4. Final: status update

## Asignación de recursos
| Agente | Tipo | Sprint | Aislamiento |
|--------|------|--------|-------------|
| Agent A | python-expert | 3A-1 (Models) | worktree |
| Agent B | python-expert | 3A-2 (Schemas+Endpoints+Logic) | worktree |
| Agent C | frontend-architect | 3B (Frontend cleanup) | worktree |
