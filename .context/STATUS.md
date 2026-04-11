# CRECE v2.0 — Status

**Último update:** 2026-04-11 09:40 local
**Sesión activa:** cerrando
**Main HEAD:** ver `git log --oneline -1 main`

---

## Estado global

### Sprints completados (100% del scope funcional)

| Sprint | Estado | Nota |
|---|---|---|
| **S1 Saneamiento** | ✅ peer qmmine5b | `dbc884c` |
| **S2 Benchmark Prompts IA** | ✅ 100% | S2.1-S2.6 completos |
| **S3 Plan Estructurado + Kanban** | ✅ backend + UI + migration + E2E escrito | Playwright run real pendiente |
| **Backport md-research** | ✅ 3 items | Platform.from_url, capture_url, opengraph helper |
| **Sprint n8n-mexico cross-review** | ✅ | Paquete npm publicado + workflow validado e2e |

### Sprints pendientes para siguiente sesión

| Sprint | Esfuerzo | Prioridad |
|---|---|---|
| **S4 Motor de Trends MVP** | 7 días nominal | Alta (plan core) |
| **S5 Wizard Onboarding** | 1.5 días nominal | Alta (demo crítica) |

### Merges del día (en orden cronológico)

```
<latest>  2026-04-11 — PR #6 hygiene post-n8n sprint (pending)
909904a   2026-04-11 — PR #5 S2.6 loop 3-iter + winner + ciudadanos fix
112e9ba   2026-04-11 — PR #4 Sprint 2/3 closures (veda, Kanban E2E, Gemma real)
40ed808   2026-04-11 — PR #3 Sprints 2-3 + backport + ollama Coolify
dbc884c   2026-04-11 — Sprint 1 deuda técnica (peer qmmine5b)
2fabfb4   2026-04-11 — docs: D-SEC-03/D-DX-01/D-OBS-01/D-INFRA-01
```

---

## Sprint 2 — Benchmark Prompts IA ✅

### Loop S2.6 — 3 iteraciones reales medidas contra Gemma 3:12b

Test case: `alejandro_piña_medina_diagnostico.json` (datos reales scrapeados
+ NLP 30d desde dev DB). Ejecutado contra Mac M-series local (~4-6 min/iter).

**Scores post rubric fix:**

| Iter | Prompt | Total | Coverage | Spec | Factual | Compliance | Length | Hallu |
|---|---|---|---|---|---|---|---|---|
| 04 | **v1 baseline (ganador)** | **86.5** | 100 | 63 | 87.8 | 100 | 85.6 | 85 |
| 05 | v2 (strict length + specificity) | 85.5 | 100 | 63 | 91.5 | 100 | 83.1 | 75 |
| 06 | v3 (literal format + anti-hallu) | 81.8 | 100 | 49 | 85.3 | 100 | 86.6 | 75 |

**Ganador:** v1 baseline. Commiteado en `backend/app/nlp/prompts/diagnostico_winner.md`.

### Learnings críticos del experimento

1. Gemma ignora mínimos de palabras (pedir 1800 → entregó 1247)
2. Más instrucciones = más alucinación (v2/v3 inventaron `@martibatres`)
3. Formato literal rígido reduce patterns rubric-detectables (9→7)
4. Simpler wins — v1 baseline convergió como óptimo

### Infraestructura validada

- `rubric.py` 6 dimensiones, self-test 92.3/100 (post-fix de decimales)
- `runner.py` multi-provider ollama/claude/gemini/offline
- `compare.py` side-by-side + gap analysis
- `loop.py` orchestrator de iteraciones
- `build_test_cases.py` genera JSON desde DB real
- 4 fixtures reales: Piña + Solano × Diagnóstico + Consolidación
- Coolify Ollama CPU-only NO es viable para el loop (>17 min sin completar)
- Mac M-series con `gemma3:12b` local es ~4-6 min/iter ← ruta de trabajo

---

## Sprint 3 — Plan Estructurado + Kanban ✅

### Backend

- `backend/app/models/plan_ia.py` — `PlanTarea`, `EstadoTarea`, `estructura_json` JSONB
- `backend/app/schemas/plan_ia.py` — 7 schemas Pydantic con constraints
- `backend/app/services/plan_structured.py` (NUEVO) — `generate_structured_plan()` con retry hasta 2× si schema falla
- `backend/app/api/v1/endpoints/planes.py` — 4 endpoints nuevos:
  - `GET /planes/{id}/tareas`
  - `PATCH /planes/{id}/tareas/{task_id}` (audit trail)
  - `POST /planes/{id}/tareas/{task_id}/complete` (captura métrica real)
  - `GET /planes/{id}/progreso` (agregados + impacto)
- Migración `402acb98d2d4` aplicada en dev DB — `estado_tarea_enum` + `plan_tareas` + `planes_ia.estructura_json`

### Frontend

- `frontend/src/components/planes/kanban-board.tsx` — 3 columnas, edit inline, completar con métrica, historial visible, progress bar
- `frontend/src/app/dashboard/planes/[id]/kanban/page.tsx` — ruta nueva
- `frontend/src/lib/api/hooks/use-planes.ts` — hooks react-query
- Botones de movimiento (no drag-and-drop, ver D-SPRINT3-01)

### E2E

- `frontend/e2e/plan-kanban.spec.ts` — 4 tests con mocks stateful, NO ejecutado todavía
- `frontend/e2e/README.md` — documentación del suite

### Pendiente

- **S3.9** ejecutar Playwright E2E con frontend dev server arriba (~30 min)

---

## Sprint 1 peer qmmine5b — ✅ `dbc884c`

- Migración Alembic `d4e7a2c1b8f3_add_dirigente_id_to_users.py`
- Deltas honestos en `/dashboard/overview` (`dirigentes_change` real, `ipd_change=None`)
- Fix prefetch RSC `/dashboard/settings`

---

## Cross-project n8n-mexico ✅

### Paquete publicado

- **`@mdconsultoria-ti/n8n-nodes-crece@0.1.1`** en npm público
- 4 nodos activos: `CreceSegmentar`, `CreceVoterScore`, `CreceContenido`, `CreceSentimiento`
- `CreceCanvassing` omitido del array `nodes[]`, código queda en repo para v0.2.0
- 6 workflows CRECE importados + re-typed + credencial linkeada
- 1 workflow end-to-end validado (read path `Buscar Ciudadano` → 18 items deserializados)

### Bugs descubiertos + arreglados en tiempo real

| Bug | Fix |
|---|---|
| `fixture_sintético.json` PLACEHOLDER literal | Runner validation PR #4 |
| `seed.py` sin org bootstrap → `/api-keys` 500 | SQL runtime fix + PR #6 seed fix |
| `ciudadanos.py` JWT-only → n8n 401 | Swap dual-auth PR #5 |
| `rubric._score_factual` decimal false positive | PR #6 regex fix |
| `runner.py` path bug out_dir relativo | PR #5 bugfix |

---

## Backport md-research ✅

3 items portados a `main`:

- **`Platform.from_url()`** classmethod — 21 host patterns + subdominio fallback
- **`BaseScraper.capture_url()`** default None — 8 scrapers heredan sin cambios
- **`helpers/opengraph.py`** — httpx + regex universal link preview

Documentado en `docs/BACKPORT-MD-RESEARCH.md` con rationale de los 4 items NO portados.

---

## Deudas técnicas abiertas

Ver `.context/DECISIONS.md` sección "Deudas técnicas encontradas durante cross-review con peer n8n-mexico":

- **D-SEC-03** — 21 endpoints siguen JWT-only, falta swap a dual-auth o middleware unificado (recomendación del peer)
- **D-DX-01** — `seed.py` sin org bootstrap → **FIXED en PR #6**
- **D-OBS-01** — `IntegrityError` devuelve 500 plano → **FIXED en PR #6**
- **D-INFRA-01** — Tunnel Cloudflare efímero, bloqueado por Carlos (admin Coolify)
- **D-SEC-02** — `ApiKey.permissions` no enforced (deuda cross-proyecto)
- **Rubric** — `_score_factual` decimal false positive → **FIXED en PR #6**
- **Rubric** — `_score_specificity` patterns estrechos (solo 6 regex)
- **Rubric** — `_score_hallucinations` solo detecta @handles, miss numbers/dates/facts
- **Drift migration** — `social_posts.embedding`, `competidor_social_profiles.last_scraped_at`, `secciones_electorales.seccion` constraint

---

## Infraestructura activa (para el próximo arranque)

### Backend local
- **Contenedor:** `crece-backend` bind-mounted a `/Users/marxchavez/Projects/crece-v2/backend`
- **Puerto:** `8002` (local host)
- **Base de datos:** PostgreSQL + PostGIS en `:5438` (crece_dev)
- **Tests DB:** `:5438` crece_test
- **Redis:** `:6383`
- **MinIO:** `:9006/9007`

### Tunnel Cloudflare efímero (reinicia con nombre nuevo)
- Hoy: `musicians-oregon-judge-angela.trycloudflare.com` (PID 5762, `cloudflared tunnel --url http://localhost:8002`)
- Log: `/private/tmp/cf-tunnel.log`
- **Aviso:** al próximo reinicio cambia de nombre. Ver `.context/DECISIONS.md` D-INFRA-01 para alternativas robustas

### Ollama
- **Mac local (recomendado para benchmarks):** `http://localhost:11434` con `gemma3:12b` (8GB) y `gemma4:latest`
- **Coolify VPS (exposición directa):** `http://163.245.208.96:11434` con `gemma3:12b`
- CPU-only en ambos. Mac M-series ~4 min/iter; VPS x86 >17 min sin completar (inviable para loop)

### Frontend
- **Vercel:** `https://frontend-zeta-sepia-46.vercel.app/` (production deploy)
- **Dev local:** `npm run dev` en `frontend/` (puerto 3000)

### Credenciales demo (hardcoded en login page)
- Admin: `admin@consultoriamd.com` / `crece2026!`
- Piña: `pina@crece.mx` / `demo2026!`
- Solano: `solano@crece.mx` / `demo2026!`

### Organización raíz (post PR #6 seed fix)
- `id=3, slug=mc-cdmx, nombre='Movimiento Ciudadano CDMX', tipo=PARTIDO`
- Todos los users del seed scopados a esta org automáticamente
