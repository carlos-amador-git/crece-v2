# CRECE v2.0 — Status

**Ultimo update:** 2026-04-13 17:10 local
**Sesion activa:** Sesion 2 — Whisper + Geo enrich + Org scoping fix
**Branch activo:** `feat/sprint-c-hardening`


---

## Sesion 2026-04-13 noche — /sprint-review NLP + Framework Político

**Alcance:** 8 fases completadas en una sesión con cross-audits Gemini + Perplexity.

### Fases ejecutadas

| Fase | Deliverable |
|---|---|
| **A** Setup | Ollama + HF verificado (topics degradado por cache xlm-roberta, fix post-cleanup) |
| **B** Endpoints RTs+dedup | `/dashboard/overview`, `/social/sentiment-timeline`, `/social/posts` filtran RTs + min_length. Piña timeline -0.163 (antes -0.295) |
| **C** NLP reprocess | 260/3,709 posts con controversy + toxicity + platform-adjusted. Script idempotente. Pausado por decisión arquitectural (no bloquea producto) |
| **D.0** Framework político | 4 tablas nuevas, 32 reglas default v1, API `/framework/*`, audit log verificado con override + rollback |
| **D.2** Validación encuestas | Migration `encuestas_publicas` + servicio `divergencia_encuestas.py` threshold 30%. Scraper scope: Oraculus + Demoscopía (peer md-research investigó, reporte en md-research/analysis/) |
| **D.3** Admin panel | `/dashboard/admin/clasificacion` — UI 3 pasos: generar prompt → pegar JSON de Claude/Gemini/Perplexity → aplicar framework |
| **E** Charts lab | `tools/charts-lab/` con Plotly — Treemap + Stream + Sunburst con datos reales |
| **F.1** UI niveles análisis | `/dashboard/settings/analisis-politico` — 4 niveles amigables (Rápido→Enriquecido→Contextual→Personalizado) |

### Decisiones arquitecturales clave

- **D-NLP-01**: Framework 3 capas (NLP técnico + LLM contextual + Matriz rule-based configurable)
- **D-NLP-02-03**: Defaults +1/-1/0 suaves (Gemini recomendación). Admin org + admin MD editan
- **D-NLP-04**: Colapsar Layer 2+3 descartado — Gemma 12B lento (5+ min/post)
- **D-NLP-05**: Validación externa opción B (alerta divergencia >30%)
- **NEW**: Pipeline MANUAL operado por MD Consultoría. Zero infra LLM. 3 IAs externas (Claude Code + Gemini CLI + Perplexity web) deliberan. Costo $0. Cadencia semanal. Fine-tune modelo propio = evolución natural (no deuda) cuando tengamos 500+ validaciones por tenant.

### Archivos nuevos

**Backend (14 archivos):**
- `migrations/versions/f7a8b9c0d1e2_political_framework.py`
- `migrations/versions/g8b9c0d1e2f3_encuestas_publicas.py`
- `app/services/political_framework.py`
- `app/services/divergencia_encuestas.py`
- `app/nlp/political_llm_prompt.py`
- `app/api/v1/endpoints/political_framework.py`
- `app/api/v1/endpoints/admin_classification.py`
- `scripts/seed_political_framework.py`
- `scripts/reprocess_nlp_full.py`
- `scripts/llm_political_pilot.py` (abandonado — Gemma lento)

**Frontend (2 páginas nuevas):**
- `src/app/dashboard/settings/analisis-politico/page.tsx`
- `src/app/dashboard/admin/clasificacion/page.tsx`
- Sidebar con sección "Admin MD" (solo role=admin)
- Badge "Analisis Contextual · 3 IAs deliberaron" en dashboard

**Tools:**
- `tools/charts-lab/index.html` + README

**Docs (5 archivos):**
- `docs/AUDITORIA-SENTIMENT-2026-04-13.md`
- `docs/CHARTS-LAB-DECISIONES.md`
- `docs/NLP-MODELOS-INVESTIGACION.md`
- `docs/POLITICAL-FRAMEWORK-DEFAULTS.md`
- `docs/OPERACION-MD-CLASIFICACION-SEMANAL.md`

### DB state

- 5 tablas nuevas (`contexto_politico`, `framework_matrix_defaults`, `framework_overrides_org`, `framework_audit_log`, `encuestas_publicas`)
- 11 columnas nuevas en `social_posts` (tono, target, sentimiento_politico_ajustado, controversy, toxicity, topics, platform_adjusted, nlp_model_version, llm_razon, llm_modelo, llm_processed_at)
- `dirigentes.rol_politico` — 2 oposición (Piña, Solano), 4 oficialismo
- 32 reglas v1 sembradas en `framework_matrix_defaults`
- 5 contextos políticos (federal, CDMX, Oaxaca, NL, Jalisco)
- 5 posts clasificados como prueba end-to-end (ia_fuente=claude)

### Peer coordination

- Peer `08rystzm` (md-research) investigó scrapers encuestas MX en paralelo
- Reporte en `md-research/analysis/20260413-mexican-polls-scrapers-crece.md`
- Oraculus JSON inline = scraper 30 líneas · Demoscopía CDMX/Oaxaca obligatorio
- Plan para FASE D.2 implementación real (5-6h) pendiente de siguiente sesión
---

## Sesion 2026-04-13 tarde — Whisper Pipeline + Geo Enrich + Org Scoping

### Tarea 1: Enriquecer secciones_geo_cdmx con master_catalogo.csv (COMPLETADA)
- Script: `backend/scripts/enrich_secciones_catalogo.py`
- 5,531 filas actualizadas, 5,495/5,589 enriquecidas
- Columnas agregadas: volatilidad, estrato, lista_nominal, categoria, dtto_local_cat, dtto_fed_cat, alcaldia, nivel_socioeconomico
- 94 secciones sin match en CSV (existentes en shapefile pero sin estructura MC)

### Tarea 2: Whisper pipeline para posts sin texto (EN PROGRESO)
- Script: `backend/scripts/whisper_tiktok_pipeline.py`
- Pipeline: yt-dlp download → ffmpeg → whisper-cli (ggml-small) → UPDATE DB
- TikTok batch: ~62% éxito (31/50 transcritos), mayoria discursos politicos
- Posts sin voz marcados con `raw_data.needs_ocr = true`
- Facebook + Instagram batch en cola

### Tarea 3: Dashboard org scoping fix (COMPLETADA)
- Bug: admin endpoint `/dirigentes/` no leia X-Org-Id header → todos los dirigentes visibles
- Fix: `dirigentes.py` y `social.py` ahora leen X-Org-Id para admin tenant switching
- Verificado visualmente: MC-CDMX 17.3K audiencia vs GOB-OAXACA 60.8K
- Followers chart, posts list, KPIs — todo scoped correctamente por org

---

## Sesion 2026-04-13 — Sprint E Multi-Tenant + War Room

### Fase 1: Multi-Tenant 3 Orgs (COMPLETADA)
- 3 organizaciones: MC-CDMX (id=1), GOB-OAXACA (id=2), CDMX-IND (id=3)
- 9 usuarios: admin + analista + campo + 6 dirigentes (Pina, Solano, Pineda, Nolasco, Jimenez, Cravioto)
- 6 dirigentes con 15 social profiles (Twitter, Instagram, Facebook, TikTok)
- org_id en JWT token y /auth/me response (con org_nombre, org_slug)
- Dirigentes endpoint filtra por org_id para non-admin users
- Admin tenant switcher en topbar con dropdown de 3 orgs
- Watermark "DATOS SIMULACION" banner para orgs sinteticas (gob-oaxaca, cdmx-ind)
- get_db_rls dependency listo para RLS enforcement (SET LOCAL app.current_org_id)
- X-Org-Id header en API client para admin tenant switching
- Login page: 7 demo buttons agrupados por org con colores (accent, amber, violet)

### Fase 2: Poblar Orgs (COMPLETADA)
- 13 sample posts para 4 nuevos dirigentes (con sentimiento y engagement)
- 2 planes IA (Oaxaca: posicionamiento turistico, CDMX-IND: estrategia legislativa)
- Total DB: 19 posts, 3 planes, 15 social profiles, 6 dirigentes, 3 orgs

### Fase 3: Login UX (COMPLETADA)
- Demo buttons agrupados por org: MC CDMX (accent), GOB OAXACA (amber), CDMX IND (violet)
- Campos se llenan visualmente al click (ya existia de sesion anterior)

### Fase 4: War Room (COMPLETADA)
- E.4.2 HECHO: 5 formatos guiones de campo en Content Factory
- E.4.1 HECHO: CompetitorSnapshotCard widget en dashboard (datos demo MC-CDMX vs Batres/Taboada)
- E.4.3 HECHO: GET /dirigentes/{id}/flash-analysis — 5 metricas + suggested_action

### Sprint F Review (mismo dia)
- F1 HECHO: Dashboard overview endpoint scoped por org_id (X-Org-Id header)
- F2 HECHO: Competitor widget en dashboard
- F3 HECHO: Flash Analysis endpoint (SQL aggregations, sin LLM)
- F4 HECHO: org_id hardening en voter_scoring (segments, by-seccion) + encuestas + social posts

### Archivos modificados
**Backend:**
- `app/schemas/user.py` — org_id, org_nombre, org_slug en UserResponse
- `app/api/v1/endpoints/auth.py` — org_id en JWT, org details en /me
- `app/api/v1/endpoints/dirigentes.py` — org_id scoping para non-admin
- `app/core/database.py` — get_db_rls + get_org_id_from_user
- `scripts/seed.py` — 3 orgs, 9 users, 6 dirigentes, 15 profiles
- `scripts/seed_multitenant.py` — NEW: idempotent multi-tenant seed
- `scripts/seed_org_data.py` — NEW: sample posts + plans para nuevas orgs

**Frontend:**
- `src/lib/api/types.ts` — org_id, org_nombre, org_slug en User
- `src/lib/api/client.ts` — X-Org-Id header
- `src/lib/auth.ts` — OrgContext, activeOrg, setActiveOrg
- `src/components/layout/topbar.tsx` — tenant switcher dropdown + org badge
- `src/app/dashboard/layout.tsx` — SyntheticDataBanner watermark
- `src/app/login/page.tsx` — 7 demo buttons grouped by org
- `src/app/dashboard/contenido/page.tsx` — 5 guiones de campo formats

### DB state post-sprint
| Tabla | Count |
|-------|-------|
| organizaciones | 3 |
| users | 9 |
| dirigentes | 6 |
| social_profiles | 15 |
| social_posts | 19 |
| planes_ia | 3 |
| alcaldias_cdmx | 16 |
| ciudadanos_legacy | 9,723 |
| ciudadanos_v2 | 205 |
| unidades_territoriales | 5,552 |

### Verificacion visual (screenshots)
- Login: 7 demo buttons x 3 orgs (/tmp/crece-login-multitenant.png)
- Dashboard admin: tenant switcher "MC CDMX" (/tmp/crece-dashboard-admin.png)
- Tenant dropdown: 3 orgs + "datos simulacion" label (/tmp/crece-tenant-switcher.png)
- GOB-OAXACA watermark: amber banner visible (/tmp/crece-oaxaca-watermark.png)
- Pineda dashboard: isolated data, 20.8K followers, 3 posts (/tmp/crece-pineda-dashboard.png)
- Content Factory: 5 guiones de campo in formato dropdown (/tmp/crece-guiones-campo.png)

---

## Anterior

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
