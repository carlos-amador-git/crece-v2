# PLAN — Cirugía Módulo Dirigente

**Sesión:** Joy (Claude Code)
**Worktree:** `/Users/marxchavez/Projects/crece-v2-dirigente-surgery`
**Rama:** `feat/dirigente-surgery`
**Delegado por:** Carlos (peer en `feat/sprint-c-hardening`)
**Cross-audit:** Gemini CLI (dos pases, segundo via Carlos por fallo de capacity en CLI de Joy)

## Alcance

4 bugs + 1 feature en módulo dirigente de CRECE v2.

| # | Problema | Solución |
|---|---|---|
| d | `/dashboard/dirigentes` expone lista a role=viewer (solo ve su propio registro) | Redirect role=viewer → `/dashboard/dirigentes/{su_id}`. Admin mantiene lista flota |
| b | "Crecimiento 0%" es placeholder | Tabla `social_profile_snapshots` + extender task Celery `scrape_all_profiles` + cálculo 7d/30d/90d |
| a | Radar IPD: TikTok=0 (followers=0 pero hay 62 posts), YouTube=0 (scraper nunca corrió), eje "Engagement" duplicado | Backfill + correr YT + radar B1 (5 ejes plataforma, engagement separado) |
| c | Falta widget "Tendencia por red" | Widget nuevo con switcher Treemap/Stream/Sunburst sobre misma data (reuso charts-lab) |
| e | Falta semáforo "¿mejorando o decayendo?" | Delta 30d vs 30d anterior, verde/ámbar/rojo por red + alerta 48h frescura para `data_source='manual_host_ingest'` |

## Decisiones arquitecturales (aprobadas por Gemini + Carlos)

- **Snapshot diario** (no on-demand). FK por `profile_id` (no handle) para sobrevivir cambio de username. `connectNulls:true` en Recharts para gaps.
- **Denormalización**: `social_profile_snapshots` lleva `dirigente_id`, `org_id`, `platform` además de `profile_id` — crítico para RLS performante + queries time-series por platform.
- **`data_source` como ENUM** (veto de Gemini al bool): `automated_scraper` / `manual_host_ingest` / `official_api`. Documenta *por qué* el perfil es manual (bloqueo IP YouTube) y permite al worker filtrar con `WHERE data_source != 'manual_host_ingest'`.
- **`last_manual_update DATETIME`** en `social_profiles` + alerta si `data_source='manual_host_ingest' AND (NOW - last_manual_update) > 48h`. Evita "deuda de frescura silenciosa".
- **Celery**: extender `app.workers.tasks.scrape_all_profiles` (celery_app.py:39, tasks.py:213). NO crear task nueva. Snapshot se inserta al final del scrape.
- **Radar B1**: quitar eje "Engagement", dejar 5 ejes por plataforma. Engagement como KPI/bar chart aparte. YouTube NO se oculta — carencia penaliza IPD por coverage.
- **YouTube Docker bloqueo**: opción (3) `data_source='manual_host_ingest'` + ingesta manual (ya hecha por Carlos: 56 videos). NO Bright Data por ahora (se reconsidera si escala).
- **Dos migrations Alembic separadas** (no una): (1) enum `data_source` + `last_manual_update`, (2) `social_profile_snapshots`. Facilita rollback.

## Orden de ejecución

**d → b → a → c → e**

Razón del re-orden (Gemini): (d) es frontend trivial, limpia tablero rápido. (b) construye datos para (c) y (e). (a) corrige visualización una vez los datos están bien. (c) consume data de (b). (e) consume data de (b).

## Archivos en mi ámbito

- `frontend/src/app/dashboard/dirigentes/**`
- `frontend/src/components/charts/**`
- `backend/app/api/v1/endpoints/dirigentes.py`
- `backend/app/services/diagnostico*.py`
- `backend/app/scrapers/tiktok.py`
- `backend/app/scrapers/youtube.py`
- `backend/app/workers/tasks.py` (solo `scrape_all_profiles`)
- `backend/migrations/versions/<nueva>_data_source_enum.py`
- `backend/migrations/versions/<nueva>_social_profile_snapshots.py`

## Archivos que NO tocar (zona de Carlos)

- `backend/app/api/v1/endpoints/admin_overview.py`
- `backend/app/api/v1/endpoints/admin_classification.py`
- `backend/app/api/v1/endpoints/planes.py`
- `frontend/src/app/dashboard/admin/**`
- `frontend/src/app/dashboard/planes/[id]/page.tsx`
- `frontend/src/components/planes/plan-tareas-list.tsx`
- `backend/scripts/seed_plan_tareas_*.py`
- `backend/data/planes-deliberados/**`

## Sprints

| Sprint | Objetivo | Archivos | Criterio de aceptación |
|---|---|---|---|
| S1 (paso d) | Redirect role=viewer | `frontend/src/app/dashboard/dirigentes/page.tsx` | Viewer redirigido al entrar. Admin ve lista. Verificado en Playwright con usuario pina@crece.mx |
| S2 (paso b) | Migrations + snapshots + task Celery | 2 migrations, `models/social.py`, `workers/tasks.py`, endpoint crecimiento en `dirigentes.py` | Alembic up/down OK. Task corre. `/dirigentes/{id}/crecimiento` retorna 7/30/90d. Piña TikTok backfilleado. 3 YT profiles con `data_source='manual_host_ingest'` |
| S3 (paso a) | Fix radar IPD B1 | `frontend/src/components/charts/ipd-radar-chart.tsx`, `services/diagnostico.py` | Radar muestra 5 ejes. Engagement separado como KPI. TikTok Piña sale >0. YouTube muestra 0 si no hay canal (visible) |
| S4 (paso c) | Widget tendencia + switcher | `frontend/src/components/charts/trend-por-red.tsx` nuevo, import en `[id]/page.tsx` | Switcher Treemap/Stream/Sunburst sobre misma data consumida de `/dirigentes/{id}/crecimiento` |
| S5 (paso e) | Semáforo + alerta frescura | `frontend/src/components/dashboard/semaforo-crecimiento.tsx`, logic en `dirigentes.py` | Verde/ámbar/rojo por red. Alerta log si >48h sin update manual |

## Cross-audit Gemini resultados

Registrados en `/Users/marxchavez/Projects/crece-v2/docs/` si aplica + log de conversación con Carlos en peers. Resumen:
- Primer pase: aprobó plan original con 6 refinamientos (FK profile_id, denormalización, connectNulls, B1, NO ocultar YT, extender Celery en vez de task nueva).
- Segundo pase: veto parcial al bool `is_manually_tracked` → enum `data_source`. Añadió `last_manual_update` + alerta 48h. Dos migrations separadas. Sin vetos adicionales.

## Reporte a Carlos

Brief tras cada sprint vía `claude-peers` (to_id 30kkees9). Final: PR a main coordinado por Carlos.
