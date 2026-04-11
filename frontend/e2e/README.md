# CRECE v2 — E2E Playwright tests

Tests Playwright ligeros contra el frontend de Next.js. Todos usan **mocks
de API** en lugar de hitar un backend real — eso los hace rápidos,
reproducibles y ejecutables en CI sin orquestar docker-compose.

## Estructura

```
e2e/
├── helpers/
│   └── auth.ts              # injectAuthState, mockDashboardApis
├── pages.spec.ts            # smoke tests de las 15 páginas del dashboard
├── visual.spec.ts           # comparaciones visuales (screenshots)
├── plan-kanban.spec.ts      # S3.9 Sprint 3 — flujo Kanban de plan estructurado
├── playwright.config.ts
└── screenshots/
```

## Cómo correr

Desde `frontend/`:

```bash
# Levantar dev server + correr suite completa
npm run dev &            # en otra terminal o background
npm run test:e2e

# Solo un archivo
npx playwright test --config=e2e/playwright.config.ts e2e/plan-kanban.spec.ts

# Modo UI interactivo (debug paso a paso)
npm run test:e2e:ui
```

## S3.9 — Kanban test (`plan-kanban.spec.ts`)

Verifica el flujo end-to-end del tablero Kanban agregado en Sprint 3:

1. **Renderizar columnas con tareas distribuidas** (`TODO / IN_PROGRESS / DONE`)
2. **Mover tarea TODO → IN_PROGRESS** vía botón `→` del card
3. **Editar título inline** via diálogo de edición
4. **Completar tarea capturando métrica real** + actualización de progreso

Los 4 tests usan un **store en memoria** dentro del `beforeEach` que permite
a PATCH/complete reflejar los cambios en los GET subsecuentes, simulando un
backend stateful sin tocar uno real.

### Dependencias del test

- `injectAuthState` del helper existente (fakes `crece_access_token` +
  intercepta `/auth/me`)
- Mocks de 4 rutas backend:
  - `GET /api/v1/planes/{id}` — detalle del plan
  - `GET /api/v1/planes/{id}/tareas` — lista
  - `GET /api/v1/planes/{id}/progreso` — agregado
  - `PATCH /api/v1/planes/{id}/tareas/{task_id}` — update con echo
  - `POST /api/v1/planes/{id}/tareas/{task_id}/complete` — cierre con métrica

### Datos de fixture

3 tareas mock para `plan_id=42`:

| ID | Estado inicial | Plataforma | Métrica |
|---|---|---|---|
| 1 | TODO | INSTAGRAM (reel) | engagement_rate → 0.08 |
| 2 | IN_PROGRESS | TWITTER (hilo) | impressions → 5000 |
| 3 | DONE | FACEBOOK (live) | reach → 2150/2000 |

### Ejecutar solo S3.9

```bash
cd frontend
npx playwright test --config=e2e/playwright.config.ts e2e/plan-kanban.spec.ts
```

## Estado actual del suite

- `pages.spec.ts` — smoke de 15 páginas del dashboard (heredado)
- `visual.spec.ts` — comparaciones visuales (heredado)
- `plan-kanban.spec.ts` — **nuevo**, 4 casos, cierra S3.9 del Sprint 3

## Lo que NO cubren los E2E

- No hitan el backend real — si el contrato del backend cambia (renombre de
  endpoints, cambio de schema response), los tests siguen verdes pero el
  backend puede estar roto. Para contratos reales, usar los tests de `pytest`
  del backend o un test de integración dedicado que levante ambos servicios.
- No validan el pipeline de generación IA ni las llamadas a Ollama/Claude.
  Para eso hay pruebas separadas en `backend/tests/test_plan_structured.py`
  (cuando existan) y el benchmark de Sprint 2 (`backend/benchmarks/ai/`).
- No verifican el behavior de drag-and-drop real (los tests usan botones
  `→` y `Completar` porque el componente actual de Kanban NO usa dnd — ver
  DECISIONS D-SPRINT3-01).
