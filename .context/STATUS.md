# CRECE v2.0 — Status

**Último update:** 2026-04-12 01:20 local
**Sesión activa:** /sprint-review Sprint B (Canvassing Geo) + Sprint A (Demo)
**Main HEAD:** `1185921` (PR #7 merged)
**Branch activo:** `feat/canvassing-geo-map` @ 2 commits (`78c3e87`, `0276661`)

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

| Sprint | Esfuerzo | Prioridad | Avance |
|---|---|---|---|
| **S4 Motor de Trends MVP** | 7 días nominal | Alta (plan core) | **9/11** funcionalmente cerrado (+2 scaffolds) |
| **S5 Wizard Onboarding** | 1.5 días nominal | Alta (demo crítica) | **6/6 core** (auto-login real = deuda menor) |

### Sesión 2026-04-12 — Sprint B Canvassing Geo + Sprint A Demo
Branch: `feat/canvassing-geo-map` (pendiente PR a main)

**Sprint B — Canvassing Geo Map (killer feature):**
- `78c3e87` — feat(canvassing): mapa geo con 9,631 ciudadanos reales + filtros + clustering
  - Backend: `GET /canvassing/geo` (GeoJSON PostgreSQL-native) + `GET /canvassing/geo-stats`
  - Frontend: `CanvassingGeoMap` component (MapLibre + clustering + popup)
  - Page reescrita: filtros sidebar + mapa + stats bar + tabs rutas
  - Hooks: `useCanvassingGeo`, `useCanvassingGeoStats`
  - Verificado: BJ=812, CUA=5000(limit), filtros estrato/participación/contactado, tsc clean

**Sprint A — Demo Interna:**
- `0276661` — docs: guion demo 30 min para equipo MC
  - 7 escenas: intro → dashboard → mapa canvassing → wizard → plan IA → PII → Q&A
  - Checklist pre-demo + plan de respaldo

**Cross-audit Gemini (integrado):**
- G1: RLS verificada en ciudadanos_legacy (org_id scope)
- G2: Umbral MVT a 15K registros (hoy 9,723, inline OK)
- G3: Cluster property aggregation (documentado, no implementado — nice-to-have)
- G4: Filtros dtto_local/dtto_federal agregados al endpoint
- G5: Smoke test inmediato post-B.1 (ejecutado)
- G6: GeoJSON construido en PostgreSQL (`jsonb_build_object` + `jsonb_agg`)

### Sesión 2026-04-11 tarde-3 — /sprint-implement luz verde all
Commits en `fix/sprint-4-trends`:
- `9efc76d` — S4.1 catálogo INEGI 16 alcaldías CDMX (ST_Contains verified)
- `24b032d` — docs(s4) /sprint-review enriquecimiento + cross-audit Gemini
- `59413bd` — S4.2 topic_trends + RLS + HNSW orden a→c→b (RLS verificada con rol no-priv)
- `dac0039` — S4.4a location_inference con DB lookup + normalize_social_text + 10 tests
- `bb01c46` — docs D-S4-05/06 y STATUS mid-session
- `598c537` — Batch 1: S4.8 audit RLS + S4.3 seeds 136 cuentas + S4.6a queues + S4.7 RSS parser
- `682b598` — Batch 2: S4.5 detect_trends + S4.6b label_trend_cluster + S4.7 ingest_rss_feeds task
- `521fd6a` — Batch 3: S4.9 endpoint /trends/geo + /alcaldias + S4.10 TrendingAlcaldiaCard + E2E real

**Tareas S4 — estado final**:
| ID | Estado | Verificación |
|---|---|---|
| S4.1 | ✅ | 16 alcaldías INEGI PostGIS, ST_Contains 3/3 points |
| S4.2a/b/c | ✅ | topic_trends + vector(384) + HNSW cosine + 2 RLS policies verificadas |
| S4.3 | ✅ | 136 cuentas semilla YAML (target era 150) |
| S4.4a + a.5 | ✅ | location_inference DB-backed + normalize_social_text + 10 tests |
| S4.4b | ⏸ scaffold | spaCy es_core_news_md NO instalado (deuda D-S4-04) |
| S4.5 | ✅ | detect_trends pipeline end-to-end, 1 trend real generado sobre posts de Piña |
| S4.6a/b | ✅ | cola trends_labeling + Ollama batch labeling probado contra gemma3:12b live |
| S4.7 | ✅ parser | fetch_all_feeds + parser RSS con 8 fuentes + 4 tests; persistencia diferida (D-S4-07) |
| S4.8 | ✅ | search_similar_posts requiere org_id kw-only, cross-org leak imposible, 3 tests |
| S4.9 | ✅ | GET /trends/geo + /alcaldias live, auth JWT, scopeado por org |
| S4.10 | ✅ | TrendingAlcaldiaCard montado en /dashboard/social, tsc clean |
| S4.11 | ✅ | E2E real: detect_trends sobre 381 posts dev DB → 1 trend BJ → label Ollama "Diálogo universitario..." |

Dep nueva: `pgvector>=0.3.0` en pyproject.toml.
Migraciones: `a1b2c3d4e5f6` (alcaldías) + `b2c3d4e5f6a7` (topic_trends + RLS + HNSW).
Endpoints live: `/api/v1/trends/geo`, `/api/v1/trends/alcaldias`.
Tests totales nuevos en S4: **17 verdes** (10 location_inference + 3 RLS audit + 4 RSS parser).

**Deudas documentadas en DECISIONS**:
- **D-S4-04**: spaCy es_core_news_md no instalado (skip por budget, S4.4b)
- **D-S4-07**: RSS persistence requires `platform_enum += 'NEWS'` migration + synthetic profiles o profile_id nullable
- **D-S4-08**: clustering semántico HNSW real requiere backfill_embeddings() sobre 381 posts existentes (primer pase agrupa solo por alcaldía)

**Próximo paso recomendado**: arrancar S5 Wizard Onboarding (1.5 días nominal). Todos los blockers resueltos: RLS audited, topic_trends table ready, endpoints live, UI card mounted.

### Sesión 2026-04-11 tarde-4 — D-DATA-01 Ruta C import CRECE legacy
**Contexto:** el CEO aportó el zip `MC Tablas.zip` con 5 CSVs del CRECE Oracle APEX original. Aprobó Ruta C: importar 3 alcaldías piloto.

**Tablas nuevas y datos importados:**
- `unidades_territoriales` (5,552 rows, sin PII) — grano sección × colonia, con volatilidad, estrato, lista nominal, categoría P1..P5
- `ciudadanos_legacy` (9,723 rows, RLS-scoped, PII sensible) — Cuauhtémoc 6,643 + Miguel Hidalgo 2,267 + Benito Juárez 813
- `promotores_legacy` (45 rows) — super/mega/regular promotores de las 3 alcaldías piloto

**Archivos nuevos:**
- Migraciones: `c3d4e5f6a7b8` (unidades_territoriales) + `d4e5f6a7b8c9` (ciudadanos_legacy + promotores_legacy + RLS policies)
- Modelos: `backend/app/models/unidad_territorial.py`, `backend/app/models/legacy.py`
- Script: `backend/scripts/import_mc_original.py` (idempotente, gated por `CRECE_MC_RAW_DIR`)
- `.gitignore`: `backend/data/raw/mc_original/` excluido del repo (PII)

**Calidad de la data importada:**
- 100% de ciudadanos linkeados a `unidad_territorial` via sección electoral
- 99% con coordenadas GPS reales (9,632/9,723)
- 100% de ciudadanos asignados a un promotor legacy
- Top promotor: MCCDMXCUAUSUPERPROMOTORC3 con 903 ciudadanos

**Hallazgos documentados en DECISIONS.md:**
- D-DATA-01 (decisión Ruta C con alcance y trade-offs)
- D-DATA-02 (compliance LFPDPPP pendiente — pgcrypto at-rest, audit log, right-to-delete)
- D-DATA-03 (reconciliación legacy ↔ v2 pendiente)
- D-DATA-04 (datos faltantes: solo 5% con email, 37% con phone)

**Próximos pasos habilitados:**
1. Voter scoring real sobre 9,723 ciudadanos con lat/lon
2. Canvassing con unidades territoriales + volatilidad + estrato socioeconómico
3. Trends detector puede filtrar por `unidad_territorial` (más fino que alcaldía)
4. S5 wizard puede usar promotores reales en vez de usuarios sintéticos

### Sesión 2026-04-11 tarde — /sprint-review
- Plan S4+S5 revisado, enriquecido con subdivisiones y criterios medibles (ver `PLAN-current.md` sección "Plan revisado 2026-04-11")
- Cross-audit con Gemini CLI aplicó 4 ajustes: orden correcto S4.2 `a→c→b`, S4.8 debe ir tras S4.2b (no antes), S4.4 necesita pre-processor de normalización social, S5.3a debe retornar `sync_status=pending` inmediatamente
- Ruta crítica actualizada: `S4.1 ✅ → S4.2a → S4.2c (RLS) → S4.2b (HNSW) → S4.8 audit → S4.5`
- Resources asignados por tarea (agentes + skills + herramientas)
- **S4.1 ejecutado y verificado**: 16 alcaldías INEGI CDMX en PostGIS, `ST_Contains` OK contra 3 puntos conocidos. Commit `9efc76d` en `fix/sprint-4-trends`.
- **Próximo paso**: S4.2a — crear tabla `topic_trends` con FKs a `alcaldias_cdmx` y `org_id`, SIN la columna vector todavía.

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
