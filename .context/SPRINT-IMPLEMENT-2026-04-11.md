# Sprint-Implement Plan — 2026-04-11

## Contexto
- **Peer qmmine5b:** deuda técnica Sprint 1 en paralelo.
- **Yo:** Sprints 2-5 del plan (.context/PLAN-current.md).
- **Zona de exclusión:** no tocar `backend/app/api/v1/dashboard.py`, `backend/app/models/user.py`, `backend/migrations/**`, `frontend/src/components/layout/sidebar.*`.
- **Realidad:** 14+ días de trabajo listado. Un turno de sesión no completa todo. Ejecuto Sprint 2 hasta lo ejecutable + scaffold estructural de Sprint 3 (migrations van al peer por exclusión — yo hago modelos, schemas, services, endpoints, UI). Sprint 4-5 quedan planificados con archivos placeholder y tareas explícitas.

## Bloques ejecutables en esta sesión

### Bloque A — S2 Benchmark (objetivo: funcional end-to-end sobre 1 test case)
A.1 Rúbrica 6 dimensiones con scoring determinista + hooks LLM-judge
A.2 Runner multi-provider (ollama/claude/gemini, con flag `--offline` para saltar llamadas)
A.3 Compare tool (side-by-side diff + scores)
A.4 Loop orchestrator (3 iteraciones target)
A.5 Generar test_cases JSON desde DB real
A.6 Smoke test local (al menos verificar imports + rúbrica con fixture sintético)

### Bloque B — S3 Scaffold estructural (sin migration, el peer maneja esa zona)
B.1 Modelo `plan_tareas` en `backend/app/models/plan_ia.py` (peer hace la migración)
B.2 Schemas Pydantic `PlanTarea` y `PlanEstructurado` en `backend/app/schemas/plan_ia.py`
B.3 Service `plan_generator.generate_structured()` con JSON mode contra schema
B.4 Endpoints CRUD tareas en `backend/app/api/v1/endpoints/planes.py`
B.5 Excepción veda en middleware (toca `backend/app/middleware/veda.py` — fuera de zona excluida)
B.6 Kanban UI stub: página `/dashboard/planes/[id]/kanban` + componente `KanbanBoard` + drag-and-drop placeholder

### Bloque C — S4 Planificación + skeleton
C.1 Documento de diseño de `topic_trends` model + RLS HNSW requirements en `.context/S4-DESIGN.md`
C.2 Seed YAML de cuentas por alcaldía piloto
C.3 Service stub `location_inference.py`
C.4 Worker stub `trends_detector.py` (no corre, solo esqueleto)

### Bloque D — S5 Planificación
D.1 `.context/S5-DESIGN.md` con endpoints y estados del wizard
D.2 Stub de página `/dashboard/sistema/onboarding/page.tsx`

## Criterios de aceptación
- A: `python -m benchmarks.ai.rubric --self-test` pasa. Runner acepta `--offline` y genera un iter_00_fixture.md.
- B: `alembic check` (peer) detecta el modelo nuevo; pytest imports no rompen; UI Kanban carga (mock data OK).
- C/D: Archivos existen con TODO explícitos, no se considera "entregado" sino "listo para siguiente sesión".

## Cross-audit (self-review en esta sesión, `/gemini plan` queda pendiente por no tener Gemini CLI wired)
Riesgos asumidos:
- Test cases reales dependen de DB viva. Si backend local está caído, genero fixtures sintéticos y marco S2.2 como "pendiente refresh cuando DB viva".
- Llamadas a Ollama/Claude reales quedan OPT-IN vía flag. Lo default del runner es offline.
- Kanban UI depende de librería drag-and-drop (dnd-kit). Si no está instalada, hago placeholder con botones "Move to X" en lugar de drag.
