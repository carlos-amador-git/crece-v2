# CRECE v2.0 — Status

**Ultimo update:** 2026-04-23 (sesión /sprint-implement post-review CEO 11 screenshots)
**Sesion activa:** frontend hotfixes branch `hotfix/23a-ui-puros` (4 commits, pendiente push + PR)
**Branch activo:** `hotfix/23a-ui-puros` ahead of `main @ 40e3ce1`
**Próxima ventana §9.8:** día 30 piloto ≈ 2026-05-20

---

## 2026-04-23 — Sprint 23 · post-review CEO (11 screenshots)

**Workflow:** `/sprint-review` + `/sprint-implement` con cross-audit Gemini.
**Diagnóstico:** 11 findings F-23-01..F-23-11 en `.context/frontend-review-2026-04-23/DIAGNOSTICO-SCREEN-CRECE.md`.
**Plan revisado:** `PLAN-current.md` (copia de `frontend-review-2026-04-23/PLAN-REVISADO.md`).
**Gemini audit:** `GEMINI-AUDIT.md` (3 reclasificaciones, 2 gaps, 2 optimizaciones, 2 riesgos no vistos).

### Commits en `hotfix/23a-ui-puros` (ahead of main)

| SHA corto | Scope | Findings cubiertos |
|---|---|---|
| `787c1be` | docs(.context) · diagnóstico + plan + Gemini audit | base documental |
| 23-A | fix(frontend) · UI hotfixes | F-23-02, F-23-05 UI, F-23-07, F-23-08, F-23-09 parcial |
| 23-B | fix(backend,frontend) · compose URL + platform/RT filters | F-23-05 datos P1, F-23-03, F-23-04 |
| 23-D | fix(frontend) · copy rewrite titles + context | F-23-10, F-23-11 parcial |

### Findings status

| # | Estado | Nota |
|---|---|---|
| F-23-01 Tema Urgente sin afiliación | 🔴 §9.8 pendiente | Framework 3 capas existe; no conectado a KPI |
| F-23-02 Competitor hardcoded Piña | ✅ cerrado | Resuelto por user.full_name |
| F-23-03 Toggle RT | ✅ cerrado | Backend ya soportaba |
| F-23-04 Filtro red social | ✅ cerrado | Backend ya soportaba |
| F-23-05 Post cards | ✅ UI + URL backend | P2/P3 quedan §9.8 |
| F-23-06 Sentiment Prom. dirigente | 🔴 §9.8 pendiente | Ligado a F-23-01 |
| F-23-07 Electoral plurinominal | ✅ cerrado | Empty state diferenciado |
| F-23-08 Planes tab CTA | ✅ cerrado | Link a /dashboard/planes |
| F-23-09 Header Diagnóstico | ⚠️ parcial | MASTER §3.1 quitado; destino link pendiente D-23-B |
| F-23-10 Copy Tier 1 | ⚠️ parcial | 8/10 renames; patrón estructural propuesta Sprint 24+ |
| F-23-11 Copy Tier 2 | ⚠️ parcial | 5/8 renames; patrón estructural propuesta Sprint 24+ |

### Decisiones agregadas a DECISIONS.md
D-23-A a D-23-G (7 nuevas · ver `.context/DECISIONS.md`).

### Deuda pendiente documentada
- `SPRINT-23B-INVESTIGACION.md` · P2 (columna url) + P3 (nullable counters) → §9.8 2026-05-20
- `SPRINT-23D-COPY-PROPOSAL.md` · patrón "qué mide / cómo te fue / qué hacer" 4-fases → Sprint 24+
- `SPRINT-23E-INVESTIGACION.md` · motor sentimiento con afiliación 4-fases → §9.8 2026-05-20

### Próximos pasos recomendados
1. Push branch + abrir PR `hotfix/23a-ui-puros` → main
2. Deploy a prod (según convención D-27: `vercel deploy --prod` desde main post-merge)
3. Screenshot Playwright post-deploy para verificar contra los 11 findings originales
4. CEO responde D-23-B (destino metodología) y autoriza (o no) disclaimer interim F-23-01

---

## 2026-04-20 — Gate pre-piloto CERRADO (sesión Joy)

**Arco 2026-04-14 → 2026-04-20 · 7 días · ejecución autónoma + hotfixes post review visual.**

### Cierre funcional
- PRs merged: **#32** endpoints Plan IA cliente + Admin HITL · **#33** tests state machine (15 parametrized) · **#34** hotfix-pre-piloto-v2 6 findings (F-01/F-02/F-03/F-04/F-05/F-07)
- Bug fix última milla: `6726db4` — `/plan-ia/recomendaciones` aceptaba `estado: str`; fix a `list[str] | None` + `.in_()`. Ballesteros pasó de "Pendientes (0)" → "Pendientes (4)" en prod.
- Login hardening: `4efef29` quita accesos demo de login page producción.
- Agentation widget frontend + crawlbase node22 fix: `34dd173`.

### Sprints completados en el arco (commits en main)
| Sprint | Alcance | Commit ref |
|---|---|---|
| Pre-S2 | D-22 competidores client-owned + D-23 onboarding stack + 3 inputs operativos | `b62d843`, `cbd430c` |
| S0 | 6 tareas validación autónomas | `2d32680` |
| S1 | 10 tareas Backend Foundations | `b0381ce` |
| S2 | 10 bloques Diagnóstico Tier 1 Core MVP + Plutchik 21 | `21cc10d` |
| S3 | 8 bloques Diferenciadores Tier 2 + T0 memory hardening Docker | `49e2e26`, `6fef586` |
| S4 | Plan IA cierre ciclo D-17 · 15/15 tareas · 8 bloques prompt + 4 integraciones | `8a3e507`, `c0bd4de` |
| S5 | Onboarding Wizard 9 secciones + T0 Celery migration + Mac M4 primary | `920702d`, `415f830` |
| MVP cierre | SPRINT-CURRENT a 'MVP cerrado · fase piloto' + LaunchAgent cloudflared | `29d7d89`, `a428661` |

### Findings review visual cerrados (F-01..F-07)
- **F-01** MATRIZ_ER_5x5 → Zenodo v1 empírico (Nano X p25-p75 0.013-0.213%, UI "0.01%-1.1%", tooltip "~100× IM commercial 3-7%"). Campo `zenodo_validated` en API.
- **F-02** CardShell acepta `persistentBanner`. Demo banner B04 persiste sobre insufficient_data.
- **F-03** 9 pasos onboarding capturados. D-23 paso 5 + D-22 paso 7 verificados.
- **F-04** B13 narrative "X% engagement en comments inauténtico" según impact_hint.
- **F-05** Banner D-19 permanente en header Tier 1 (red-flag semantics).
- **F-07** B14 warning "⚠️ Detector en calibración".

### Credenciales entregables post-gate
| Usuario | Email | Password | Dirigente | Estado |
|---|---|---|---|---|
| Admin MD | admin@consultoriamd.com | admin123 | — | HITL operativo |
| Piña | pina@crece.mx | Pina2026! | id=1 · IPD 2.6/10 | demo 60 min agendable |
| Ballesteros | ballesteros@crece.mx | Ballesteros2026! | id=8 · IPD 3.1/10 | entregable ahora · 4 aprobadas verificadas prod |

### Data state final
- Piña id=1: 5 aprobadas + 1 ejecutada + 1 completada + 11 rechazadas
- Ballesteros id=8: 4 aprobadas (Cialdini Authority · Kahneman System2 · Haidt Care · Cialdini Reciprocity)
- Matriz ER: `5x5-zenodo-v1-2026-04-19` · 8 VALIDATED · 17 TBD extrapoladas
- Benchmarks: `backend/data/zenodo/v1/benchmarks_er_politicos_mx_v1.csv` (D-19 base)

### Branches no mergeados (estado intencional)
- `docs/prompt-plan-ia-v1.1-prepared` (commit `403dd31`) — prompt v1.1 preparado **NO ACTIVO**. Activación condicionada ≥7 días uso v1.0 + feedback redundancia + autorización CEO.

### Pendientes próxima sesión (frontend)
🟢 nice-to-have + 🟡 Fase C post-piloto:
- **F-06** agrupar Tier 2 semánticamente (Autenticidad · Calidad mensaje · Compliance)
- **F-08** Plan IA cards más compactas + drawer/expand
- **F-09** B01 y B06 ejes Y mejor etiquetados
- **F-10** B16 Promesas · timeline hechas vs cumplidas
- **F-11** tooltips descriptivos en números grandes
- **F-12** Settings routing · consolidar 4 rutas en tabs
- **F-13** Plan IA post-hotfix validación coherente
- **F-14** Histórico empty state mejorado
- **F-15** Admin HITL columna "Días en espera" + warning >24h
- **F-16** Typeahead Harfuch paso 7 Competidores — **DIFERIDO §6.4** (reactivar cuando cliente sin conocimiento exacto)

### Blockers abiertos
- **Agentation MCP**: config `~/.claude.json` línea 4443 fix aplicado (`server --mcp-only`) + zombie PID 76505 eliminado; `/mcp` reconnect sigue fallando → requiere **restart completo Claude Code** (no solo `/mcp`).
- **D-SEC-03**: 21 endpoints JWT-only (sin swap a dual-auth) — abierto desde 2026-04-11.
- **IDOR parcial** `/dirigentes/{id}/crecimiento`: check solo aplica si `user.dirigente_id NOT NULL` — analysts/field_operators de otra org podrían bypasear. Mitigación: tenant check basado en `org_id` (patrón `_require_tenant_access`).
- **Gemini CLI 0.37.1** rate limit 429 RESOURCE_EXHAUSTED — upgrade a 0.37.2 pendiente.

### Blockers MITIGADOS en el arco
- **D-INFRA-01** Tunnel Cloudflare efímero → **MITIGADO** con LaunchAgent auto-update Vercel (`a428661`). Tunnel rota ~1h, Vercel env var se actualiza solo.

### Auditoría memoria (2026-04-20)
Capas verdes: auto-memory (43 entradas) · smart-connections (1,622 sources) · Obsidian MCP · graphify-crece-v2 (3,775 nodos) · graphify-md-design-system (534) · gbrain (3 páginas, subutilizado) · context-mode hooks activos.
Capas con gap: MCP memory vacío (sin hidratar) · DECISIONS.md sin entradas 2026-04-14..2026-04-20 (arco post-gate sin registrar).

---

## Sesion 2026-04-13 noche — /sprint-review NLP + Framework Político

**Alcance:** 8 fases completadas en una sesión con cross-audits Gemini + Perplexity.

### Fases ejecutadas

### Sprint 1 operativo (en esta sesión)
- 95 posts clasificados por Claude Opus 4.6 via admin panel
  - MC-CDMX: 35 posts (24 Piña oposición +0.38, 11 Solano oposición -0.09)
  - GOB-OAXACA: 30 posts Pineda oficialismo (+0.47 promedio)
  - CDMX-IND: 30 posts Jiménez/Cravioto oficialismo (+0.52 / +1.00)
- 0 errores en batch processing
- Admin panel `/dashboard/admin/clasificacion` validado visualmente end-to-end
- Guardrail acceso: dirigente bloqueado (pantalla "Acceso restringido"), admin accede
- Badge "Analisis Contextual · 3 IAs deliberaron" visible en dashboard

### Sprint 2 NLP batch (corriendo en background al cierre)
- Script: `docker exec crece-backend python scripts/reprocess_nlp_full.py`
- Progreso al cierre: 2,180/3,709 posts con `nlp_model_version='multi-model-v1'`
- Topics model xlm-roberta re-descargado correctamente post cache clean
- Velocidad: ~4.6 posts/sec, ETA ~7 min al momento del handoff
- Idempotente: reanudable si se interrumpe

### Pendiente para próxima sesión
1. Dashboard admin operativo `/dashboard/admin/overview` (CEO aprobó mockup)
2. Scrapers encuestas Oraculus + Demoscopía (peer md-research entregó plan)
3. Commit final con Sprint 1+2 results
4. Implementar charts (Treemap/Stream/Sunburst) en dashboard cliente


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

### Tunnel Cloudflare (MITIGADO 2026-04-20 con LaunchAgent)
- LaunchAgent auto-update Vercel env var cuando tunnel rota (~1h)
- URL actual en runtime: `cat /tmp/crece-tunnel.url`
- Commit `a428661` — D-INFRA-01 deuda reducida de "blocker" a "automático"
- Log: `/private/tmp/cf-tunnel.log`

### Ollama
- **Mac local (recomendado para benchmarks):** `http://localhost:11434` con `gemma3:12b` (8GB) y `gemma4:latest`
- **Coolify VPS (exposición directa):** `http://163.245.208.96:11434` con `gemma3:12b`
- CPU-only en ambos. Mac M-series ~4 min/iter; VPS x86 >17 min sin completar (inviable para loop)

### Frontend
- **Vercel prod (oficial):** `https://frontend-zeta-sepia-46.vercel.app/` (verificado 200 OK · proyecto `frontend` · team `marxs-projects-bb530f2b`)
- **Deploy workflow:** `cd frontend && vercel deploy --prod --yes` (alias estable). Push a GitHub NO dispara re-deploy del proyecto `frontend`.
- **NO usar:** `crece-v2.vercel.app` (proyecto separado, no liberado — confirmación CEO 2026-04-20)
- **Dev local:** `npm run dev` en `frontend/` (puerto 3000)
- **Login hardened:** accesos demo removidos del login page en producción (`4efef29`)

### Credenciales (ver sección "Credenciales entregables post-gate" arriba para estado real)
Legacy demo creds previas (pueden estar stale):
- Piña: `pina@crece.mx` / `demo2026!` → **actualizado a** `Pina2026!`
- Solano: `solano@crece.mx` / `demo2026!` → **sin uso en piloto** (Ballesteros la reemplazó)
- Admin: `admin@consultoriamd.com` / `crece2026!` → **actualizado a** `admin123`

### Organización raíz (post PR #6 seed fix)
- `id=3, slug=mc-cdmx, nombre='Movimiento Ciudadano CDMX', tipo=PARTIDO`
- Todos los users del seed scopados a esta org automáticamente

---

## 2026-04-14 — Sprint IA-1 completado + cirugía dirigente (Joy)

### Carlos (feat/sprint-c-hardening)

Sprint IA-1 — Índice de Aceptación MVP:
- Migration `h9c0d1e2f3g4_social_comments` aplicada
- 200 comments reales TikTok ingestados (Brightdata dataset gd_lkf2st302ap89utw5k)
- 200 comments clasificados con framework (comment-framework-v1)
- Endpoint `/api/v1/social/posts/{id}/ia` — 3 scores + breakdown
- Endpoint `/api/v1/social/dirigentes/{id}/ia-summary` — top aprobación/rechazo
- LFPDPPP compliance: author_hash SHA256, cero PII crudo
- Test real: post Piña 7357909824622890245 → 11.5% aprobación / 20% rechazo / 68.5% neutral

YouTube ingesta (tangencial): 56 videos ingestados via host macOS (YT bloquea Docker).

### Joy (feat/dirigente-surgery)
- 5 commits: redirect viewer + migrations + radar B1 + widget Tendencia + docs
- 2 migrations Alembic: ds01 (enum data_source) + ds02 (social_profile_snapshots)
- Widget Tendencia con switcher Treemap/Stream/Sunburst
- Semáforo de crecimiento + alerta 48h data_source='manual_host_ingest'
- Pre-merge: rebase ds01/ds02 sobre h9c0d1e2f3g4

### Pendiente
- Cross-audit Gemini del resultado IA-1 + cirugía Joy
- Merge coordinado de las 2 ramas
- UI widget IA en `/dashboard/social/[post_id]` (Sprint IA-2)
- Ingestar más comments: FB/IG/YouTube para posts restantes
- Aviso Privacidad CRECE actualizado (LFPDPPP)

---

## 2026-04-14 05:40 — Sprint M COMPLETADO (merge Joy + Carlos consolidado)

### Commits en main (desde ÚLTIMA sesión)
- 94c72aa Merge PR #10 (Sprint 0 + 0.5 + IA-1)
- 714ca23 Merge PR #11 (cirugía módulo dirigente)
- fcb0d58 fix(migration): ds02 reuse platform_enum sin recrear
- 6fca2b4 fix(enum): DataSource usa values_callable para mapeo lowercase

### Migrations aplicadas
g8 → h9 (social_comments) → ds01 (data_source + last_manual_update) → ds02 (social_profile_snapshots RLS)

### Smoke tests PASS
- GET /api/v1/admin/overview → 200 (6 widgets flota)
- GET /api/v1/social/posts/1088/ia → 200 (200 comments Piña clasificados)
- GET /api/v1/dirigentes/1/crecimiento → 200 (5 plataformas + semaforo)
- GET /api/v1/planes/1/tareas → 200 (12 tareas Piña)

### Backfill ejecutado
4 profiles marcados data_source='manual_host_ingest':
- Piña YouTube (29 subs)
- Pineda YouTube (581 subs)
- Cravioto YouTube (26 subs)
- Piña TikTok (0 followers — bloqueo bot detection)

### Sprint W (Whisper 98 TikToks) — hallazgo honesto
Los 98 posts "sin texto" pendientes resultaron ser IG images (sin video) + FB URLs 404. No hay audio/video transcribible. Pipeline no aplica.

### Pendiente (siguientes sprints del plan REV 2)
- Sprint B: comments masivo 6 dirigentes × 4 plataformas (rotación Brightdata + Crawlbase + ScraperAPI + Apify + PhantomBuster cuando se agote)
- Sprint IA-2: UI widget IA con normalización por rol político
- Sprint D: diagnóstico formal por dirigente (FODA + benchmark vs adversario)
- Sprint P: regenerar 6 planes v3 grounded en diagnóstico (migración suave)
- Sprint C: LFPDPPP completo (aviso + retención + ARCO)
- Sprint X: cierre documental

### Bugs conocidos / deuda técnica
- IDOR parcial en /dirigentes/{id}/crecimiento: check solo aplica a users con dirigente_id NOT NULL. Analysts/field_operators de otra org podrían bypasear. Mitigar en iteración siguiente con tenant check basado en org_id (patrón _require_tenant_access)
- Gemini CLI 0.37.1 con rate limit 429 RESOURCE_EXHAUSTED — upgrade a 0.37.2 pendiente
- Chrome DevTools MCP timeout en capturas de pantalla (no bloquea funcionalidad)

---

## 2026-04-14 06:30 — /sprint-implement "todos los sprints" — 5 de 6 COMPLETADOS

### Sprint B: Comments masivo 6×4 — PARCIAL ⚠️
- 200 comments TikTok Piña ingestados (Sprint IA-1 original)
- Script `/tmp/scrape_comments_batch.py` disparado para 6 dirigentes × 3 plataformas
- Brightdata snapshots en curso >10 min sin output visible
- Comments se ingestarán async; script es idempotente

### Sprint IA-2: UI widget IA — COMPLETADO ✅
- `frontend/src/lib/api/hooks/use-indice-aceptacion.ts` — hooks React Query
- `IndiceAceptacionCard` — stacked bar aprobación/neutral/rechazo + tono breakdown
- `IASummaryCard` — top aprobación/rechazo por dirigente
- Confidence banding (low/medium/high según volumen)
- Integración en perfil dirigente + post detail pendiente de UI wiring (2-3 líneas)

### Sprint C: LFPDPPP — COMPLETADO ✅
- `docs/AVISO-PRIVACIDAD-CRECE.md` — aviso completo (LFPDPPP art. 10-IV + 16-II)
- `/api/v1/legal/privacidad` — metadata pública (200 OK verificado)
- `/api/v1/arco/exercise` — acceso/cancelación/oposición con hash SHA256
- `retention_tasks.cleanup_old_comments` — celery beat cada 86400s (24h)
- Retención 180d para social_comments

### Sprint D: Diagnósticos FODA — COMPLETADO ✅
- Script `generate_diagnostico_dirigentes.py` genera DIAGNOSTICO tipo plan_ia
- 6 DIAGNOSTICOS en BD con FODA + baseline + engagement per platform
- Grounded en: posts NLP (3709), framework clasificado (387), IA comments (200)
- Estructura `foda` (F/O/D/A) + `baseline` (métricas) + `profiles`

### Sprint P: Planes v3 grounded — COMPLETADO ✅
- Script `generate_planes_v3_from_diagnostico.py` deriva tareas desde FODA
- 6 planes v3 CONSOLIDACION con modelo_ia='foda-derived-v3'
- 29 tareas nuevas — cada una con `fundamento_foda` en cambios_historial
- Migración suave: v2 marcado superseded_by_v3, v3 activo sin romper historial
- Deltas por dirigente: Piña 5, Solano 5, Pineda 4, Nolasco 4, Jiménez 5, Cravioto 6

### Sprint X: Cierre documental — EN CURSO 🔄

### Commits en main desde arranque sesión
- 94c72aa Merge PR #10 Sprint 0+0.5+IA-1
- 5858263 fix(security) IDOR + salt
- 714ca23 Merge PR #11 cirugía dirigente Joy
- fcb0d58 fix(migration) ds02 platform_enum
- 6fca2b4 fix(enum) DataSource values_callable
- 63dd4f2 feat Sprint C LFPDPPP + IA-2 UI
- b8d8b98 feat Sprint D diagnósticos + P planes v3

### Estado BD actual
- 6 dirigentes · 3 orgs
- 3,833 posts · 200 comments con NLP
- 6 DIAGNOSTICOS · 6 planes v3 (29 tareas nuevas) + 6 planes v2 (superseded)
- 25 social_profiles (con 3 YT + 1 TT manual_host_ingest)

### Pendiente técnico
- Sprint B comments masivo (cuando Brightdata responda) — ejecutar `/tmp/scrape_comments_batch.py`
- UI wiring widgets IA en páginas existentes (copy-paste 2-3 import + component mount)
- IDOR parcial en /crecimiento (check solo aplica si user.dirigente_id NOT NULL)
- Gemini CLI capacity issue persistente — upgrade 0.37.2
