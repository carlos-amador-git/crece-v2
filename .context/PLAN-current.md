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
