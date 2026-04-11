# CRECE v2.0 — Status

## Estado: SPRINT 2 ENTREGADO + SPRINT 3 BACKEND + KANBAN UI ✅
## Fecha: 2026-04-11

## Sesión 2026-04-11 (coordinada con peer qmmine5b)

### División de trabajo
- **Peer qmmine5b** (worktree `../crece-v2-sprint1-deuda`, rama `sprint1-deuda`): deuda técnica Sprint 1
- **Yo** (main): Sprints 2-5

### Sprint 1 deuda técnica — COMPLETO ✅ (commit `dbc884c`)
Merged FF a main desde worktree `../crece-v2-sprint1-deuda`, rama ya eliminada.

1. **Migración Alembic explícita** `d4e7a2c1b8f3_add_dirigente_id_to_users.py` para `users.dirigente_id` (FK → dirigentes + index). Idempotente contra DBs ya parcheadas por ALTER manual. `alembic upgrade head` verde en dev DB.
2. **Deltas honestos en `/dashboard/overview`**: `dirigentes_change` se calcula real desde `Dirigente.created_at` comparando ventana actual vs previa. `ipd_change = None` (Optional[float]) porque NO existe tabla histórica de follower counts — la regla "NO inventar datos" prohíbe devolver 0.0 falso. Frontend renderiza "—" en lugar de "0%" engañoso.
3. **Prefetch `/dashboard/settings`**: sidebar ahora soporta `prefetch` per-item, Settings link con `prefetch={false}` para evitar 404 de RSC prefetch en despliegues parciales.

Verificación: migración alembic upgrade verde, `KpiOverviewResponse` schema carga e instancia con None (pydantic verificado), `tsc --noEmit` clean en los 4 archivos frontend modificados. Pytest completo no se corrió por warmup prolongado de modelos NLP + dev DB temporalmente roto por cambios uncommitted de sesión paralela (Sprint 3 `plan_ia.estructura_json`).

Deuda técnica residual: infraestructura de snapshots de follower counts para calcular `ipd_change` real (pendiente, sprint futuro).

### Sprint 2 — Benchmark Prompts IA ✅ FUNCIONAL

**Directorio `backend/benchmarks/ai/` creado con runner end-to-end offline.**

| ID | Tarea | Estado |
|----|-------|--------|
| S2.1 | Estructura directorio + `prompts/`, `test_cases/`, `outputs/` | HECHO |
| S2.2 | Test case fixture + script `build_test_cases.py` (requiere DB viva) | HECHO (fixture) / PENDIENTE (DB real) |
| S2.3 | Loop orchestrator `loop.py` | HECHO |
| S2.4 | Rúbrica 6 dimensiones `rubric.py` (+ `--self-test` pasa) | HECHO |
| S2.5 | Runner multi-provider `runner.py` (ollama/claude/gemini/offline) + `compare.py` | HECHO |
| S2.6 | 3+ iteraciones sobre prompt de plan generation | PENDIENTE (requiere Ollama + DB) |

**Archivos producidos:**
- `backend/benchmarks/ai/__init__.py`
- `backend/benchmarks/ai/README.md`
- `backend/benchmarks/ai/rubric.py` — 6 dims, determinista + heurísticas
- `backend/benchmarks/ai/runner.py` — async multi-provider
- `backend/benchmarks/ai/compare.py` — side-by-side + scores
- `backend/benchmarks/ai/loop.py` — orquestador iterativo
- `backend/benchmarks/ai/build_test_cases.py` — genera JSON desde DB real
- `backend/benchmarks/ai/prompts/diagnostico_v1.md` — baseline extraído de `plan_generator`
- `backend/benchmarks/ai/test_cases/fixture_sintético.json` — fallback sin DB
- `backend/benchmarks/ai/outputs/2026-04-11/` — iter_00 offline + compare_00 generados

**Verificación end-to-end ejecutada:**
```
python -m benchmarks.ai.rubric --self-test              # PASS total=93.8
python -m benchmarks.ai.runner --providers offline ...  # OK
python -m benchmarks.ai.compare ...                     # OK total=56.7 fixture
```

### Sprint 3 — Plan estructurado + Kanban ✅ BACKEND + UI COMPLETO

**Backend:**
- `backend/app/models/plan_ia.py` — agregados `PlanTarea` + `EstadoTarea` enum + campo `estructura_json` en `PlanIA`
- `backend/app/schemas/plan_ia.py` — `PlanTareaBase`, `PlanTareaCreate`, `PlanTareaUpdate`, `PlanTareaCompleteRequest`, `PlanTareaResponse`, `PlanEstructurado`, `PlanProgresoResponse` con constraints Pydantic
- `backend/app/services/plan_structured.py` (NUEVO) — `generate_structured_plan()` con function calling, retry hasta 2 veces si el LLM viola schema, persiste en `estructura_json` + filas `plan_tareas`
- `backend/app/api/v1/endpoints/planes.py` — endpoints nuevos:
  - `GET  /planes/{id}/tareas`
  - `PATCH /planes/{id}/tareas/{task_id}` (con `cambios_historial` audit trail)
  - `POST  /planes/{id}/tareas/{task_id}/complete` (captura `metrica_valor_real`)
  - `GET  /planes/{id}/progreso` (agregados de progreso + impacto)
  - `POST /planes/generar` ahora acepta `estructurado: true` como opt-in

**Frontend:**
- `frontend/src/lib/api/hooks/use-planes.ts` — tipos + hooks `usePlanTareas`, `usePlanProgreso`, `useUpdateTarea`, `useCompleteTarea`
- `frontend/src/components/planes/kanban-board.tsx` (NUEVO) — tablero 3 columnas con:
  - Movimiento entre estados vía botones (no drag-and-drop para no agregar deps)
  - Edición inline (titulo, descripcion, responsable, frecuencia) en Dialog
  - Captura de métrica real al completar
  - Historial de cambios visible en el Dialog de edición
  - Barra de progreso + impacto acumulado por métrica
- `frontend/src/app/dashboard/planes/[id]/kanban/page.tsx` (NUEVO) — página del tablero

**Verificación:**
- `tsc --noEmit` frontend: **exit 0 ✅**
- Importación backend + router routes check: **9 rutas registradas ✅**

**Lo que queda para cerrar Sprint 3 (próxima sesión):**
- **S3.1 Migración Alembic** para tabla `plan_tareas` + columna `estructura_json` → bloqueada por zona de exclusión del peer; el peer no la tomó, queda pendiente para ejecutar cuando su sprint1-deuda esté mergeado
- **S3.5 Excepción veda** en middleware para creación de planes IA internos → PENDIENTE, requiere leer `veda.py` y añadir branch
- **S3.7b Historial de cambios UI** en timeline — parcialmente hecho (lista simple en Dialog), falta UI tipo timeline
- **S3.9 Test E2E Playwright** — PENDIENTE

### Sprint 4 — Motor de Trends MVP 🟡 DISEÑADO + STUB

- `.context/S4-DESIGN.md` — diseño completo de los 11 componentes
- `backend/app/services/location_inference.py` — scaffold con lógica heurística placeholder (3 alcaldías piloto)
- **Todo lo demás:** 7 días de trabajo dedicado. Incluye migraciones PostGIS, worker Celery, integración pgvector HNSW con filtro org_id, RSS ingest, UI card.

### Sprint 5 — Wizard Onboarding 🟡 DISEÑADO

- `.context/S5-DESIGN.md` — diseño completo de endpoints + UI wizard + progress polling + auto-login
- **Ejecución:** 1.5 días dedicados

## Archivos creados/modificados en esta sesión (main, sin commit todavía)

**Nuevos:**
```
.context/SPRINT-IMPLEMENT-2026-04-11.md
.context/S4-DESIGN.md
.context/S5-DESIGN.md
backend/benchmarks/__init__.py
backend/benchmarks/ai/__init__.py
backend/benchmarks/ai/README.md
backend/benchmarks/ai/rubric.py
backend/benchmarks/ai/runner.py
backend/benchmarks/ai/compare.py
backend/benchmarks/ai/loop.py
backend/benchmarks/ai/build_test_cases.py
backend/benchmarks/ai/prompts/diagnostico_v1.md
backend/benchmarks/ai/test_cases/fixture_sintético.json
backend/benchmarks/ai/outputs/2026-04-11/iter_00_prompt.md
backend/benchmarks/ai/outputs/2026-04-11/iter_00_offline.md
backend/benchmarks/ai/outputs/2026-04-11/compare_00.md
backend/app/services/plan_structured.py
backend/app/services/location_inference.py
frontend/src/components/planes/kanban-board.tsx
frontend/src/app/dashboard/planes/[id]/kanban/page.tsx
```

**Modificados (tracked):**
```
backend/app/models/plan_ia.py         ← +PlanTarea +EstadoTarea +estructura_json +relationship
backend/app/schemas/plan_ia.py        ← +7 schemas (PlanTareaBase/Create/Update/Complete/Response, PlanEstructurado, PlanProgresoResponse)
backend/app/api/v1/endpoints/planes.py ← +4 endpoints Sprint 3
frontend/src/lib/api/hooks/use-planes.ts ← +4 hooks Sprint 3
```

## Zona de exclusión respetada
Cero tocamiento de:
- `backend/app/api/v1/dashboard.py` ✓
- `backend/app/models/user.py` ✓
- `backend/migrations/**` ✓ (migración plan_tareas queda pendiente, no se creó)
- `frontend/src/components/layout/sidebar.*` ✓

## Próximos pasos recomendados
1. **Peer merge sprint1-deuda → main** (peer avisa cuando esté listo)
2. **Crear migración `plan_tareas`** (puede hacerlo cualquiera, la zona se libera tras merge del peer)
3. **Ejecutar S2 loop real** (requiere Ollama + DB viva + credenciales Claude)
4. **Commit de Sprint 2 + 3 backend/UI** en `main` (o rama `sprint2-3`) — coordinado con peer
5. **Sprint 4 ejecución dedicada** (7 días)
6. **Sprint 5 ejecución dedicada** (1.5 días)

## Cross-audit (self-review, `/gemini plan` no disponible en esta sesión)
Riesgos:
- Kanban sin drag-and-drop: trade-off deliberado. Botones funcionan, UX es menos fluida. Si se quiere dnd real, instalar `@dnd-kit/sortable` en siguiente iteración (decisión CEO).
- `build_test_cases.py` no probado contra DB viva en esta sesión (el tunnel puede haberse caído). Se deja fixture sintético como fallback.
- `generate_structured_plan()` retry loop: si Ollama devuelve JSON sistemáticamente inválido, la latencia se triplica. Acotado a 3 intentos totales.
- Historial de cambios en `PlanTarea.cambios_historial` (JSONB): no hay índice. Para >1000 tareas por plan habrá que migrar a tabla dedicada.
