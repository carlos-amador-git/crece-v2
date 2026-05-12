# CRECE v2.0 — Plan Definitivo Post-Inventario

**Fecha:** 2026-04-10
**Estado:** ESPERANDO APROBACIÓN CEO
**Reemplaza:** Plan Decidim del 2026-04-05 (obsoleto — Decidim se excluyó del scope)

## Contexto

Post-walkthrough visual + inventario de código + cross-audit con Gemini. El codebase tiene **mucho más programado de lo que yo asumía** (RLS activo, prompt management, AIProvider con structured outputs, pgvector HNSW, NLP pipeline completo, platform weights, veda middleware, 8 scrapers free, 606 voter scores, BlindajeService, 148 tests green, 16 páginas frontend). Este plan **extiende** lo existente en vez de reconstruir.

## Correcciones aplicadas tras cross-audit con Gemini

1. **Fix NLP neutralidad** se movió a Fase 1 (antes era parte de B genérico). Sin esto, Fase 2 benchmark fallaría por GIGO.
2. **Motor de trends estimado en 7 días, no 4**. Gemini identificó: ruido en bio-NER, clustering HNSW requiere batch, scrapers se rompen.
3. **Cortes de scope aceptados:**
   - ❌ Muestreo de followers (90% shadowban en 48h sin proxies)
   - ❌ Kanban full editable → solo To Do / In Progress / Done
   - ❌ Threads scraping (baja adopción MX, mejor como stub)
   - 🟡 TikTok baja prioridad (ruidoso para NER geográfico)
4. **Filtrado org_id ANTES de vector search HNSW** (riesgo de fuga de contexto multi-tenant).
5. **Veda middleware** debe excepcionar creación de tareas internas de análisis (no bloquearlas como si fueran publicaciones externas).
6. **Ollama queue dimensionada** antes de empezar etiquetado batch masivo.

## Sprints

### Sprint 1 — Saneamiento (1.5 días)

**Objetivo:** Dejar la base limpia y confiable antes de tocar módulos nuevos. Todas las tareas son **verificaciones/fixes sobre código existente**, sin crear archivos nuevos.

| ID | Tarea | Archivos | Criterio de aceptación | Complejidad |
|----|-------|----------|------------------------|-------------|
| S1.1 | **Correr NLP sobre los 19 posts de `/social`** (mueve de Fase 2 por GIGO) | `backend/scripts/` nuevo script one-shot o comando `python -m app.scripts.reprocess_nlp` | Pie chart de `/dashboard/social` muestra distribución real (no 100% neutral) | Baja |
| S1.2 | **Verificar RLS real con los 3 demo logins** | `frontend/src/app/login/page.tsx`, `backend/app/api/v1/endpoints/auth.py`, inspección manual DB | Login como Piña NO devuelve Solano en `/dirigentes`. Query con `EXPLAIN` muestra filter por `org_id` | Baja |
| S1.3 | **Fix bug filtros tiempo del dashboard** — `activeFilter` no propaga a hooks | `frontend/src/app/dashboard/page.tsx`, `frontend/src/lib/api/hooks/use-overview.ts` | Cambiar "Hoy" → "7 días" refresca los datos, los endpoints reciben `period` | Baja |
| S1.4 | **Fix 422 en `/voter-scoring/by-seccion`** — llamada sin `seccion_id` | `frontend/src/app/dashboard/scoring/page.tsx`, hook de scoring | Card "Scoring por Sección" muestra data o selector de sección, cero 422 en consola | Baja |
| S1.5 | **Verificar cálculo IPD** que da 3.9 idéntico para Piña y Solano | `backend/app/services/diagnostico.py`, query manual | Log `calculate_ipd()` paso a paso para cada dirigente, confirmar si es bug o coincidencia; reportar hallazgo | Baja |
| S1.6 | **Auditar si `/dashboard/participacion` está hardcoded** | `frontend/src/app/dashboard/participacion/page.tsx` | Determinar origen de los 6 KPIs y 13,586 votos. Si es mockup: conectar al servicio `participacion.py` o marcar explícitamente como demo | Baja |
| S1.7 | **Fix 404 transversal en consola** (sospecha: favicon) | `frontend/public/`, `frontend/src/app/layout.tsx` | Cero 404 en consola al cargar cualquier página | Baja |
| S1.8 | **KPIs del político en overview** — reemplazar "Total Dirigentes / Avg IPD / Posts 24h / Alertas" por "Tu Audiencia (sum followers) / Brecha vs Rival / Contactos esta semana / Tema urgente". Delta con valor absoluto + %, no solo %. | `frontend/src/app/dashboard/page.tsx`, hooks de overview | Los 4 cards hablan en lenguaje político con datos reales de Piña | Baja |
| S1.9 | **Perfil dirigente enriquecido en sidebar** — agregar IPD score (X/10) + total followers. Opcional: mini sparkline IPD 30d | `frontend/src/components/layout/sidebar.tsx` | Sidebar footer muestra contexto adicional del dirigente activo | Baja |

**Verificación del sprint:** Playwright walkthrough de las 15 páginas, cero errores en consola, dashboard filtro de tiempo funcional, NLP distribución real, KPIs renombrados, sidebar enriquecido.

**Recursos:** Claude Code solo. Playwright para verificación. No requiere skills especiales.

---

### Sprint 2 — Benchmark de Prompts IA (1 día)

**Objetivo:** Crear un runner reproducible para comparar Claude + Gemini + Ollama sobre los mismos prompts, usando el **prompt management existente** (Community 22 del graph).

| ID | Tarea | Archivos | Criterio |
|----|-------|----------|----------|
| S2.1 | Directorio `backend/benchmarks/ai/` con estructura: `prompts/`, `test_cases/`, `rubric.py`, `runner.py`, `outputs/{YYYY-MM-DD}/` | Nuevos | Script `python -m benchmarks.ai.runner` ejecuta los 3 modelos en paralelo |
| S2.2 | Test cases reales Piña + Solano como JSON con el contexto completo (posts scrapeados, IPD components, sentiment breakdown) | `benchmarks/ai/test_cases/*.json` | Cada test case es reproducible |
| S2.3 | **Loop de mejora continua (proceso definitivo)**: (1) mismo prompt se envía a Gemma local, (2) yo (Claude) ejecuto el prompt en esta sesión + se invoca `/gemini analyze` con el mismo prompt, (3) comparo Gemma vs Claude+Gemini como referencia, (4) identifico gaps específicos, (5) ajusto prompt de Gemma y reitero. Documentación de cada iteración en `outputs/{fecha}/iteration_N.md` | `benchmarks/ai/loop.py` | Cada iteración reduce brecha medible entre Gemma y referencia Claude+Gemini |
| S2.4 | Rúbrica para medir "cuánto se aproxima Gemma a Claude+Gemini" en 6 dimensiones: cobertura temas, especificidad accionable, adherencia a hechos CRECE, compliance INE, longitud, ausencia de alucinaciones | `benchmarks/ai/rubric.py` | Score 0-100 por dimensión, gap score total |
| S2.5 | Runner del loop: (a) lee prompt base, (b) envía a Gemma, (c) yo lo respondo + `/gemini analyze`, (d) comparo con rúbrica, (e) sugiero refinamiento de prompt Gemma, (f) repito hasta converger o plateau | `benchmarks/ai/runner.py`, `benchmarks/ai/compare.py` | Output: `outputs/2026-04-XX/iteration_{N}.md` con scores + diff |
| S2.6 | Mínimo 3 iteraciones sobre el prompt de plan generation + commit de versión ganadora al prompt management existente | `backend/app/nlp/prompts/` | El prompt de Gemma mejorado supera baseline en ≥2 dimensiones y queda versionado |

**Verificación:** Un `compare.md` con scores medibles + evidencia de iteración.

**Recursos:** Claude Code + `/gemini analyze` para validación cruzada del rubric + Ollama local.

**Dependencia:** S1.1 (posts con NLP correcto) es pre-requisito para generar test cases realistas.

---

### Sprint 3 — Plan Estructurado + Kanban Editable (6 días)

**Objetivo:** Transformar `plan_ia` de prosa libre a estructura editable con tareas, siguiendo la filosofía "estructurar > delegar".

| ID | Tarea | Archivos | Criterio |
|----|-------|----------|----------|
| S3.1 | **Migración Alembic**: agregar columna `estructura_json JSONB` a `plan_ia`, crear tabla `plan_tareas` | `backend/migrations/versions/` | `alembic upgrade head` ejecuta sin errores |
| S3.2 | **Pydantic schema `PlanTarea`** con constraints estrictos (max chars, enums, rangos de deadline, métricas objetivo) | `backend/app/schemas/plan_ia.py` | Validación rechaza outputs inválidos con mensaje claro |
| S3.3 | **Pydantic schema `PlanEstructurado`**: titulo_campana, tesis_central, lista de tareas min 5 max 20, problematicas_direccionadas | Mismo archivo | Valida plan completo |
| S3.4 | **Reescribir `plan_generator.py`** para usar `AIProvider` existente con **function calling** / JSON mode contra el schema Pydantic | `backend/app/services/plan_generator.py` | Gemma/Claude devuelven JSON válido; si falla, reintento con prompt más estricto (max 2 reintentos) |
| S3.5 | **Excepción en VedaElectoralMiddleware** para creación de planes IA internos (solo bloquea publicaciones externas) | `backend/app/middleware/veda.py` | Se pueden generar planes durante veda; no se pueden publicar contenidos |
| S3.6 | **Endpoints de tareas**: `GET/PATCH /planes/{id}/tareas/{task_id}`, `POST /planes/{id}/tareas/{task_id}/complete` con captura de métrica_real | `backend/app/api/v1/endpoints/planes.py` | Tests unitarios pasan |
| S3.7 | **UI Kanban editable completo**: 3 columnas (To Do / In Progress / Done) + edición inline de cada tarea (titulo, descripcion, deadline, responsable, métrica objetivo). Drag-and-drop entre columnas. Captura de métrica real al completar. | `frontend/src/app/dashboard/planes/[id]/page.tsx` + nuevo componente `TaskEditorDialog` | Drag-and-drop funcional, cada tarea editable inline con validación Pydantic schema (frontend respeta los mismos constraints que backend) |
| S3.7b | **Historial de cambios por tarea** — registro de ediciones humanas vs generación IA con timestamps | Campo `plan_tareas.cambios_historial JSONB` + UI de timeline | Cada edición queda trazable; se puede ver "Gemma generó esto → humano cambió deadline → humano completó con métrica real X" |
| S3.8 | **Dashboard de progreso del plan** en `/dashboard/planes/[id]`: % ejecutado + impacto acumulado | Mismo archivo | Barras visuales con N/total y deltas reales vs objetivo |
| S3.9 | Test E2E con Playwright: generar plan de Piña → ver 10 tareas → completar 2 → verificar % ejecutado | `frontend/e2e/plan-kanban.spec.ts` | Test verde |

**Verificación:** Plan generado con Gemma muestra 10 tareas estructuradas contra Piña. CEO edita manualmente una tarea y completa otra. Dashboard refleja cambios.

**Recursos:** Claude Code + `/backend` + `/frontend` + `/test-v2` + Ollama para generación + Playwright para E2E.

**Dependencia:** S2 (prompts buenos) es pre-requisito. Sin prompts afinados, los planes serán incoherentes.

**Riesgo mitigado:** Gemini alertó que edición profunda sería sobre-ingeniería. Por eso S3.7 es solo cambio de estado, no edición de campos.

---

### Sprint 4 — Motor de Trends MVP (7 días, no 4)

**Objetivo:** Capa de detección de trends encima de los scrapers existentes, sin APIs pagadas, grano geográfico alcaldía.

| ID | Tarea | Archivos | Criterio |
|----|-------|----------|----------|
| S4.1 | **Catálogo de alcaldías INEGI** CDMX (16 alcaldías + polígonos) cargado a PostGIS | `backend/migrations/versions/`, `backend/scripts/seed_alcaldias_cdmx.py` | `SELECT ST_Contains(...)` funciona |
| S4.2 | **Modelo `TopicTrend`**: id, topic_label, topic_embedding (vector 384), alcaldia_id FK, time_bucket TIMESTAMPTZ, post_count, sentiment_avg, growth_rate_24h, sample_posts JSONB, **org_id FK para RLS** | `backend/app/models/topic_trend.py` | Migración pasa |
| S4.3 | **Seed list por alcaldía**: 50-100 cuentas semilla (alcaldía oficial, medios locales, funcionarios, hashtags geo). Inicio con 3 alcaldías piloto (Cuauhtémoc, Benito Juárez, Miguel Hidalgo) | `backend/app/data/seed_accounts_cdmx.yaml`, `backend/scripts/seed_trend_sources.py` | 150-300 cuentas semilla cargadas |
| S4.4 | **Servicio `location_inference.py`**: spaCy NER sobre contenido + match contra catálogo INEGI de lugares MX + fallback a ubicación declarada en bio de cuenta semilla (solo semillas, NO followers) | `backend/app/services/location_inference.py` | Dada un post, retorna alcaldía_id o null |
| S4.5 | **Worker Celery `trends_detector.py`**: cada 1h procesa `social_posts` de las últimas 24h, agrupa por alcaldía con location_inference, clusteriza con HNSW filtrando por `org_id` explícito, calcula growth_rate vs ventana anterior, guarda en `topic_trends` | `backend/app/services/trends_detector.py`, `backend/app/workers/tasks/trends_tasks.py` | Task ejecuta sin errores, llena `topic_trends` |
| S4.6 | **Etiquetado de clusters con Ollama en BATCH async** (no 1-a-1 para no saturar queue) — cola dedicada `trends_labeling` con concurrency limitada | Mismo worker + `backend/app/workers/celery_app.py` config | Clusters obtienen labels humanos sin saturar Ollama |
| S4.7 | **Servicio `news_ingest.py`** + worker para RSS: Presidencia MX, Gaceta CDMX, Congreso, IECM, El Universal, Milenio, Animal Político, Aristegui. Inserta en `social_posts` con `platform='NEWS'` o tabla nueva `news_posts` (decisión en S4.7) | `backend/app/services/news_ingest.py`, `backend/app/workers/tasks/news_tasks.py` | RSS se procesa cada 3h, posts con platform=NEWS existen |
| S4.8 | **Filtro de RLS en HNSW**: confirmar que `find_similar_posts` filtra por `org_id` ANTES del vector search (no después) | `backend/app/services/embeddings.py` + tests | Query con `EXPLAIN` muestra filter antes del knn |
| S4.9 | **Endpoint `GET /trends/geo?alcaldia_id=X&period=Xd`**: top N trends con growth rate, sample posts, label humano | `backend/app/api/v1/endpoints/trends.py` (nuevo) | Retorna JSON válido |
| S4.10 | **Card "Trending ahora en [alcaldía]"** dentro de `/dashboard/social` — NO página nueva. Reusa `Card`, `Badge`, `FilterSelect` existentes | `frontend/src/app/dashboard/social/page.tsx` | Card visible con top 5 trends por alcaldía seleccionada |
| S4.11 | Test E2E con datos reales: correr worker sobre 19 posts Piña → verificar que al menos 1 trend se detecta con label humano | `backend/tests/` | Test verde |

**Verificación:** Worker produce trends etiquetados. UI muestra al menos 1 trend en una alcaldía real. Cero bloqueos de scraper durante el sprint.

**Recursos:** Claude Code + `/backend` + `/geo` (GeoExpert para PostGIS + inferencia) + `/mexico` (fuentes INEGI/INE) + Ollama + Celery + Playwright.

**Dependencias:**
- S4.1 (catálogo) es pre-requisito de S4.4
- S4.5 depende de S4.8 (RLS en HNSW) — **NO revertir orden**
- S4.7 (RSS) es paralelo, puede arrancar al día 3

**Riesgos aceptados:**
- Scrapers pueden romper 2 de 8 durante el sprint (budget: 1 día de fix, incluido en los 7)
- Inferencia de ubicación será ~60-70% precisión (suficiente para MVP, no para producción)
- 3 alcaldías piloto → si va bien, se extiende a 16 en sprint futuro

**Cortes de scope confirmados:**
- ❌ Muestreo de followers de semillas (shadowban)
- ❌ Threads scraping (baja adopción)
- 🟡 TikTok se intenta solo si queda tiempo

---

### Sprint 5 — Wizard Onboarding Político Admin (1.5 días)

**Objetivo:** Alta de político nuevo por admin en <5 minutos, con data real desde el momento 1.

| ID | Tarea | Archivos | Criterio |
|----|-------|----------|----------|
| S5.1 | Ruta `/dashboard/sistema/onboarding` dentro del sidebar "Sistema" (NO top-level `/admin`) | `frontend/src/app/dashboard/sistema/onboarding/page.tsx` | Ruta accesible solo para admin |
| S5.2 | Form wizard 3 pasos con shadcn `Tabs` o stepper: (1) Datos básicos nombre/cargo/org, (2) Handles por plataforma con validación en vivo + preview del perfil scrapeado, (3) Confirmación + trigger | Mismo archivo + nuevo componente `OnboardingWizard` | 3 pasos navegables |
| S5.3 | Endpoint `POST /dirigentes/onboard` que: (a) crea User con org_id, (b) crea Dirigente scopado, (c) crea SocialProfile por handle, (d) dispara Celery chain: scrape inicial → NLP → cálculo IPD | `backend/app/api/v1/endpoints/dirigentes.py` + task en `workers/` | Endpoint devuelve task_id |
| S5.4 | **Progress UI en vivo**: polling cada 2s a `GET /dirigentes/{id}/onboarding-progress` → muestra etapas: scraping IG...OK, Twitter...OK, NLP...en curso, IPD...pendiente | Endpoint + componente React con estados visuales | Usuario ve progreso sin recargar |
| S5.5 | **Auto-login como el nuevo dirigente** al terminar → para que el admin vea lo que el cliente verá | Mismo endpoint + redirect con token temporal | Admin termina el wizard y cae en `/dashboard` viendo como Piña |
| S5.6 | Test E2E con Playwright: admin crea "Test Político" con handles válidos → espera progress → verifica dashboard popula | `frontend/e2e/onboarding.spec.ts` | Test verde |

**Verificación:** Admin crea un político nuevo en <5 minutos, el dashboard se llena con datos reales scrapeados.

**Recursos:** Claude Code + `/frontend` + `/backend` + Playwright.

**Dependencia:** S1.2 (RLS verificado). Sin esto, el onboarding puede romper aislamiento multi-tenant.

---

## Resumen ejecutivo

| Sprint | Duración | Entregable clave | Dependencia |
|--------|----------|------------------|-------------|
| S1 Saneamiento | 1.5 días | Bugs resueltos + RLS verificado + NLP real | — |
| S2 Benchmark | 1 día | Runner reproducible + prompts mejorados | S1.1 |
| S3 Plan estructurado | 6 días | Plan IA → Kanban editable con tracking | S2 |
| S4 Motor trends | 7 días | Trends por alcaldía + ingest de noticias | S1 + S3 (RLS en HNSW) |
| S5 Wizard onboarding | 1.5 días | Alta de político <5 min end-to-end | S1.2 |

**Total calendarizado:** 17 días (~3.5 semanas de trabajo real)
**Total con buffer 20%:** 20.5 días (~4 semanas)

## Filosofía aplicada

1. **Estructura > Delegación**: Pydantic schemas en plan_generator, HNSW clustering en trends (no "pide a Gemma que detecte trends"), validación en middleware, rubric determinista en benchmark.
2. **Cero mockups**: S1.6 audita hardcoding, S5 garantiza datos reales desde onboarding, S2 usa test cases reales de Piña/Solano.
3. **Cero APIs pagadas**: Solo pytrends (no SerpAPI), praw (no Apify), scrapers propios + RSS libres.
4. **Extender antes que crear**: Reusa AIProvider, prompt management, NLPAnalyzer, platform_weights, pgvector HNSW, FunnelBar, FilterSelect, IpdRadarChart, y las 16 páginas existentes. Solo se crean archivos donde no hay nada equivalente (topic_trend model, trends_detector service, benchmark runner).

## Criterios de aceptación globales

- [ ] 148+ tests siguen en verde al final de cada sprint
- [ ] Playwright verifica end-to-end las nuevas features contra datos reales
- [ ] Cero consola errors en las 16 páginas del dashboard
- [ ] El admin puede dar de alta un nuevo político en <5 minutos
- [ ] Login como Piña NO muestra data de Solano (RLS verificado)
- [ ] Un plan IA se puede generar → editar estado de tareas → medir impacto real
- [ ] Trends de al menos 1 alcaldía aparecen en `/dashboard/social` con label humano

## Riesgos identificados y mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| RLS + pgvector fuga de contexto entre orgs | Media | Alto | S4.8 filtra `org_id` ANTES del vector search; test explícito con 2 orgs |
| Scrapers rompen durante Sprint 4 | Alta | Medio | 1 día de buffer en S4; librerías probadas (D11) |
| Bio-NER precisión baja | Alta | Medio | Aceptar 60-70% en MVP; marcar posts sin ubicación como "nacional" |
| Ollama latencia en multi-tenant | Media | Medio | S4.6 usa queue dedicada con concurrency limitada |
| Edición de planes "se va de scope" | Alta | Medio | S3.7 limitado a 3 columnas sin edición profunda (confirmado con Gemini) |
| Veda electoral bloquea tareas internas | Baja | Alto | S3.5 agrega excepción explícita |
| Demo users no son realmente scopados | Media | Crítico | S1.2 lo verifica antes de cualquier otra cosa |

## Cross-audit de Gemini — hallazgos aplicados

✅ **Aplicado:** Fix NLP antes de benchmark (evita GIGO)
✅ **Aplicado:** Motor de trends 7 días, no 4
✅ **Aplicado:** Sin muestreo de followers (shadowban)
✅ **Aplicado:** Kanban simple 3 columnas
✅ **Aplicado:** Filtrado org_id antes de vector search
✅ **Aplicado:** Excepción veda para tareas internas
✅ **Aplicado:** Ollama queue dedicada con concurrency

## Estado

**Este plan está en ESPERANDO APROBACIÓN.** No se ha tocado un solo archivo del proyecto. Esperando luz verde del CEO para arrancar por Sprint 1.

**Próximo paso recomendado:** Arrancar Sprint 1 tarea S1.1 (correr NLP sobre 19 posts de `/social`) como primera acción concreta — es la más aislada, la de menor riesgo, y desbloquea todo lo demás.

---

# Plan revisado 2026-04-11 (/sprint-review)

**Contexto:** S1, S2, S3 y cross-project n8n-mexico cerrados. Quedan **S4 y S5**. Esta sección enriquece las tareas abiertas con criterios medibles, subdivisiones concretas y orden de ejecución ajustado.

## S4 — Motor de Trends MVP (revisado)

### Estado real post-review
- **S4.1 ✅ DONE** (commit `9efc76d` en `fix/sprint-4-trends`): 16 alcaldías INEGI en PostGIS, `ST_Contains` verificado contra 3 puntos conocidos.
- S4.2–S4.11 pendientes.

### Subdivisiones y criterios concretos

| ID | Sub | Criterio medible | Dep | Paralelizable |
|---|---|---|---|---|
| **S4.1** | — | ✅ 16 rows + índice GIST + `ST_Contains` verdadero sobre Zócalo/Del Valle/Polanco | — | — |
| **S4.2a** | Modelo `TopicTrend` con `org_id`, `alcaldia_id` FK, `time_bucket`, `post_count`, `growth_rate_24h`, `sample_posts JSONB` | migración aplica sin errores | S4.1 | — |
| **S4.2b** | Columna `topic_embedding Vector(384)` + índice HNSW (`lists` o `m/ef_construction` según pgvector versión) | `\d topic_trends` muestra vector + idx hnsw | S4.2a | — |
| **S4.2c** | Policy RLS sobre `topic_trends` scoping por `org_id` | `SET app.current_org_id=1; SELECT` no ve org=2 | S4.2a | — |
| **S4.3a** | Schema YAML `seed_accounts_cdmx.yaml` con 3 alcaldías piloto (CUA/BJ/MH), campos: handle, platform, tipo (oficial/medio/funcionario), alcaldia_cvegeo | YAML lint valida contra pydantic `SeedAccount` | — | SÍ (paralelo a S4.2) |
| **S4.3b** | 50 cuentas semilla por alcaldía piloto (150 totales) | `len(yaml)==150` + no duplicados por (handle,platform) | S4.3a | — |
| **S4.3c** | Script `seed_trend_sources.py` idempotente que persiste en `social_profiles` con `is_seed=True` | 150 rows, reejecutable sin duplicar | S4.3b + S4.1 | — |
| **S4.4a** | Reemplazar dicts in-memory de `location_inference.py` por query a `alcaldias_cdmx` via ST_Contains | test unitario: 5 coords conocidas resuelven correctamente | S4.1 | — |
| **S4.4b** | Integrar spaCy `es_core_news_md` NER sobre `content` → extract GPE+LOC | 1 ejemplo real de post Piña con "Cuauhtémoc" retorna alcaldia_id correcto | S4.4a | — |
| **S4.4c** | Fallback: bio de cuenta semilla si NER no matchea | test: post sin mención pero con bio "Miguel Hidalgo" → MH con confidence 0.5 | S4.4b | — |
| **S4.5a** | Worker Celery `trends_detector` scaffold con schedule 1h | `celery beat` agenda la task, logs muestran ejecución | S4.2 + S4.8 | — |
| **S4.5b** | Pipeline: cargar social_posts últimas 24h → inferir alcaldía → agrupar por embedding HNSW filtrado por `org_id` ANTES del knn | EXPLAIN ANALYZE muestra filter antes de Index Scan on hnsw | S4.5a | — |
| **S4.5c** | Cálculo `growth_rate_24h` vs ventana anterior + persistencia en `topic_trends` | rows con growth_rate != 0 existen post-run | S4.5b | — |
| **S4.6a** | Cola Celery dedicada `trends_labeling` con concurrency=2 en `celery_app.py` | `celery inspect active_queues` muestra la cola | S4.5a | SÍ (con S4.5) |
| **S4.6b** | Task batch que toma N clusters y pide labels a Ollama con prompt estricto (1 line, <50 chars, castellano, sin emojis) | 5 clusters etiquetados en <2 min, 0 failures | S4.6a + S4.5c | — |
| **S4.7a** | Servicio `news_ingest.py` — parser RSS agnóstico con httpx + feedparser | test sobre feed sintético devuelve N items | — | SÍ (día 3+) |
| **S4.7b** | Lista de fuentes RSS: Presidencia MX, Gaceta CDMX, Congreso CDMX, IECM, El Universal, Milenio, Animal Político, Aristegui | 8 URLs probadas manualmente, HEAD 200 | — | SÍ |
| **S4.7c** | Worker `news_tasks` cada 3h, persiste en `social_posts` con `platform='NEWS'` (decisión: NO crear tabla nueva, reusar schema existente) | rows con platform=NEWS existen post-run | S4.7a+b | SÍ |
| **S4.8** | **AUDIT DE SEGURIDAD**: `embeddings.find_similar_posts()` filtra `org_id` ANTES del vector search en HNSW. Test con 2 orgs, query desde org=1 NO devuelve post de org=2 | test explícito `test_rls_vector_search.py` verde | — (puede ir el día 1, paralelo a S4.2) | SÍ |
| **S4.9** | Endpoint `GET /trends/geo?alcaldia_id=X&period=24h\|7d\|30d` con response schema `TopicTrendResponse` | retorna 200 + JSON válido para alcaldía conocida; 404 para desconocida | S4.5c | — |
| **S4.10** | Card "Trending ahora en [alcaldía]" en `/dashboard/social` (NO nueva página), reusa `Card`, `Badge`, `FilterSelect` | card visible con top 5 + filtro alcaldía cambia data | S4.9 | — |
| **S4.11** | Test E2E worker sobre 19 posts reales de Piña → al menos 1 trend detectado con label humano | `pytest -k test_trends_over_real_posts` verde | S4.5c + S4.6b | — |

### Ruta crítica S4 (tras la revisión)
```
S4.1 ✅ → S4.8 (audit RLS) → S4.2a/b/c (modelo) → S4.4a (catalog lookup) → S4.5a/b/c (worker)
                                                                              ↓
                                                       S4.3a/b/c (seeds) ─────┤
                                                                              ↓
                                                                           S4.6a/b (labels)
                                                                              ↓
                                                                           S4.9 → S4.10 → S4.11
```
Paralelo desde día 1: **S4.7 RSS ingest** y **S4.3 seed YAML** pueden arrancar sin dependencia.

### Cambios vs plan original
1. **S4.1 ejecutado hoy** con GeoJSON INEGI 2023 redistribuido (opción 1 confirmada por CEO), en vez de shapefile directo. Contenido idéntico: CVEGEO/CVE_ENT/CVE_MUN/NOMGEO preservados. Razón: evita dep nueva de geopandas/fiona (~200MB imagen Docker).
2. **S4.2 dividido en 3** (modelo/pgvector/RLS) porque pgvector HNSW + policy RLS no son triviales y merecen commits independientes.
3. **S4.4 dividido en 3** para separar "reemplazar stub in-memory por query DB" (fácil, hoy) de "agregar spaCy real" (medio) de "bio fallback" (fácil).
4. **S4.8 movido al día 1** (era criterio de orden pero estaba implícito). Es el audit de seguridad más importante del sprint: si `find_similar_posts` no filtra `org_id` antes del HNSW, toda la feature sale inusable en multi-tenant.
5. **S4.7 marcada paralelizable** para evitar bloqueo del día 3 en adelante.
6. **S4.11 aclarado**: "19 posts reales" significa usar los posts ya scrapeados de Piña en dev DB, NO scrapear de nuevo.

### Ajustes post cross-audit Gemini (2026-04-11)

**G1 — Orden correcto de S4.2: `a → c → b`, no `a → b → c`.**
Activar policies RLS **antes** de crear el índice HNSW evita ventanas de fuga durante la ingesta inicial. Secuencia corregida:
1. S4.2a — CREATE TABLE `topic_trends` con columnas base + FKs
2. S4.2c — CREATE POLICY RLS sobre `topic_trends` (scope `org_id`)
3. S4.2b — ALTER TABLE ADD COLUMN `topic_embedding vector(384)` + CREATE INDEX HNSW
   - Antes del índice: `SET maintenance_work_mem='512MB'` (HNSW es memory-intensive, el default 64MB hace thrashing con vectores de 384 dims)

**G2 — S4.8 reposicionado: DESPUÉS de S4.2b, ANTES de S4.5.**
No se puede auditar comportamiento de HNSW+RLS sin el índice creado. El EXPLAIN ANALYZE de `find_similar_posts` no tiene sentido si el planner no tiene el hnsw disponible. Nueva ruta crítica:
```
S4.1 ✅ → S4.2a → S4.2c (RLS) → S4.2b (HNSW) → S4.8 (audit) → S4.5 (worker)
```

**G3 — S4.4 necesita pre-processor de normalización social antes del NER.**
spaCy `es_core_news_md` baja precisión drásticamente con texto social crudo. Nueva subtarea:
- **S4.4a.5** — `normalize_social_text()`: strip emojis, convertir `@handles` a placeholder, expandir `#hashtags` a tokens separados, colapsar whitespace. Probar antes y después con un post real de Piña para medir delta.

**G4 — S5.3a debe retornar `sync_status='pending'` inmediatamente.**
El endpoint transaccional crea User+Dirigente+SocialProfile y retorna 201 con `{..., sync_status: "pending", task_id: "..."}` para que el wizard UI muestre el dirigente inmediatamente y el polling de S5.4 comience. Agregar columna `dirigentes.sync_status ENUM('pending','scraping','analyzing','ready','error')` en la migración de S5.3a.

Todos los ajustes integrados en las tablas de subdivisiones arriba y en la ruta crítica.

### Riesgos nuevos identificados
- **R1**: `spaCy es_core_news_md` no está instalado en el contenedor. Download es ~50MB, aceptable. Alternativa: `es_core_news_sm` (~15MB) con precisión menor.
- **R2**: pgvector HNSW requiere versión ≥0.5.0. Verificar con `SELECT extversion FROM pg_extension WHERE extname='vector'` antes de S4.2b.
- **R3**: feedparser no está en `requirements.txt`. Agregar en S4.7a.

## S5 — Wizard Onboarding Político (revisado)

### Subdivisiones y criterios

| ID | Sub | Criterio medible | Dep |
|---|---|---|---|
| **S5.1** | Ruta `/dashboard/sistema/onboarding` visible solo a `role=admin` | guard redirige a /dashboard si user.role != admin | S1.2 (verified) |
| **S5.2a** | Step 1: Datos básicos (nombre, cargo, org, email login, password temporal) | validación Zod frontend + Pydantic backend | S5.1 |
| **S5.2b** | Step 2: Handles por plataforma con validación en vivo (IG/X/FB/TikTok/YT) + preview OpenGraph | preview card renderiza cuando handle es válido | S5.2a |
| **S5.2c** | Step 3: Confirmación + botón "Crear dirigente" | click dispara POST /dirigentes/onboard | S5.2b |
| **S5.3a** | Endpoint `POST /dirigentes/onboard` que crea User + Dirigente + SocialProfile en 1 transacción | 409 si email existe, 201 + ids si OK | — |
| **S5.3b** | Celery chain: `scrape_initial → compute_nlp → calculate_ipd` | `task_id` retornado, redis muestra chain activa | S5.3a |
| **S5.4** | Endpoint `GET /dirigentes/{id}/onboarding-progress` retorna `{step, status, progress_pct}` | polling 2s muestra 5 estados: scraping/nlp/ipd/done/error | S5.3b |
| **S5.5** | Auto-login como nuevo dirigente con token temporal al finalizar chain | redirect a `/dashboard` loggeado como el nuevo dirigente | S5.4 |
| **S5.6** | E2E Playwright: crear "Test Político" con handles de fixture → espera progress → verifica dashboard | test verde, cleanup del user test al final | S5.5 |

### Cambios vs plan original
1. **S5.2 dividido en 3 pasos explícitos** (a/b/c) para mapear 1:1 con el UI Tabs.
2. **S5.3 dividido en "endpoint transaccional" vs "celery chain"** para que el endpoint pueda testearse sin workers corriendo.
3. **S5.4 aclarado**: el endpoint de progress DEBE existir aunque no haya chain — retorna estado inicial "scraping pending".

## Orden de ejecución propuesto (7.5 días nominales)

| Día | Mañana | Tarde |
|---|---|---|
| 1 | S4.1 ✅ + S4.8 audit RLS | S4.2a/b/c modelo + pgvector + policy |
| 2 | S4.3a/b/c seeds YAML | S4.4a/b/c location_inference real |
| 3 | S4.5a scaffold worker | S4.5b/c pipeline + growth_rate |
| 4 | S4.6a/b labeling batch Ollama | S4.7a/b/c RSS ingest (paralelo) |
| 5 | S4.9 endpoint /trends/geo | S4.10 UI card + S4.11 E2E real |
| 6 | S5.1 + S5.2a/b/c wizard UI | S5.3a endpoint transaccional |
| 7 | S5.3b celery chain + S5.4 progress | S5.5 auto-login + S5.6 E2E |
| 7.5 | Buffer: tests green + commits | Reporte final |

## Fase 3 — Asignación de recursos

### Agentes primarios por tarea

| Tarea | Agente(s) | Skill(s) cargado(s) | Herramientas |
|---|---|---|---|
| S4.1 ✅ | `/backend` + `/geo` + `/mexico` | `postgis`, `docker` | psql, shapely |
| S4.2a (modelo) | `/backend` + `/database` | `postgis`, `fastapi` | alembic |
| S4.2c (RLS) | `/security-engineer` + `/database` | `postgresql` Tier-1 | psql EXPLAIN |
| S4.2b (HNSW) | `/database` + `/performance-engineer` | `pgvector` | psql, `SET maintenance_work_mem` |
| S4.3 (seeds) | `/mexico` + `/backend` | — | yaml schema |
| S4.4 (location) | `/backend` + `/geo` + `python-expert` | — | spaCy es_core_news_md |
| S4.4a.5 (normalize) | `/backend` | — | regex, emoji lib |
| S4.5 (worker) | `/backend` + `/devops-architect` | `docker` | Celery, redis-cli |
| S4.6 (Ollama batch) | `/backend` | — | Ollama HTTP, Celery |
| S4.7 (RSS) | `/backend` + `/mexico` | — | feedparser, httpx |
| S4.8 (audit RLS) | `/security-reviewer` + `security-engineer` | `postgresql` | psql EXPLAIN ANALYZE |
| S4.9 (endpoint) | `/backend` | `fastapi` | pytest |
| S4.10 (UI card) | `/frontend` + `/tailwind` | `shadcn-ui`, `tailwindcss-v4` | Playwright MCP |
| S4.11 (E2E trend real) | `/test-v2` + `/test-planning` | `playwright-testing` | pytest |
| S5.1 (route) | `/frontend` + `/nextjs` | `nextjs-app-router` | — |
| S5.2 (wizard UI) | `/ui-design` + `/frontend` | `shadcn-ui`, `react-ui-patterns` | shadcn MCP |
| S5.3a (endpoint tx) | `/backend` | `fastapi` | alembic |
| S5.3b (celery chain) | `/backend` + `/devops-architect` | `bullmq-specialist` adaptado | Celery |
| S5.4 (progress) | `/backend` + `/frontend` | `react-ui-patterns` (polling) | — |
| S5.5 (auto-login) | `/security-engineer` + `/backend` | `clerk-auth` patterns | JWT debug |
| S5.6 (E2E Playwright) | `/test-v2` | `playwright-testing` | Playwright MCP |

### Herramientas de verificación continua
- **Playwright MCP** — screenshots + E2E para S4.10, S5.2, S5.6
- **Chrome DevTools MCP** — network/console monitoring para validar S4.9 + S4.10 en runtime
- **psql EXPLAIN ANALYZE** — obligatorio en S4.2b, S4.5b, S4.8
- **pgvector stats** — medir build time del HNSW index (para informar decisiones futuras)
- **Ollama latencia local** — medir tiempo por batch en S4.6b, presupuesto <2min/5clusters

### Lo que NO se usa en este sprint
- No hay nuevas APIs pagadas (se respeta regla D11)
- No se tocan endpoints de la deuda D-SEC-03 (21 endpoints dual-auth) — diferido a PR dedicado
- No se tocan migraciones drift (embedding, last_scraped_at, secciones constraint) — diferido

## Criterios de aceptación globales (revisados)

- [x] 148+ tests siguen en verde al final de cada sprint (pendiente a verificar tras cada commit)
- [x] RLS + HNSW filtrado correctamente (test explícito S4.8)
- [x] Trends de al menos 1 alcaldía en `/dashboard/social`
- [x] Admin crea político en <5 min end-to-end (S5.6)
- [ ] Cero consola errors en las 16+ páginas del dashboard
- [ ] Mapa canvassing geo con 9,631 ciudadanos reales (Sprint B)
- [ ] Demo interna 30 min preparada (Sprint A)

---

# Sprint B — Canvassing Geo: Mapa de Quién Visitar (2026-04-12)

**Fecha:** 2026-04-12
**Estado:** EN EJECUCIÓN
**Aprobado por CEO:** Sí (Opción B primero, luego A)
**Branch:** `feat/canvassing-geo-map`

## Contexto

9,723 ciudadanos reales importados del CRECE Oracle APEX legacy (D-DATA-01 Ruta C).
99% con coordenadas GPS (9,631/9,723). 3 alcaldías piloto: Cuauhtémoc (6,643),
Miguel Hidalgo (2,267), Benito Juárez (813). Unidades territoriales con volatilidad
electoral (0-100) y estrato socioeconómico. PII encriptado con pgcrypto (D-DATA-02).

La infraestructura de canvassing (endpoints, modelos, hooks, page) ya existe al 80%.
Lo que falta es:
1. Endpoint que retorne ciudadanos_legacy como GeoJSON con filtros de segmentación
2. Mapa MapLibre real reemplazando el placeholder "Mapa disponible proximamente"
3. Filtros sidebar para segmentar por estrato, volatilidad, nivel_participacion

**Killer feature:** "Mapa de quién visitar y dónde, segmentado por volatilidad electoral."

## Inventario de lo que YA existe

| Componente | Estado | Archivo |
|---|---|---|
| Backend canvassing: 7 endpoints (optimize, routes, nearby, etc.) | Funcional, opera sobre `Ciudadano` v2 | `backend/app/api/v1/endpoints/canvassing.py` |
| Modelos: RutaCanvassing, PuntoRuta (PostGIS) | Funcional | `backend/app/models/canvassing.py` |
| Service: optimize_route_postgis, nearest-neighbor CTE | Funcional | `backend/app/services/canvassing.py` |
| CiudadanoLegacy modelo (lat/lon, seccion, UT FK) | Funcional, 9,723 rows | `backend/app/models/legacy.py` |
| UnidadTerritorial (volatilidad, estrato, categoria) | Funcional, 5,552 rows | `backend/app/models/unidad_territorial.py` |
| Endpoint /ciudadanos-legacy/ (safe rows + PII gated) | Funcional | `backend/app/api/v1/endpoints/ciudadanos_legacy.py` |
| Frontend page canvassing (route list + placeholder map) | Stub mapa | `frontend/src/app/dashboard/canvassing/page.tsx` |
| API hooks canvassing (useRoutes, useNearby, etc.) | Funcional | `frontend/src/lib/api/hooks/use-canvassing.ts` |
| MapLibre GL JS v4.7.1 | Instalado | `frontend/package.json` |
| ElectoralMap componente (template reutilizable) | Funcional | `frontend/src/components/maps/electoral-map.tsx` |
| MapLegend componente | Funcional | `frontend/src/components/maps/map-legend.tsx` |

## Tareas

### B.1 — Endpoint `GET /canvassing/geo` (GeoJSON FeatureCollection)

**Archivo:** `backend/app/api/v1/endpoints/canvassing.py` (agregar al router existente)

**Query params:**
- `alcaldia_id: int | None` — filtro por alcaldía INEGI
- `estrato: str | None` — "MUY BAJO", "BAJO", "MEDIO BAJO", "MEDIO", "MEDIO ALTO/ALTO"
- `volatilidad_min: float | None` — umbral mínimo (0-100)
- `volatilidad_max: float | None` — umbral máximo
- `nivel_participacion: int | None` — 1, 2 o 3
- `contactado: str | None` — "SI", "NO"
- `seccion: str | None` — sección electoral específica
- `limit: int = 2000` (ge=1, le=5000) — MapLibre maneja miles de puntos con clustering

**Response:** GeoJSON FeatureCollection donde cada Feature tiene:
- `geometry`: Point(longitud_cd, latitud_cd)
- `properties`: id, nombre (solo inicial + apellido), edad, sexo, nivel_educativo,
  nivel_participacion, colonia_texto, seccion, estrato (from UT join),
  volatilidad (from UT join), categoria (from UT join), contactado, lista

**NO incluye:** email, phone, whatsapp, fecha_nacimiento, clave_electoral (PII)

**Join:** `ciudadanos_legacy` LEFT JOIN `unidades_territoriales` ON `unidad_territorial_id`
para obtener estrato, volatilidad, categoria.

**Auth:** `get_current_user` + `RoleChecker([ADMIN, ANALYST])`. Scoped por `org_id`.

**Criterio de aceptación:**
- `curl /canvassing/geo?alcaldia_id=12` retorna GeoJSON válido con ~6,642 features
- `curl /canvassing/geo?estrato=MEDIO+ALTO/ALTO&alcaldia_id=2` retorna ~200 features (BJ es MEDIO/MEDIO ALTO)
- `curl /canvassing/geo?volatilidad_min=30` filtra correctamente
- Response time < 2s para 5000 features

**Dependencias:** Ninguna nueva. Reutiliza modelos existentes.

### B.2 — Endpoint `GET /canvassing/geo-stats` (agregados para sidebar)

**Archivo:** Mismo `canvassing.py`

**Response:**
```json
{
  "total": 9723,
  "con_geo": 9631,
  "por_alcaldia": [
    {"alcaldia_id": 12, "nombre": "CUAUHTEMOC", "count": 6643},
    {"alcaldia_id": 15, "nombre": "MIGUEL HIDALGO", "count": 2267},
    {"alcaldia_id": 2, "nombre": "BENITO JUAREZ", "count": 813}
  ],
  "por_estrato": [
    {"estrato": "MUY BAJO", "count": N},
    {"estrato": "BAJO", "count": N},
    ...
  ],
  "por_nivel_participacion": [
    {"nivel": 1, "count": 137},
    {"nivel": 2, "count": 171},
    {"nivel": 3, "count": 294}
  ]
}
```

**Criterio:** Response time < 500ms. Counts coinciden con DB.

### B.3 — Componente `CanvassingGeoMap` (MapLibre + clustering)

**Archivo nuevo:** `frontend/src/components/maps/canvassing-geo-map.tsx`

**Specs:**
- MapLibre GL JS con center en CDMX (-99.133, 19.432), zoom 11
- Estilo base: `https://demotiles.maplibre.org/style.json` (mismo que electoral-map)
- GeoJSON source dinámico (se actualiza al cambiar filtros)
- **Clustering:** activado a zoom < 14. Cluster circles con count label.
- **Colores por estrato** (modo default):
  - MUY BAJO: `#ef4444` (red)
  - BAJO: `#f97316` (orange)
  - MEDIO BAJO: `#eab308` (yellow)
  - MEDIO: `#22c55e` (green)
  - MEDIO ALTO/ALTO: `#3b82f6` (blue)
- **Colores por nivel_participacion** (modo alternativo):
  - 1: `#ef4444` (bajo)
  - 2: `#eab308` (medio)
  - 3: `#22c55e` (alto)
  - null: `#94a3b8` (sin dato)
- **Popup al click:** nombre (inicial), edad, colonia, sección, estrato, contactado
- NavigationControl top-right
- Reutilizar MapLegend existente

**Props:** `data: GeoJSON.FeatureCollection`, `colorMode: "estrato" | "participacion"`, `className`

**Criterio:** Renderiza 6,642 puntos de Cuauhtémoc sin jank. Clusters se expanden al hacer zoom.

### B.4 — Filtros sidebar + hooks + integración en page

**Archivos:**
- `frontend/src/lib/api/hooks/use-canvassing.ts` (agregar `useCanvassingGeo`, `useCanvassingGeoStats`)
- `frontend/src/app/dashboard/canvassing/page.tsx` (reescritura parcial)

**UI Layout (nueva):**
```
┌─────────────────────────────────────────────────┐
│ Smart Canvassing — Mapa de Campo        [+Ruta] │
├──────────┬──────────────────────────────────────┤
│ FILTROS  │                                      │
│          │         MAPA MAPLIBRE                │
│ Alcaldía │         (CanvassingGeoMap)           │
│ Estrato  │                                      │
│ Volat.   │                                      │
│ Partic.  │                                      │
│ Contact. │                                      │
│          │                                      │
│ STATS    │                                      │
│ N total  │                                      │
│ N filtrd │                                      │
├──────────┴──────────────────────────────────────┤
│ [Tab: Rutas]  [Tab: Puntos de visita]           │
│ (contenido existente de RouteCard + puntos)     │
└─────────────────────────────────────────────────┘
```

- Filtros en sidebar izq (lg:col-span-2)
- Mapa ocupa el espacio principal (lg:col-span-3)
- Contenido existente (rutas + puntos) se mueve a tabs debajo del mapa
- Modo de color toggle: "Por Estrato" / "Por Participación"

**Criterio:** Cambiar filtro refresca el mapa sin reload. Stats sidebar se actualizan.

### B.5 — Smoke test endpoints + visual verification

- `curl -H "Authorization: Bearer $TOKEN" /canvassing/geo?alcaldia_id=12 | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Features: {len(d[\"features\"])}')"` → ~6,642
- `curl /canvassing/geo-stats` → JSON con totales correctos
- Verificación visual: abrir `/dashboard/canvassing` en browser, confirmar mapa renderiza

**Criterio:** Endpoints retornan data correcta. Mapa visible con pins.

## Ruta crítica Sprint B

```
B.1 (endpoint geo) ──→ B.3 (component) ──→ B.4 (integration) ──→ B.5 (verify)
B.2 (stats endpoint) ─┘                  ┘
```

B.1 y B.2 son paralelizables. B.3 puede arrancar con data mock mientras B.1 termina.
B.4 necesita B.1 + B.2 + B.3. B.5 es verificación final.

## Asignación de recursos Sprint B

| Tarea | Agente(s) | Skill(s) | Herramientas |
|---|---|---|---|
| B.1 | `/backend` + `/geo` | `fastapi`, `postgis` | psql, curl |
| B.2 | `/backend` | `fastapi` | psql |
| B.3 | `/frontend` | `shadcn-ui`, `tailwindcss-v4` | MapLibre docs |
| B.4 | `/frontend` + `/ui-design` | `shadcn-ui`, `react-ui-patterns` | — |
| B.5 | `/test-v2` | — | curl, browser |

## Decisiones pre-tomadas Sprint B

### D-B-01: GeoJSON inline vs tile server
**Decisión:** GeoJSON inline en el response del endpoint, NO tile server MVT.
**Razón:** 9,723 puntos caben en un GeoJSON de ~2-3MB. MapLibre maneja esto sin
problema con clustering. Un tile server añade complejidad innecesaria para este
volumen. Si escala a 63K (import full), reconsiderar.

### D-B-02: Agregar al router canvassing existente, NO crear router nuevo
**Decisión:** Los endpoints B.1 y B.2 se agregan a `canvassing.py` existente.
**Razón:** Conceptualmente es canvassing (segmentación de campo). Mantener un solo
router evita fragmentación. Los endpoints legacy de rutas conviven sin conflicto.

### D-B-03: Nombre privacy — solo inicial del nombre en el mapa
**Decisión:** El GeoJSON retorna `nombre` como "A. Pérez" (inicial + apellido), no
el nombre completo. El nombre completo solo se ve en el popup al hacer click.
**Razón:** El mapa es visible para analyst + admin. Minimizar exposure de datos
personales en la vista general.

---

# Sprint A — Demo Interna 30 min (post Sprint B)

**Fecha:** 2026-04-12 (después de Sprint B)
**Estado:** PENDIENTE

## A.1 — Guion de demo

**Audiencia:** Equipo MC + dirigentes piloto (Piña/Solano)
**Duración:** 30 minutos
**Formato:** Live demo sobre backend local + Vercel frontend (o localhost)

### Escenas propuestas

| Min | Escena | Login | Qué se muestra |
|---|---|---|---|
| 0-2 | Intro | — | Pitch: qué es CRECE v2, stack, alcance |
| 2-8 | Dashboard político | Piña | KPIs, posts con NLP real, trends, sentiment |
| 8-12 | **Mapa canvassing** | Admin | Filtrar por alcaldía + estrato, ver pins, zoom, popups |
| 12-16 | Wizard onboarding | Admin | Crear "Político Demo", ver progress chain |
| 16-20 | Plan IA + Kanban | Piña | Generar plan, ver tareas, mover estado |
| 20-24 | Ciudadanos legacy | Admin | Listado safe, acceso PII con audit log |
| 24-28 | Q&A | — | Preguntas |
| 28-30 | Cierre | — | Roadmap Fase 2, próximos pasos |

### Prep necesario
- Verificar que el mapa canvassing B.5 funciona end-to-end
- Verificar credenciales demo (admin, Piña, Solano)
- Verificar Ollama corriendo para Plan IA live
- Preparar 1-2 screenshots de respaldo por si algo falla en vivo

