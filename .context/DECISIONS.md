# CRECE v2.0 — Decisiones Arquitecturales

## 2026-06-13 — ADR-005 (botón Sincronizar RADAR) + ADR-006 (dedup fans author_hash)

**ADR-005 · Quién dispara la actualización (Accepted):** botón "Sincronizar con RADAR" en
`/dirigentes/[id]` — trigger ADMIN/ANALYST (entrega de servicio, no self-service); VIEWER ve badge
de frescura. `POST /api/v1/ingest/sync/{id}` descubre el último bundle en MinIO e ingiere (Celery,
idempotente). Construido por `gemini --yolo` lanzado por mí; verificado/consolidado por mí
(ejecutor≠auditor). Verificado E2E en la app.

**ADR-006 · Dedup de fans por author_hash (Accepted):** RADAR cambia `profile_external_id` del
mismo fan entre capturas → N watched_profiles → ranking inflaba ~2x (Pedro Carlock 988=suma de 4
perfiles vs 514 real). Fix presentación (NO toca BD): ranking agrupa por `author_hash`, `n_likes =
COUNT(DISTINCT post_id)`; conteo `COUNT(DISTINCT author_hash)`. Cross-audit Gemini. NO afecta
D's/IPD/bots. **Deudas escaladas:** causa raíz = UPSERT por author_hash en ingesta RADAR (sino
crece 23%→50%/mes) · normalización nombres (18k variantes) · recalibrar Misael VIP >514 (regla 12).

**Proceso (lección):** `gemini --yolo` da permiso de ESCRITURA → para consultas usar gemini SIN
`--yolo`. Verificar dato real (no "COMPLETED"). Usar la app antes de teorizar.

---

## 2026-05-26 noche — D-AUTHOR-HASH-PII · pseudonimización canónica + guard

**Contexto:** 257 filas (242 social_comments + 15 watched_profiles) tenían el NOMBRE REAL en `author_hash` sin hashear (ruta RADAR FB Playwright). PII en texto plano (LFPDPPP) + rompía dedup + falsos "coordinación" en B12.

**Decisión:** `app/services/author_hash.py::ensure_author_hash()` es el guard canónico — si ya es hash lo deja, si es PII cruda hashea `sha256(platform:value:salt)` (salt `COMMENT_AUTHOR_SALT`, mismo esquema que apify_fb_deep). Determinista → mismo nombre = mismo hash en ambas tablas. Backfill aplicó a las 257 filas. Guard agregado en `ingest_radar_comments(_v2)`. NO merge automático con hashes basados en author_id (distinto input) — eso queda como dedup cross-source futuro.

---

## 2026-05-26 noche — D-LISTENERS-WORKER · event listeners en uvicorn Y Celery worker

**Contexto:** los SQLAlchemy event listeners (`audit_listeners`, `engagement_listeners`) solo se registraban en el lifespan de uvicorn. Los scrapers + ops de BD corren en el **Celery worker** (proceso aparte) → engagement_rate no se calculaba y ops destructivas no se auditaban (gap LFPDPPP art.32).

**Decisión:** registrar ambos en `worker_process_init` (`celery_app.py`) además de `main.py`. En contexto Celery el audit queda `user_id=NULL` ("operación de sistema") — seguro, inserts en try/except. El worker NO auto-recarga → requiere `docker restart crece-celery-worker`.

---

## 2026-05-26 noche — D-B12-CORO-CALIBRACION · contenido distintivo mínimo

**Contexto:** B12 "coro_cluster" (Jaccard ≥0.8) marcaba como coordinación a autores con texto idéntico. Investigación (Gemini priorizó dup-vs-coordinación): eran **elogios genéricos** ("Excelente", "Felicidades", "Saludos amiga" — 429 autores en 202 grupos), NO coordinación ni dup de BD.

**Decisión:** `MIN_SHINGLES_CORO=6` — un autor solo entra a coro si su corpus tiene ≥6 shingles distintivos. Excluye elogio genérico corto, mantiene mensajes largos repetidos (coordinación real plausible). Saymi 8→4 flagged. **Calibración de B12/B15 cerrada; calibraciones menores B08/B09 quedan opcionales.**

**Triage F1 (verdicto):** las 10 cards no-revisadas (B01/02/04/05/06/08/09/10/16/17) NO tienen errores críticos — contraste con las 8 revisadas visualmente que sí. B05 ya tenía mapa español (D-EKMAN-1). Solo B08 (gap_alert ruidoso) y B09 (viral números chicos) tienen calibración menor pendiente, no cliente-facing.

---

## 2026-05-26 — D-ER-CANONICO · engagement_rate centralizado + calculado en todas las rutas de ingest

**Contexto:** `social_posts.engagement_rate` tiene `default=0.0`. Las rutas de ingest (scrapers ORM, RADAR ingest SQL, Apify) no lo calculaban → 35% de posts globales en 0 pese a interacción real. Rompía B03 (matriz 2×2 colapsaba), degradaba B07/B15.

**Decisión:**
- Fórmula CANÓNICA única en `app/services/engagement.py`: con views (TikTok/YT/Reels) `(likes+comments)/views*100`; sin views (X/FB) `(likes+comments+shares)/followers*100`. Verificada por reverse-engineering + `bot_detection.py`. NO inventa datos (deriva de métricas reales). followers actuales = aproximación aceptada (no persistimos followers_at_post_time).
- Event listener `before_insert`/`before_update` en SocialPost (`app/core/engagement_listeners.py`) registrado en uvicorn (lifespan) **Y** Celery worker (`worker_process_init`). **Crítico:** los scrapers corren en el worker, no en uvicorn.
- Scripts SQL crudo + backfill importan el helper (una sola fuente de verdad).
- Backfill global aplicado: 1973 posts de todos los clientes.

**Gap señalado (no resuelto):** `audit_listeners` tiene el mismo patrón pero solo en uvicorn, no en worker → ops destructivas en tasks Celery sin auditar (LFPDPPP). Fix aparte.

---

## 2026-05-26 — D-CARDS-CALIBRACION-DATOS-REALES · validar corrección semántica por-card

**Contexto:** Review visual CEO descubrió que B18/B07/B14/B15/B03 daban resultados falsos (diputado→puta, +0 estancado, 0.966 desvío, 1-comentario-rage, 254 éxitos). Patrón común: las 18 cards Tier 2 se construyeron en lote con lógica placeholder (diccionarios, Jaccard léxico, snapshots copiados) y NUNCA se calibraron contra datos reales. Los audits midieron dimensiones (smoke/seguridad/perf) pero no la **corrección semántica** del número por-card.

**Decisión:** toda card de diagnóstico debe validarse contra datos reales del piloto (Saymi) antes de considerarse cliente-ready. El "compila + renderiza + pasa smoke" NO basta. Regla reforzada: probar contra datos reales (ya en CLAUDE.md, violada en fase scaffold).

---

## 2026-05-26 — D-B14-COMPOSICION · Topic Drift → composición de conversación

**Decisión:** B14 abandona el drift léxico bigram-Jaccard (saturado ~1.0) y mide **composición** de a qué responde la audiencia vía `nlp_target` (persona/tema/otro) + `topics_extracted` para nombrar temas. Se conserva el heatmap (CEO lo pidió explícitamente), recoloreado por foco dominante. Vista de composición elegida sobre score recalibrado.

---

## 2026-05-26 — D-B07-HONESTO-RADAR · B07 estado honesto, dato real vía RADAR

**Decisión:** B07 muestra "Medición de crecimiento en proceso de integración" en vez de "+0 Estancado" falso (D-ANTI-MOCK-1). Adapter FE↔BE wired (delta_followers/top_posts) — se emite solo con variación REAL entre snapshots. El dato real de followers histórico lo provee **RADAR (Hugo, peer)**: RADAR persiste timeseries, CRECE ingiere a `social_profile_snapshots`. Contrato acordado, pendiente ejecución Hugo.

---

## 2026-05-26 — D-B15-VOLUMEN · hostilidad exige volumen real

**Decisión:** B15 (rage/hostilidad) exige ≥5 comentarios en el post **y** ≥3 negativos reales para flag (antes 1 comentario negativo + ER spike disparaba falso positivo). Muestra evidencia inline (comentarios que dispararon). Esto además surfacea las críticas legítimas que B18-violencia correctamente ignora.

---

## 2026-05-26 — D-PALABRAS-CONFIG · diccionarios de moderación configurables por admin (PLAN)

**Decisión (CEO):** mover los diccionarios hardcoded (hate/vpg/amenazas/rage) a tabla configurable por admin con categoría + severidad + **scope** (exacta/raíz/contiene). Default scope=exacta + botón "Probar" para no reabrir el bug del "diputado". Plan escrito en `.context/PLAN-2026-05-26-palabras-moderacion-config.md`. Sprint siguiente. Supersede el parche manual de gaps de género del diccionario B18.

---

## 2026-05-19 tarde — D-BUG-CONTROL-CHARS-POST-PILOTO · Bug `/planes/{id}` JSON queda diferido

**Contexto:** Plan deuda tests v2 incluyó concern Gemini (HIGH severity) sobre bug control chars en endpoint `/api/v1/planes/{id}`. Hipótesis Gemini: si cliente abre plan individual durante demo, axios podría fallar parseando JSON con `\n` raw en strings (output LLM sin escapar). Concerns absorbido en plan v2 moviendo verificación a Bloque A pre-piloto.

**Verificación empírica 2026-05-19 (Bloque A smoke):** Playwright headless navegó a `/dashboard/planes/52` (caso real con prompt y contenido LLM). Resultado: render OK · 5 tareas visibles · sin error visible · sin console error de parsing. Axios tolera los control chars `\n` no escapados.

**Decisión:** bug confirmado existe (jq + python json.loads strict siguen fallando), pero NO afecta UI cliente. Fix mantenido en Bloque B post-piloto (plan deuda tests v2). Prioridad baja.

**Fix pendiente cuando se ejecute Bloque B:**
- Backend: sanitize `prompt_usado` y `contenido` con `.replace("\n", " ")` o usar serializer que escape control chars correctamente.
- Test acompañante: `tests/api/v1/test_planes_endpoint.py::test_get_plan_id_emits_valid_strict_json`.

**Anti-patrón evitado:** fix urgente HOY de un bug que NO afecta cliente · regla "Calidad > Tiempo pero no fix lo que no rompe pre-demo".

---

## 2026-05-19 — D-MISAEL-VIP-40 · Override Misael Fan #1 en 40 reactions / 12 comments

**Contexto:** El plan `PLAN-2026-05-17-fans-dashboard.md` línea 81 documentó "~80 reactions / 12 comments" como estimación sin base empírica. La sesión del 2026-05-18 codificó literal `reactions: 80` en `frontend/src/lib/api/utils/vip-overrides.ts`. CEO clarificó 2026-05-19 que el acuerdo verbal previo fue **40 reactions**, no 80, y la decisión nunca quedó persistida (regla `feedback_persist_peer_decisions` violada).

**Decisión:** `reactions: 40, comments: 12` para Misael Gómez (cliente_seed Saymi · `misael.gomez.981351`). NO regresar a 80.

**Justificación matemática (verificada empíricamente 2026-05-19):**
- BD tiene 295 posts Saymi FB pero solo **42 con reactions capturadas** (cobertura RADAR Hugo · postmortem S-8.1).
- Reactions reales de Misael en BD: **10**.
- Top cliente_seed real: Mueller Ramírez con 34 reactions.
- Top fan auto_suggested: Pedro Carlock con 36 reactions.
- **40 reactions = apenas por encima de Mueller (defendible como "Fan #1 cliente_seed") + dentro del límite matemático de 42 posts con reactions.**
- 80 era **imposible** matemáticamente (un usuario solo puede reaccionar 1 vez por post · max real = 42).

**Anti-patrón a evitar:** copiar números del plan v3 a código sin validar contra BD. Plan v3 puso "~80" como estimación pre-empírica; cuando se implementó, había que verificar contra la BD real. Esa verificación faltó.

**Persistencia:** comentario inline en `vip-overrides.ts:38-43` redirige a esta decisión. Cualquier agente futuro que vea el override debe leer este D-MISAEL-VIP-40 antes de tocar el número.

---

## 2026-05-15 noche — D-PLAN-IA-CC-GEMINI-CLI-1 · Generador plan_ia pausado, migración a CC+Gemini CLI

**Origen:** auditoría B3 (CRIT-PLAN-IA). CEO corrigió mi diagnóstico inicial: "El binario es CC (Claude Code, tú) y Gemini CLI, Ollama está off hasta que no mejoremos el VPS o lo corramos programado en la madrugada. No hay API de ningún tipo."

**Estado real descubierto:**
- `backend/app/services/plan_generator.py` con `_generate_claude` (Anthropic SDK) es **dead code** — ningún endpoint activo lo invoca.
- `backend/app/services/plan_ia/llm_pipeline.py` (el pipeline real, encolado por Celery `plan_ia_generate_async`) llama Ollama remoto `http://163.245.208.96:11434` (VPS Coolify) modelo `gemma3:12b` — Ollama declarado OFF por CEO.
- Decisión arquitectural CEO: **subprocess Claude Code CLI (`/Users/marxchavez/.local/bin/claude`) + Gemini CLI wrapper (`~/.claude/bin/gemini-clean`)** — ZERO API.
- Histórico planes_ia en BD muestra 9 modelos distintos, incluyendo `claude-opus-4.6+gemini-2.5-pro` (3 planes) generados MANUALMENTE por CEO fuera del sistema (validación del patrón deseado).

**Decisión:** Pausar endpoint sin borrar código. Endpoint `POST /api/v1/plan-ia/generate/{dirigente_id}` retorna HTTP 503 con mensaje explicativo. `plan_generator.py` mantiene código con header `# DEAD MODULE` documentando refactor pendiente. Frontend `/dashboard/planes` botón "Generar Plan" disabled con tooltip "Feature pausada · refactor a Claude Code + Gemini CLI pendiente".

**Refactor pendiente (sprint propio):**
- Reemplazar `_call_ollama` en `llm_pipeline.py` con `_call_cc_subprocess` (default) + `_call_gemini_cli_subprocess` (fallback)
- Mantener `_call_ollama` como tercer fallback dormant (VPS futuro)
- Tests E2E del pipeline con subprocess

**Out of scope para esta pausa:** generador de reels (feature nueva con Groq tier gratuito — ver D-REELS-GROQ-1 siguiente).

## 2026-05-15 — D-AUDIT-MULTI · Multi-tenant scope helper extraído + audit-driven hotfix

**Regla:** El patrón `assert_dirigente_access` que cierra leaks multi-tenant vive en módulo compartido `backend/app/core/scope.py`. TODO endpoint nuevo que acepte `dirigente_id` (path o query) DEBE importarlo. No duplicar helpers locales en archivos individuales (legacy de `watched_profiles.py` y `competitors.py` queda funcional pero futuras refactorizaciones consolidan).

**Patrón validado:**
```python
from app.core.scope import assert_dirigente_access

async def my_endpoint(dirigente_id: int, ..., current_user: ...):
    await assert_dirigente_access(db, current_user, dirigente_id)
    # ... resto del handler
```

**Endpoints corregidos en hotfix `0f232ea` 2026-05-15:**
- `/dirigentes/{id}/diagnostico`, `/dirigentes/{id}/social-summary`
- `/bot-detection/analyze/{id}`
- `/eventos/by-dirigente/{id}`, `/eventos/?dirigente_id=N` (scope por org en listing)
- `/social/sentiment-timeline?dirigente_id=N`, `/social/sentiment-coverage?dirigente_id=N`

**Validación obligatoria post-fix:**
- 1 curl `tenant_A` → endpoint(dirigente_de_B) MUST 403.
- 1 curl `admin` → endpoint(any) MUST 200 (bypass).
- 1 curl `user` → endpoint(own_dirigente) MUST 200 (no regresión).

**Audit driver:** 6 horas en 1 sesión con 3 agentes paralelos (security-engineer, quality-engineer, performance-engineer) + cross-audit Gemini. Reportes en `.context/AUDIT-*-2026-05-15.md`. Veredicto Gemini: **PROCEDER** con piloto.

**Origen:** CEO reporte 2026-05-15 02:00 "ya hicimos audits UX/UI, faltan info/estructura/lógica". 19 findings totales, 9 cerrados en sesión, 10 diferidos a sprints S/I/P.

---

## 2026-05-15 — D-ENCUESTAS-CLIMA · Selector ámbito en comparativa

**Regla:** La vista `/dashboard/social/clima` (módulo "encuestas" de clima político) tiene 877+ series potenciales (Federal + 59 Gobernadores + 715 Alcaldes + Promedios). La vista "Comparar" NO debe renderizar todas por default (overlap visual ininteligible).

**Default obligatorio:** `Federal + Gobernadores` (~65 series). Opciones explícitas:
- `+ Top 10 alcaldes` (por aprobación actual) — ~75 series
- `Todos` — con warning visual cuando >30

**Schema BD:** `encuestas_publicas.municipio` (VARCHAR nullable) existe con datos para 87% de alcaldes (12876/14860). El endpoint `/social/clima-politico` DEBE retornarlo. Frontend renderiza `"{municipio}, {entidad}"` para `actor_tipo='alcalde'`, `"{entidad}"` para gobernadores.

**Key dedup obligatorio:** Para alcaldes (homonimia política existe), la clave de serie es `(actor_nombre, ambito, municipio)`. Para resto: `(actor_nombre, ambito)`.

**Origen:** CEO reporte 2026-05-15 "en las encuestas, faltan los nombres de los municipios o alcaldías cuando se seleccionan y tambien vi que cuando se comparan todas se amontonan". Fix `15b4e39`.

---

## 2026-05-15 — D-COMP-METRICS-W2 · Stack scraper light competidores (FB primario)

**Regla:** Para enriquecer `competitor_metrics_monthly` con followers/posts de competitor_profiles, usar este orden de fallback:

1. **Scrapers nativos** (`backend/app/scrapers/{platform}.py` via `scrape_competitors_light.py`): IG, X/Twitter, TikTok, YouTube. FB nativo NO funciona (curl-cffi sin patrones, Selenium fail en Docker).
2. **Apify INICIAL** (`apify/facebook-pages-scraper` via `scrape_competitors_light_apify.py`): SOLO Facebook. Costo cubierto por free tier mensual ($5/mes). Cap budget run obligatorio (default $0.15). Pre-flight `_apify_usage()` check; abort si MTD ≥ $4.95.

**Comando canónico:**
```bash
docker exec -e APIFY_TOKEN=<token> crece-backend python scripts/scrape_competitors_light_apify.py --dirigente-id <id> --budget 0.10
```

**UPSERT idempotente:** `ON CONFLICT (competitor_id, month_start) DO UPDATE` con month_start = primer día del mes UTC. Reruns en el mismo mes refrescan métricas sin duplicar.

**Dedupe de URLs:** Si un competitor está en FB + IG (mismo display_name, distintas plataformas), el scraper FB solo recibe handles únicos FB. NO procesar IG con actor de FB.

**Validación post-run:** verificar via `SELECT cp.display_name, cmm.followers_total FROM competitor_profiles cp JOIN competitor_metrics_monthly cmm ON cmm.competitor_id=cp.id WHERE cp.dirigente_objetivo_id=<id>`.

**Origen:** Sprint W2 war-room-personal 2026-05-15. Saymi (id=3) enriquecida con Susana Harp 62,895 + Ivette Morán 244,303. Costo run $0.00 (Apify free tier).

---

## 2026-05-14 — D-SEC-WATCHED-SCOPE-1 · Multi-tenant scope obligatorio en watched_profiles

**Regla:** Todo endpoint que opere sobre `watched_profiles` (GET/PATCH/DELETE, incluyendo `summary`, `suggestions`, `engagement`) DEBE validar el org del user antes de ejecutar query. Sin excepciones.

**Helpers canónicos** (en `backend/app/api/v1/endpoints/watched_profiles.py`):
- `_assert_dirigente_access(db, user, dirigente_id) -> org_id`: resuelve dirigente → org → `_check_org`. Retorna org_id o lanza 404/403.
- `_assert_watched_access(db, user, watched_id) -> (author_hash, dirigente_observador_id)`: para endpoints que reciben watched_id en path.

**Comportamiento default sin `dirigente_id`:**
- `admin` → ve todo (sin filtro).
- Resto de roles → filtrar `wp.org_id = user.org_id`. NO devolver dataset global.

**Origen:** Captura del CEO 2026-05-14 mostrando dirigente Cravioto logueado pero datos Saymi visibles. Root cause: GET endpoints aceptaban `dirigente_id` query param sin validación de org. POST sí lo validaba (precedente correcto). Fix consolidado en sprint 1 del PLAN-2026-05-14-fix-fantasmas-observados.md.

**Test E2E que debe pasar siempre:**
```bash
TOK_A=$(login user_org_A); TOK_B=$(login user_org_B)
curl -H "Bearer $TOK_A" "$API/aceptacion/watched-profiles/?dirigente_id=<dirigente_de_B>" → 403
```

**Aplicabilidad fuera de watched_profiles:** este patrón debe revisarse en cualquier endpoint que acepte `dirigente_id` como query param. Sospechosos: aceptación, social, benchmarks, planes_ia. Auditoría sistemática pendiente.

---

## 2026-05-14 — D-OPS-COSTO-PRUEBAS-1 · Disciplina de gasto en APIs de pago

**Regla:** El costo de un test/prueba contra una API de pago (Apify, Brightdata, ScrapingBee, etc.) NUNCA debe ser cercano o mayor al costo de la extracción real. Heurística: **test ≤ 15-20% de la extracción esperada**.

**Origen:** CEO 2026-05-14 cuestionó: *"no es posible que gastemos más en pruebas que en extracción"*. Validó tras descubrir que mi reporte de costo del SDK Apify (`usageTotalUsd` $0.825) era inferior al cobro real del API ($1.625), inflando aparentemente el % de tests.

**Aplicación obligatoria:**
1. Antes de correr un test pagado, calcular `test_cost / expected_extraction_cost`. Si > 30%, replantear: bajar cap del test, hacer test sobre 1 unidad mínima, o saltarlo e ir directo.
2. **Confiar en API/billing del proveedor, NO en log del script.** Validar con `GET /v2/actor-runs?desc=1` (Apify) o equivalente. SDK reporta pre-finalización; cobro definitivo viene minutos después.
3. Reportes de gasto al CEO siempre con número del API, con desglose test/extracción.
4. Múltiples tests grandes son anti-patrón. Si necesitas iterar, una unidad mínima por iteración.

**Caso de origen:** sesión 2026-05-14 watchlist Saymi FB.
- Test reactions cap=5 (1 post): $0.225
- Extracción real (5 posts cap=20): $1.625 (real API) vs $0.825 (SDK log)
- Ratio real: 13.8% (dentro de regla). Bug: confiar en log → reporte erróneo al CEO → CEO detectó la inconsistencia.

---

## 2026-05-13 — D-FOLLOWERS-1 · Modelo granular `social_followers` + `follower_engagement`

### Contexto
Los dirigentes piden ver nombres de sus seguidores + si comentaron o no. `SocialProfile.followers_count` es agregado, no lista. PLAN-2026-05-13-followers-oauth-pipeline.md S1.

### Decisión
- Nueva tabla `social_followers` (ADD-ONLY · low-risk migration B-23-01) con UNIQUE `(dirigente_id, platform, follower_external_id)` para UPSERT idempotente.
- Nueva tabla `follower_engagement` con UNIQUE `(follower_id, post_id, engagement_type, comment_id)` para engagement granular sin duplicados.
- Columna `source` con CHECK constraint `('oauth','scraper_auth','public_scraper')` para trazabilidad.
- Columnas `is_real bool default true` y `bot_score float null` reservadas — hook a `bot_detection.py` diferido (B-FOLLOWERS-BOT-1).
- FK `follower_engagement.comment_id → social_comments.id` declarado solo a nivel DB (migración) porque `social_comments` no tiene modelo SQLAlchemy en `Base.metadata`. La constraint sigue siendo aplicada por Postgres.

### Archivos tocados
- `backend/app/models/follower.py` (nuevo)
- `backend/app/models/__init__.py` (re-export)
- `backend/migrations/versions/fol1_social_followers.py` (nuevo, off `spm_media1`)
- `backend/app/api/v1/endpoints/followers.py` (nuevo, endpoint paginado scoped)
- `backend/app/api/v1/__init__.py` (router include)

---

## 2026-05-13 — D-OAUTH-YT-1 · OAuth YouTube primero (sin Meta App Review)

### Contexto
PLAN-2026-05-13 Q1: ¿empezar con OAuth real YouTube o esperar Meta? YouTube no requiere App Review (sólo Google Cloud Console por CEO). Meta queda gateado 4-6 semanas. CEO dio luz verde autónoma · default plan adoptado.

### Decisión
- Implementar `youtube_oauth_real.py` con flujo OAuth 2.0 estándar (auth code + refresh) usando httpx directo (sin google-api-python-client → dependencia mínima).
- Service permanece **detrás de toggle `OAUTH_YOUTUBE_ENABLED=false`** mientras CEO no haya entregado `GOOGLE_OAUTH_CLIENT_ID` + `_SECRET` (B-OAUTH-YT-GCP-1).
- El stub service existente (`oauth_service.py`) sigue siendo el path por default — la coexistencia evita romper el comportamiento actual.
- Tokens guardados en `OAuthTokenByPlatform.token_hash` / `refresh_token_hash` **en claro** hasta integrar pgcrypto (B-OAUTH-YT-CRYPTO-1).
- Scraper privilegiado `YouTubePrivilegedScraper` rechaza tokens con `is_stub=True` (anti-falso-positivo en producción).

### Reversible
Sí · toggle off + revertir scaffold sin tocar BD. Cero filas con `is_stub=False` hoy.

---

## 2026-05-13 — D-AUDIT-PIPELINE-1 · Pipeline `audit_data_quality.py` 4 capas

### Contexto
PLAN-2026-05-13 S5: dejar de descubrir huecos de BD usando la app. Necesitamos detección sistemática **pre-uso**.

### Decisión
- Script `backend/scripts/audit_data_quality.py` con 4 capas independientes:
  1. **coverage** — NULLs %, top valores, distinct count por tabla.
  2. **referential** — FK huérfanas (6 queries dedicadas).
  3. **api-contract** — parsea `api.<method>(...)` en `frontend/src/lib/api/hooks/*.ts` y cross-referencia contra `app.api.v1.api_router`.
  4. (slot reservado para PII / LFPDPPP en próxima iteración).
- Outputs `.md` (humano) + `.json` (CI) en `.context/audits/data-quality-YYYY-MM-DD.md`.
- Severidad 5-tier (info/low/medium/high/critical). Exit codes 0/1/2 para CI gates.
- Flags `--subset` (rápido, tablas core), `--layer X`, `--frontend-dir` (override para correr desde container sin frontend montado), `--output-dir`.

### Validación
Primera corrida 2026-05-13: 433 findings totales. 5 críticos: `/onboarding/{id}/profile` y 4 más donde FE llama path que BE no expone (→ NUEVO B-ONBOARDING-FE-BE-MISMATCH-1). 0 FKs rotas. 110 columnas HIGH NULL >50% (mayoría son features futuras planificadas).

### Próxima iteración
- Wire al pre-commit hook (`--subset`).
- Cron Celery beat nightly (`--full`).
- Capa 4: PII residual (campos que deberían estar cifrados pero no lo están).

---

## 2026-05-12 — D-COOLIFY-DOCTRINE-V2-1 · Vercel staging · Coolify demo final

### Contexto
La memoria `reference_coolify_alive_2026_05_11.md` (rev. 2026-05-11) declaró: "Coolify = demo · Vercel = piloto operativo · roles distintos NO duplicación". El CEO clarificó 2026-05-12 que el modelo real es:
- Vercel = **staging / demo-prueba** (validación de features ANTES de promover)
- Coolify = **demo final** (lo que se muestra a stakeholders post-validación)
- Mac Mini :8002 backend único, expuesto via cloudflared (Vercel) y vía VPS (Coolify)

### Decisión
1. Toda nueva feature se valida primero en Vercel (cherry-pick desde commit estable).
2. Una vez validada, se pinguea a Carlos Amador para deploy a Coolify desde branch + commit estable.
3. Coolify tiene su propia BD en VPS (no comparte estado con Mac Mini).
4. NUNCA usar Coolify como fallback del piloto Vercel.

### Anti-patrón
Pensar "Coolify se apaga" o "Coolify es residual". Es un environment activo con rol diferenciado.

---

## 2026-05-12 — D-HUMANIZ-NEUTRO-1 · Posts sin marcador no penalizan B10

### Contexto
Card B10 (Tu toque humano) penalizaba posts "sin ninguna señal" (sin 1ra persona, sin emoji, sin keyword personal, sin keyword institucional) como score=0 e implícitamente "Institucional". Esos posts son realmente neutros (anuncios cortos, frases poéticas, descripciones). 241 de 411 posts de Jiménez (58%) caían en esta categoría, arrastrando el score injustamente.

### Decisión
1. Backend `humanizacion_service.py`: posts sin marcador detectable se cuentan como `n_posts_sin_marcador` aparte, NO entran al cálculo del score.
2. Denominador del score es `n_posts_con_marcador`, no el total.
3. Frontend B10 card muestra "X analizados / Y sin marcador" cuando hay neutros, para transparencia.
4. Resultado: Jiménez sube de 44.83 a 58.68 (sigue "Equilibrado" pero ahora honesto).

### Caveats
- Conceptualmente la categoría "Institucional" del thresholdar ahora requiere posts con marcador institucional, no la ausencia de marcadores positivos.

### Archivos tocados
- `backend/app/services/diagnostico/humanizacion_service.py:160-194`
- `frontend/src/components/diagnostico/cards.tsx:675-718`

---

## 2026-05-12 — D-PEPE-MONROY-1 · Cliente independiente PAZ onboard

### Contexto
Pepe Monroy ("Líder Nacional de Partidos Políticos Locales") es el primer cliente INDEPENDIENTE de CRECE, distinto del piloto MC CDMX. Proyecto: PAZ. Alcance: municipios pequeños a nivel nacional. Plataformas: solo Instagram (@pepemonroyma, 16K seguidores, 171 posts) + Facebook (PepeMonroyM, 10.9K likes).

### Decisión
1. **Org nueva** `Proyecto PAZ` (id=4) con tipo=ONG (no es partido formal).
2. **Dirigente** Pepe Monroy (id=57) cargo "Líder Nacional de Partidos Políticos Locales", partido=PAZ, estado=Nacional.
3. **User VIEWER** `pmonroy@paz.mx` password `demo2026!` con dirigente_id=57, org_id=4.
4. **Social profiles** IG + FB creados con followers iniciales del OG metadata.
5. **Sync inicial:** IG vía instaloader/ensta (fallido en posts, OK en metadata followers/posts_count). FB scraper falló por chromedriver roto → datos iniciales del OG.

### Caveats
- Posts de IG y FB no se capturaron en el sync inicial (B-FB-SCRAPER-1, B-IG-SCRAPER-1 documentados).
- Cards B01-B10 de Pepe muestran `insufficient_data` honesto hasta que los scrapers se reparen.
- Doctrine D-COOLIFY-DOCTRINE-V2-1: Pepe entra a Vercel staging primero, luego Carlos lo deploya a Coolify demo.

### Archivos tocados
- BD: `organizaciones`, `dirigentes`, `users`, `social_profiles` (4 inserts directos via SQL).

---

## 2026-05-12 — D-CALENDARIO-1 · Catálogo efemérides + generación post LLM

### Contexto
CEO entregó calendario completo de fechas conmemorativas mexicanas 2026 (70 fechas + ideas políticas + viralidad). Necesidad: aplicar a todos los dirigentes (Solano/Piña/Pineda/Nolasco/Jiménez/Cravioto/Ballesteros + Pepe Monroy), con generación de drafts de post adaptados al tono de cada uno.

### Decisión
1. **Modelo `Efemeride`** con `mes INT + dia INT` (recurrencia anual, NO Date). Campos: titulo, tipo (cívica/internacional/social/emocional/familiar/comunidad), descripcion, ideas_politicas jsonb, viralidad (alta/media/baja), ambito (nacional/internacional/regional).
2. **Seed 70 fechas** del calendario CEO (script `backend/scripts/seed_efemerides.py`).
3. **Endpoint `GET /calendario/proximas?days=30`** scoped por JWT, devuelve fechas + dias_hasta + fecha_proxima calculados.
4. **Endpoint `POST /calendario/sugerir-post`** body={efemeride_id, dirigente_id, plataforma}. Prompt LLM inyecta:
   - Efeméride: título, tipo, ámbito, ideas políticas
   - Dirigente: nombre, cargo, partido, estado
   - Plataforma: límite chars, emoji ok, estilo
   - Reglas: NO inventar datos, tono cálido, no placeholders
5. **Fallback gracioso:** si `CLAUDE_API_KEY` está vacía, devuelve plantilla genérica con campo `fuente: plantilla_fallback` + `aviso` explicativo. Cuando se configure la key, opera con Claude real sin más cambios.
6. **Frontend:** card `EfemeridesProximasCard` (lista + popover ideas + botón Post) + modal `SugerirPostModal` (selector plataforma, editor, counter chars, copy). Nueva ruta `/dashboard/calendario`.
7. **NO se integra a `planes_ia` automáticamente** (deferido como B-CALENDARIO-PLANES-IA-1 para próxima sesión).

### Verificación E2E
Día del Maestro 15-may aparece como próxima (en 3 días, viralidad alta). Drafts generados para Jiménez (Diputada Federal) y Pepe Monroy (Líder Nacional de Partidos Políticos Locales) son distintos en cargo y ámbito.

### Archivos tocados
- `backend/app/models/efemeride.py` (nuevo)
- `backend/app/models/__init__.py`
- `backend/app/api/v1/endpoints/calendario.py` (nuevo, 260 líneas)
- `backend/app/api/v1/__init__.py`
- `backend/migrations/versions/efm1_efemerides.py` (nuevo)
- `backend/scripts/seed_efemerides.py` (nuevo)
- `frontend/src/lib/api/hooks/use-calendario.ts` (nuevo)
- `frontend/src/components/calendario/efemerides-proximas-card.tsx` (nuevo)
- `frontend/src/components/calendario/sugerir-post-modal.tsx` (nuevo)
- `frontend/src/app/dashboard/calendario/page.tsx` (nuevo)

---

## 2026-05-12 — D-BENCHMARK-CROSS-ORG-1 · Rivales declarados cargan sin RLS

### Contexto
Card B04 mostraba a Ballesteros (org_id=1) como `status: no_encontrado` cuando Jiménez (org_id=3) lo declaraba en `competidor_directo_ids=[8,7]`. Causa: `load_dirigente_scoped(db, rid, org_id)` aplicaba RLS por org_id sobre los rivales, bloqueando referencias cross-org legítimas.

### Decisión
Para los rivales declarados explícitamente por el dirigente en `competidor_directo_ids`, cargar el `Dirigente` referencia **sin scoping por org_id** (`load_dirigente_scoped(db, rid, None)`). El self sigue scopeado.

### Justificación
- Los rivales declarados son referencias informativas (nombre, métricas agregadas públicas), no acceso a data sensible interna de su org.
- Una organización política en CDMX (MORENA) puede legítimamente declarar como rival a una de MC sin estar en la misma org del SaaS.
- El blast radius se limita a lo que `_stats_dirigente` expone (followers públicos, posts conteo, ER promedio, sentiment_avg) — nunca campos privados del rival.

### Archivos tocados
- `backend/app/services/diagnostico/benchmark_service.py:146-152`

---

## 2026-05-12 — D-ER-SCALE-1 · Engagement rate en escala % (0-100)

### Contexto
Card B04 mostraba `er_avg_pct = 384.45%` para Piña (imposible) y `0.0%` para Jiménez. Investigación reveló:
- 119 posts de Jiménez en 28d tenían `engagement_rate=0.0` en BD (pipeline de cálculo nunca corrió sobre ellos).
- `benchmark_service.py:91` multiplicaba `mean(er_values) * 100.0`, asumiendo que el campo venía en fracción (0-1).
- Algunos scrapers escriben en escala fracción (0-1), otros en escala % (0-100) → heterogeneidad histórica.

### Decisión
1. **Convención unificada:** `social_posts.engagement_rate` se interpreta como **escala % (0-100)** desde 2026-05-12. Fórmula: `(likes + comments + shares) * 100 / followers`.
2. **Recálculo puntual:** SQL UPDATE re-pobló los 713 posts en 28d que tenían `er=0` aplicando la fórmula consistente.
3. **Backend:** `benchmark_service.py:91` ya NO multiplica × 100 — solo `mean(er_values)`.

### Justificación
- Sin convención unificada el card B04 muestra valores absurdos (384%) o ceros engañosos.
- Recálculo de 713 posts es conservador (solo afecta ventana de cómputo activa del card).

### Caveats / blocker derivado
- **B-ER-SCALE-1** (BLOCKERS.md): Twitter histórico (posts > 28d, no tocados por el recálculo) algunos están en escala fracción. Resultado: ER de Twitter pre-piloto queda subestimado ×100 en cards que miran ventanas largas. Fix completo requiere normalización full-DB + identificar scrapers que escriben en fracción.
- Los scrapers nuevos deben escribir en % siguiendo la fórmula declarada.

### Archivos tocados
- `backend/app/services/diagnostico/benchmark_service.py:88-97`
- Data: 713 rows `social_posts` actualizadas con SQL UPDATE.

---

## 2026-05-12 — D-EKMAN-1 · Sentimiento en Ekman-6 (no Plutchik mixto)

### Contexto
Card B05 mostraba radar vacío + tag rojo "HOSTILIDAD" para Jiménez pese a tener 1274 posts con sentiment (93% coverage). 3 capas desalineadas:
- NLP (`pysentimiento`) emite **Ekman-7**: `joy/fear/anger/disgust/sadness/surprise/others`.
- Backend B05 pedía **Plutchik mixto**: `trust/anger/joy/fear/sadness/disgust` (`trust` nunca se emite → siempre 0).
- Frontend B05 pedía **Plutchik clásico**: `trust/joy/anticipation/anger/sadness/fear` (3 keys que el backend no devolvía).
- `ratio_trust_anger` siempre era `0/anger = 0` → señal "Hostilidad" falsa.

### Decisión
1. **Backend** `sentiment_plutchik_service.py`: `EKMAN_6 = ["joy","anger","sadness","fear","disgust","surprise"]` (alias `PLUTCHIK_6` retro-compat).
2. **Métrica nueva** `ratio_joy_anger` reemplaza `ratio_trust_anger`. Backend devuelve ambos como alias temporal.
3. **Frontend** alinea `PLUTCHIK_ORDER` y `EMOCION_ES` a Ekman-6 (añade Asco, Sorpresa; quita Confianza, Anticipación).
4. **Narrativa** card: "La **Alegría** supera al **Enojo** N a 1" (antes "Confianza supera al Enojo").
5. **Signal** "Gran Alegría" reemplaza "Gran Confianza".

### Justificación
- Modelo emocional usado por el NLP es la fuente de verdad. Pretender Plutchik cuando se computa Ekman es deshonesto y produce métricas siempre cero.
- Renombrar archivo `sentiment_plutchik_service.py` → `sentiment_ekman_service.py` queda diferido (blast radius mayor).

### Archivos tocados
- `backend/app/services/diagnostico/sentiment_plutchik_service.py:47-156`
- `frontend/src/components/diagnostico/cards.tsx:388-452`

---

## 2026-05-12 — D-HUMANIZ-NORM-1 · B10 escala normalizada a [0,100]

### Contexto
Card B10 mostraba "36 / 100" para Jiménez pese a tener 56% primera persona + 57% emojis (perfil claramente humano). Investigación: la fórmula
```
score = 100 * (0.30·p1 + 0.20·p2 + 0.30·p3 − 0.20·p4)
```
tiene **techo teórico 80** (cuando p1=p2=p3=1, p4=0). Mostrar `/100` mentía por construcción.

### Decisión
1. **Renormalizar** dividiendo por la suma de pesos positivos (0.80):
```
score = 100 * (0.30·p1 + 0.20·p2 + 0.30·p3 − 0.20·p4) / 0.80
```
Max teórico real = 100. Min teórico = -25, clamp a 0.

2. **Thresholds escalados proporcionalmente** (mantener fronteras semánticas):
| Categoría | Antes | Después |
|---|---|---|
| Humanizado | ≥60 | ≥75 |
| Equilibrado | ≥35 | ≥44 |
| Institucional | <35 | <44 |

3. Aplicado en ambas funciones (`_score_post` y `compute`).

### Justificación
- Si el cap teórico es 80, mostrar `/100` confunde al usuario. La normalización es matemáticamente honesta sin cambiar la importancia relativa de cada factor.
- Pesos relativos (3/2/3/-2) se preservan — solo se escala.

### Archivos tocados
- `backend/app/services/diagnostico/humanizacion_service.py:13-15, 92-100, 109, 174`

---

## 2026-05-11 — D-NARRATIVA-1 · Narrativa política · metodología en Configuración

### Contexto

CEO review 2026-05-11 sobre card B01 "Engagement vs. tu estrato": "los políticos no
entienden Zenovo ni Nano X · igual y todo eso debería ir en metodología". Aplicado al
diagnóstico Tier 1 completo (10 cards B01-B10).

Review /gemini propuso 3 enfoques (Semáforo / War Room / Termómetro). CEO ratificó
Opción 1 (semáforo) como base universal + Opción 2 (ranking) específica para B04 +
Opción 3 (alerta visual) solo para B06 crisis. Cross-audit /gemini plan del plan de
implementación: GO con 3 ajustes técnicos.

### Decisión

1. **Cards del diagnóstico hablan lenguaje político.** Cero jerga académica visible
   (Zenodo, Plutchik, Brookings, n=316, Sprout Social, Rival IQ, IM commercial, índice
   de difusión, spike anómalo, estrato técnico). Cada métrica se contextualiza contra
   el promedio político mexicano.

2. **Toda la metodología técnica vive en `/dashboard/sistema/metodologia`** (sidebar
   → Configuración → Metodología). 10 anchors `#b01-#b10` con descripción extendida
   por bloque.

3. **Link metodología via icono ℹ️ Popover** (Radix `@radix-ui/react-popover`), no
   link text al pie de cada card. Click/tap-friendly para iPad/móvil (Tooltip hover
   era inaccesible en touch). Decisión tomada tras cross-audit /gemini plan ("OBLIGATORIO
   click/tap, hover no existe en móvil").

4. **Signal warning donde hay esfuerzo desperdiciado o percepción problemática.**
   Hallazgo extra Gemini: B03 "Sin Eco" >50% ahora "Esfuerzo Sin Retorno" (warning,
   no neutral) · B10 score<40 ahora "Distante" (warning explícito, no "Institucional"
   ambiguo).

5. **Tips educativos** ("Usar primera persona y emojis aumenta este puntaje") **fuera
   de las cards**, a `metodologia#b10` con lista accionable. Dashboard ejecutivo
   reporta estado, no da tutoriales no solicitados (criterio Gemini ratificado).

### Cambios narrativos clave

- B01: ratio "veces más" en lugar de % técnico + "estrato Micro".
- B02: label cualitativo headline ("Creciendo") + nivel N/6 subtitle.
- B04: "competidores directos" en lugar de "analizados".
- B05: diccionario defensivo case-insensitive Joy→Alegría · Anticipation→Anticipación
  · Sadness→Tristeza · Fear→Miedo. Narrativa proporcional "Confianza supera al
  Enojo X a 1".
- B06: "Alerta: N comentarios negativos inusuales" en lugar de "pico anómalo".
- B07: lista posts muestra plataforma + fecha legible (no ID interno `#abc123`).
  Excerpt real del post diferido a backend.
- B08: "de toda la conversación" en lugar de "del total de menciones".
- B09: escala cualitativa "8/10 Poder Viral" en lugar de "0.8 índice de difusión".
- B10: "Tu audiencia te percibe como 'persona real'. Por encima del promedio
  institucional" + tip educativo movido a metodología.

### Trade-offs

- **Diferido a sprint posterior:** B03 matriz 2x2 "Lo que funciona / Lo que te daña"
  (vs scatter actual), B08 gauge (vs pie chart), B07 excerpt real del post
  (requiere `content_preview` en schema B07 backend). Son rediseños mayores, no
  cambios textuales. Documentados en `.context/PLAN-2026-05-11-diagnostico-narrativa-politica.md`.
- **Convención para excepciones legítimas en código:** si un componente de test o
  documentación necesita strings como "Joy" o "índice", marcar con comentario
  `/* allow-mock: razón */` (mismo patrón que D-ANTI-MOCK-1).

### Componentes auditados

| Archivo | Cambio |
|---|---|
| `frontend/src/components/diagnostico/cards.tsx` | 10 cards reescritas (textos + signals) |
| `frontend/src/components/diagnostico/card-shell.tsx` | Tooltip→Popover + link a metodología#code |
| `frontend/src/components/ui/popover.tsx` | Nuevo (shadcn-style Radix Popover) |
| `frontend/src/app/dashboard/sistema/metodologia/page.tsx` | 10 anchors B01-B10 + secciones extendidas |
| `frontend/package.json` | `@radix-ui/react-popover@^1.1.15` |

---

## 2026-05-11 — D-ANTI-MOCK-1 · Cero hardcoded fallback en UI · guardrail automatizado

### Contexto

CEO revisó dashboard en producción 2026-05-11 logueado como Ballesteros (VIEWER). Detectó:
- Card "Tu Audiencia" mostraba **89.8K** (suma real de followers por plataforma).
- Card "vs Competidor Principal → Laura Ballesteros" mostraba **8.8K** (mock hardcoded `DIRIGENTE_METRICS_FALLBACK` del componente `CompetitorSnapshotCard`).

Factor 10x de inconsistencia visible al cliente. Causa raíz: el componente tenía un comentario `// Will be replaced by /benchmark/comparison API call in a future sprint.` que nunca se ejecutó. La regla informal de CLAUDE.md "NUNCA mocks o datos inventados" no estaba validada programáticamente — solo dependía de revisión humana.

### Decisión

1. **Borrar** todo hardcoded fallback con números visibles al usuario. `CompetitorSnapshotCard` reescrita para usar `useKpiOverview()` (followers reales) + `useBenchmarkRanking()` (competidores reales filtrando followers=0).
2. **Skeleton** o estado vacío explícito si el endpoint aún no está listo. Cero números falsos.
3. **Guardrail automatizado:** `frontend/scripts/check-no-mocks.sh` detecta patrones `_FALLBACK = { ... followers: N ... }`, `DEMO_/MOCK_/FAKE_*[]`, y comentarios `TODO replace with API`. Comando: `npm run check:no-mocks`. Exit 1 = violaciones, exit 0 = limpio. Validado en ambos sentidos.
4. **Regla operativa** añadida a `CLAUDE.md` § Reglas de Calidad ítem 5.

### Componentes auditados en este sprint (limpios)

| Componente | Estado pre-sprint | Estado post-sprint |
|---|---|---|
| `CompetitorSnapshotCard` | mock 8.8K + Batres 285K + Taboada 142K | datos reales `total_audiencia` + `/benchmark/ranking` |
| Lint script | no existía | `scripts/check-no-mocks.sh` con 3 reglas |
| `package.json` | sin script de no-mocks | `npm run check:no-mocks` |

### Trade-offs

- **Trade-off aceptado:** el lint usa grep regex, no AST. Puede dar false positives en código legítimo (test fixtures). Mitigación: convención de marcar excepciones con `/* allow-mock: <razón> */` en la misma línea.
- **No hicimos AST-based check** porque exigiría agregar `ts-morph` u otra dep · grep es lo suficientemente preciso para los 3 patrones identificados y se ejecuta en <1s.
- **Endpoint `/benchmark/ranking` reusa el existente** en lugar de crear `/benchmark/comparison` nuevo — economiza alcance y entrega valor inmediato. Si en el futuro se necesita comparativa head-to-head con engagement/sentiment, ampliar entonces.

### Pendientes a futuro (P-04b)

- Scraper de profile metrics FB+TT no corre para 5 perfiles (Solano FB · Máynez FB+TT · Ballesteros FB+TT). UI mitigada en este sprint: muestra "Sin datos · sync pendiente" en lugar de "0" engañoso. Para datos reales, scraper Playwright debe correr con cookies válidas.
- Coverage clasificación sentiment muy bajo (Ballesteros 13.6%, Solano 20%, Piña 52.7%). UI mitigada con disclaimer "X de Y posts clasificados" en card Tono Discursivo. Para mejorar, correr re-clasificación batch.

---

## 2026-05-09 (tarde) — D-DIAG-01 · Claude+Gemini 2-way para regen diagnostico enriquecido · Gemma fuera del flujo

### Contexto

CEO pidió regenerar diagnostico con prompt enriquecido (FODA 8-10 ítems/cuadrante con evidencia numérica) para Ballesteros como pilot. Flujo original propuesto: 3-way Claude + Gemini CLI + Gemma vía Coolify VPS, integración manual.

**Bloqueo Gemma:** ejecución backgrounded del prompt de ~7K chars con `num_predict=8000` sobre Gemma3:12b CPU-only → `timed out` (>60 min sin respuesta). VPS Coolify no escala para outputs largos en ventana razonable.

Claude (yo, in-conversation) y Gemini CLI sí entregaron salidas en <3 min. Outputs comparables en estructura, complementarios en énfasis (Claude métricas, Gemini metáforas).

### Decisión

**Gemma sale del flujo de regen diagnostico.** Pipeline aprobado para Sprint 2-9 escalado al resto de dirigentes:

1. Yo (Claude in-conversation) genero análisis A con prompt enriquecido
2. Gemini CLI genera análisis B con mismo prompt
3. Yo integro A+B → diagnostico final, persisto a `planes_ia` con `modelo_ia='claude+gemini-2way-enriched-YYYY-MM-DD'`

Outputs archivados de pilot: `backend/scripts/_archive_3way/{claude,gemini}_ballesteros.md`.

### Reincorporación de Gemma — condiciones

Gemma puede reincorporarse al flujo si:
- Coolify VPS migra a GPU o tier mayor (CPU actual no alcanza >2K tokens)
- Se reduce `num_predict` a 4096 y se acepta diagnostico más conciso
- Se invoca asincronía batch con cola de reintentos (no bloqueo en línea)

Mientras tanto, decisión D-NLP-06 sigue vigente para HITL (Gemma como tiebreaker offline opcional, no en línea).

---

## 2026-05-09 (noche) — D-NLP-06 · Claude+Gemini 2-way como evaluador primario para sample HITL · Gemma diferido a tiebreaker offline

### Contexto

Pre-reunión 2026-05-10 con Solano + Piña + Ballesteros: editor HITL necesita los 20 posts más recientes de cada dirigente con una sugerencia AI lista para que el dirigente confirme o edite. Plan original era Gemma3:12b vía Coolify VPS sobre 60 posts random (20×3) y aplicar mapper v3.0.1.

Dos bloqueos descubiertos en ejecución:

1. **VPS Coolify sobrecargado:** test de generación pequeña (3 tokens) de Gemma timed out >60s. En el job `bl8oy3epb` 70%+ de las llamadas dieron `ReadTimeout 240s`. Modelo está corriendo CPU-only o GPU saturada — no viable en ventana pre-reunión.

2. **Bug R3 en mi script `classify_posts_gemma_coolify.py`:** seteé `is_self_authored=True` al llamar `map_runner_to_v2()` argumentando "post del propio dirigente". Pero R3/G2 del mapper hace early-return forzando `tono_v2=celebratorio, target_v2=autopromocion` SIN importar la salida de Gemma. Resultado: los posts que sí pasaron (5/20 en Piña primer batch) fueron mapeados todos a `celebratorio/autopromocion` — sample inútil. R3 está pensado para COMMENTS donde author == dirigente (autopromocion runtime), no para posts del propio dirigente cuyo tono real puede ser cualquiera.

### Decisión

**A. Para la reunión 2026-05-10:** evaluador primario es **Claude + Gemini CLI (consensus 2-way)** sobre los 20 posts más recientes de cada dirigente. Gemma queda **suspendido** del flujo en vivo.

- Sample = 60 posts más recientes (20 cronológicos × 3 dirigentes piloto). NO random — coincide exactamente con lo que el editor pulla en modo "Cronológico".
- Cada modelo emite tono v2 + target v2 + razón. Reglas consensus:
  - tono claude == tono gemini → `2/2` agreement
  - tono claude != tono gemini → tiebreaker = Claude (mejor matiz político MX en pruebas previas), agreement `1/2_claude`
  - mismo para target
- Aplicar via UPDATE social_posts SET tono_discurso, target_politico, nlp_model_version='claude+gemini-2way-recent-2026-05-09', clasificacion_origen='ai_suggested' WHERE id=:pid AND tono_discurso IS NULL.

**B. Gemma toda la noche en background sobre sample original (random 60 random_state=42), CSV-only** (script `triangulacion_posts_2026_05_09.py`, no toca BD). Mañana evaluamos:
- Si terminó y la calidad es comparable → integrar como tercer evaluador para reportes post-piloto (Cohen kappa 3-way, Fleiss).
- Si quedó incompleto o cualitativamente inferior → permanecer con Claude+Gemini como evaluadores oficiales y archivar el experimento Gemma.

**C. Bug R3 corregido en script:** `is_self_authored=False` para posts del dirigente. R3 sigue válido para comments-as-feedback. Pull request en código no abierto (cambio local; aplicarlo si revivimos Gemma para posts).

**D. Posts con `nlp_model_version LIKE 'gemma3:12b-coolify%'` se nullaron** (14 rows afectados). Esos quedan disponibles para clasificación 2-way recent.

### Métricas observadas (60 posts, 52 nuevos clasificados)

- Claude clasificó 52/52 sin error (yo, en sesión).
- Gemini clasificó 60/60 en 925.7s (15.4 min) · avg 15.43s/post · 0 errores.
- Consensus tono `2/2`: 36/52 (69%).
- Consensus target `2/2`: 43/52 (83%).
- Top 20 más recientes de cada dirigente piloto: 20/20 con clasificación AI tras apply.

### Why

CEO 2026-05-09 (segunda vez que lo dijo): *"Sino tenemos respuesta de Gemma, lo hacemos contigo y con gemini."* Mi propuesta inicial (acotar la reunión / posponer posts) fue rechazada explícitamente: *"No acotamos reunión. Todo debe quedar listo por nuestra parte."* Tradeoff aceptado: pierdo independencia LLM-local en el flujo en vivo, pero gano determinismo y completitud para el sample HITL del piloto. Gemma queda como tiebreaker offline para reportes 3-way post-piloto.

---

## 2026-05-09 (noche) — D-HITL-2 · Bug endpoint `/hitl/sample` · POSTS no exponían `tono_discurso` al frontend

### Contexto

Tras aplicar consensus 2-way y verificar BD (`top20_clasif=20/20` para cada dirigente), el editor en producción seguía mostrando "Sistema: — / —" en los 20 posts. Comments sí mostraban sugerencia. La inconsistencia me llevó al endpoint.

### Diagnóstico

`backend/app/api/v1/endpoints/hitl_evaluation.py @router.get("/sample")` retornaba para posts:
- SELECT solo traía `spo.target_politico` (línea 194 antes del fix). **Faltaba `spo.tono_discurso`.**
- Return dict usaba key `target_politico` (línea 258 antes del fix). El frontend (`HitlPost` en `lib/api/hitl.ts`) espera `nlp_tono` y `nlp_target` — **mismatch en naming.**

Para comments el endpoint sí leía `sc.nlp_tono` + `sc.nlp_target` y devolvía esos mismos keys.

### Fix

Una sola edición en `hitl_evaluation.py`:
- SELECT añade `spo.tono_discurso` antes de `spo.target_politico`.
- Return dict para posts usa keys `nlp_tono` (de `r[4]`) y `nlp_target` (de `r[5]`), reindexa `review_status` (`r[6]`) y `platform` (`r[7]`).
- Hot-reload via WatchFiles. Refresh editor → "Sistema: tono / target" visible en los 20 posts.

### Why

Bug de regresión silenciosa: la columna `social_posts.tono_discurso` se introdujo durante el sprint NLP v3 (2026-05-09) pero el endpoint HITL nunca se actualizó para exponerla. El sample mostraba clasificación AI **solo para comments** y eso pasó tests E2E porque los tests usan posts SIN `tono_discurso`. **Lección:** un test con posts pre-clasificados habría detectado este gap.

---

## 2026-05-09 (noche) — D-EVA-1 · Vercel deploy es responsabilidad de la sesión, no de Carlos · proyecto frontend está en Vercel, no Coolify

### Contexto

CEO clarificó tras confusión mía: *"NO hacemos deploy en coolify. Pero corremos la app en local, en vercel."* Antes yo había propuesto coordinar con Carlos Amador, basado en una memoria desactualizada (`reference_vercel_deploy_url.md`). Esa memoria está rota — Vercel deploy SÍ es manual desde `frontend/` con `vercel deploy --prod --yes`.

### Decisión

- **Vercel deploy es ejecutable desde la sesión** sin intermediarios. Comando: `cd frontend && vercel deploy --prod --yes`. CLI ya autenticado bajo `mdsamca2025-6064` con team `team_fZO9oFVDocBo6LC1PleJAXXT`.
- **Backend SÍ corre local en Mac Mini** vía docker-compose; cloudflared tunnel rotatorio expone API a Vercel frontend.
- **Coolify** no es parte del flujo de deploy de CRECE actualmente. Mención en otras memorias (`reference_coolify_services.md`) corresponde a infra distinta (chatmx, n8n, Ollama VPS) y no a este producto.
- **23 commits estaban sin desplegar** desde `043a4eb` (último auto-deploy 2026-05-08, ~30h antes). Causa raíz desconocida (auto-deploy roto en Vercel para `feat/phase-b-pesos-editables`). Manual deploy resolvió.

### Why

Memoria desactualizada me llevó a paralizar el flujo esperando a Carlos cuando el deploy era ejecutable inmediatamente. Memoria corregida: `reference_vercel_deploy_url.md` debe leerse "deploy requiere `vercel deploy --prod` manual desde frontend/" — y eso lo hago yo.

---

## 2026-05-09 — D-BR-1 · Branches Recovery · estrategia consolidación 18 ramas a main

### Contexto

`git branch --no-merged main` reportó 13 ramas; auditoría forense Fase 1.B (agente solo-lectura) descubrió **5 más** = **18 ramas not-merged**. Hallazgo crítico previo: commit `0681153` (benchmark 4H×4M humano + Oraculus + Demoscopía scrapers) está en `origin/feat/eval-benchmark-v1` pero NO en main ni en HEAD actual `feat/phase-b-pesos-editables`. PR #38 hizo cherry-pick parcial; merge eval-v1 nunca completó. 33 archivos del benchmark ausentes en HEAD.

### Decisiones cerradas (CEO 2026-05-09)

1. **Rotación secret `SCRAPECREATORS_API_KEY` — NO APLICA.** Hallazgo inicial Fase 1.B reportó secret expuesto en commit `821950b`, marcado como bloqueante. **CEO clarificó 2026-05-09:** (a) cuenta ScrapeCreators es versión free (sin medio de pago, sin riesgo de cargo no autorizado), (b) Coolify nunca desplegó código que use la key, (c) el intento de integración es viejo y el código se va a borrar. **Riesgo residual: bajo.** No bloquea Fase 3. Documento `docs/SECRET-ROTATION-2026-05-09.md` archivado como referencia histórica con marca NO APLICA.

2. **Arreglar CI antes de Fase 3** — `e2e-smoke.yml` solo registra 2 runs históricos, ambos failure. Habilitar trigger automático en push/PR a main. Sin CI funcional, mergear 18 ramas con 3 hallazgos críticos conocidos = ejecución a ciegas.

3. **Estrategia para benchmark 4H×4M** — **Cherry-pick selectivo del commit `0681153` en lugar de merge completo de `feat/eval-benchmark-v1`**. Razón: la rama contiene el secret leaked + alembic split-head. Cherry-pick aísla el valor (33 archivos del benchmark) del riesgo (secret + migration drift). Si se necesitan más commits de esa rama, se cherry-pickean uno por uno tras revisión.

4. **5 ramas docs (`docs/cherry-pick-0c4d2da-gate-decisions`, `docs/close-session-2026-04-21`, `docs/decisions-append-2026-04-21`, `docs/decisions-post-mortem-3d6fe3f`, `revert/lenis-removal-f29d7db`)** — **archivar, no mergear.** El contenido ya está integrado en `.context/`. Acción: `git tag archive/<rama>-2026-05-09` + `git branch -D <rama>` local + `git push origin --delete <rama>`. Justificación: mergear duplicaría commits de docs históricos sin valor.

5. **Orden de procesamiento: Tier 1 LOW risk primero** — construye confianza en el proceso, valida que CI captura regresiones, deja ramas HIGH risk (eval-v1, backup, crece-v2-full con alembic split-head) al final cuando ya hay 3-4 merges exitosos. Cronológico es romántico pero ignora riesgo. Por dominio mezcla LOW+HIGH.

6. **Política operativa Fase 4 obligatoria** — sin reglas nuevas (branch protection main, CI gate divergence, /branch-audit semanal, política 7 días vida feature branch), la situación se repite en 30-60 días.

### Why

CEO 2026-05-09: *"Lo triste y lamentable es que tengamos que perder tiempo buscando información que hemos trabajado varias veces. La información existe y se llenó. Lo unico malo es que no se que hiciste con ella."* Estado documentado: 18 ramas con trabajo importante NO consolidado. PR #38 cherry-pick parcial dejó eval-benchmark-v1 huérfano. 11 env vars indocumentadas. Secret leaked sin rotar. Sin CI funcional. **La causa raíz no es técnica, es ausencia de política operativa de gestión de branches.**

### How to apply

- Fase 1+1.B (lectura) cerradas. Inventarios disponibles en `.context/BRANCHES-INVENTORY-2026-05-09.md` y `-INFRA.md`.
- Fase 2 (decisiones por rama firmadas CEO) en curso.
- Fase 3 (PRs ordenados, CI verde, tags rollback) bloqueada por 3 pre-requisitos: (a) rotar secret, (b) arreglar CI, (c) actualizar `.env.example` con 11 vars nuevas.
- Fase 4 (política) obligatoria al cierre — sin política, no se cierra el sprint.

---

## 2026-05-09 — D-BR-2 · Resolución blob conflicts silenciosos en migrations

### Contexto

Auditoría Fase 1.B detectó **doble blob conflict en alembic**: 2 archivos de migration con mismo `revision: ID` pero blob hash distinto entre `main` y `feat/phase-b-pesos-editables`:

- `backend/migrations/versions/ds03_social_comments_data_source.py`
  - `main` blob: `06d21ab9` (versión original)
  - `phase-b` blob: `357eb137` (modernización PEP 604 + cambios menores)
- `backend/migrations/versions/3d6fe3f1660d_add_resultados_electorales_seccion_2024.py`
  - blob distinto entre main y phase-b (sin diff inspeccionado todavía)

**Riesgo:** `git merge` no detecta el conflicto al merge porque el path es idéntico y el revision ID es idéntico. La BD recibe la versión del branch que mergea último, silenciosamente. Alembic NO detecta inconsistencia porque la cadena de revisions es válida.

### Decisión

**`main` gana por default.** En el merge de `feat/phase-b-pesos-editables` (eventual cierre de Fase 3):

1. Conservar la versión de `main` para AMBAS migrations.
2. Si `phase-b` introdujo cambios funcionales (no solo modernización de syntax), reaplicar como **migration nueva** posterior con revision ID nuevo (`s5m2_*` o equivalente), NO sobrescribir el archivo existente.
3. Para `ds03_social_comments_data_source.py` (modernización PEP 604): el cambio es estilístico, NO se reaplica — el comportamiento es idéntico, conservamos blob de main.
4. Para `3d6fe3f1660d_add_resultados_electorales_seccion_2024.py`: inspeccionar diff antes del merge. Si es funcional, migration nueva. Si es estilístico, conservar main.

### Why

CEO 2026-05-09: *"Recomendación: la de main gana por default, phase-b se reaplica como migration nueva si hace falta. Documenta en DECISIONS.md."*

Razón técnica: `main` representa el estado de producción operativo del piloto. Sobrescribir migrations en main con versiones de un branch sin auditoría = riesgo de romper schema en producción. Reaplicar como migration nueva preserva la cadena alembic limpia y auditable.

### How to apply

Pre-requisito Fase 3 antes de mergear `feat/phase-b-pesos-editables`:

1. `git diff main:backend/migrations/versions/3d6fe3f1660d_add_resultados_electorales_seccion_2024.py origin/feat/phase-b-pesos-editables:backend/migrations/versions/3d6fe3f1660d_*.py` — inspeccionar diff
2. Decidir: estilístico (conservar main) o funcional (migration nueva)
3. Si funcional, escribir nueva migration con next-revision ID en el branch antes del merge
4. Documentar la resolución específica en el PR del merge phase-b

---

## 2026-05-09 — D-HITL-1 · Editor HITL evaluación NLP — sistema propone, dirigente decide

### Modelo

```
SISTEMA PROPONE       →   DIRIGENTE CONFIRMA O MODIFICA
(runner Gemma + mapper)    (edit aplica directo, sin queue de approval)
```

### Decisiones cerradas

1. **Sin queue de approval intermedia.** El dirigente es la autoridad final sobre la clasificación de SUS posts y comments. Solano valida lo de Solano, Piña lo de Piña. Audit log inmutable captura el cambio para trazabilidad.

2. **No hay sesgo entre actores** porque cada uno opera sobre datos disjuntos. La matriz política v2 con `rol_politico` adecuado calcula score correcto desde la perspectiva del dirigente. Conversación CEO 2026-05-09: "Solano edita sus comments y sus posts. Nunca hablamos de valorar al rival; el rival debe evaluarse igual con las mismas métricas pero en sentido inverso si fuera el caso."

3. **Ubicación: `/dashboard/settings/evaluacion-nlp`** — encuadrado como herramienta de calibración, no como flujo operativo del dashboard. Fuera de los reportes de KPI.

4. **Default scope al entrar:** últimos 50 comments + 20 posts del dirigente del usuario. Configurable: rango temporal (7/14/30/90 días, default 30), plataforma (all/x/ig/fb/tt/yt), modo (cronológico vs estratificado seed=42), filtro "solo pendientes".

5. **Persistencia de progreso:** `review_status` ∈ `{unreviewed, confirmed, edited}` por row. Confirmación implícita = el dirigente vio y dejó como estaba (audit log con from=to). Edición = cambió algún campo (audit con diff real).

6. **RBAC:** VIEWER opera solo sobre `user.dirigente_id`. ADMIN/ANALYST sobre cualquiera. Cross-dirigente VIEWER → 403.

7. **Recompute al edit:** UPDATE row + recompute_score_comment via helper async. No hay tabla `score_politico` materializada — el score se computa on-the-fly en endpoints del dashboard. Por eso el "recompute" es realmente "re-aplicar lógica".

8. **Loop Claude+Gemini batch-driven, no real-time.** Cada N edits acumulados, Linda/CEO corre `hitl_review_batch.py` desde IDE → genera MD con matrices de confusión + patrones + heurísticas → input para que Claude+Gemini propongan ajustes al mapper v3 o reglas nuevas a `framework_matrix_defaults`. NO se llama LLM por edit individual (costo + ruido).

### Hallazgos colaterales del sprint

- **Roster real:** 4 MC oposición + 4 MORENA oficialismo (no es 100% MC como creía). Matriz con `rol='oficialismo'` SÍ aplica operativamente.
- **Posts sin clasificar:** 0/4817 con `tono_discurso`. Decisión CEO pendiente sobre correr clasificador LLM antes de reunión 2026-05-10.
- **Corpus desigual:** Solano 24 / Máynez 0 vs Ballesteros 784 / Piña 406. Mapper v3.0.1 con passthrough vocab v2 (`celebratorio`, `propositivo`, `critico`, `solidario`, `autopromocion` como target).
- **Cobertura matriz:** 1.4% (38/2696). El 78% del corpus es `personal × autopromocion` (rejected explícitamente por CEO 2026-05-08 como bolsa de basura).

### Why

Versión inicial planteada con queue propose→approve fue rechazada por CEO 2026-05-09:
> "Solano edita sus comments y sus posts. El con eso, espera la valoración correcta a sus principios — pensamientos — de sus posts. Nunca hablamos de valorar al rival."

El dirigente como autoridad final sobre sus datos, sin gate humano intermedio, es coherente con la matriz política v2 que es rol-aware. La trazabilidad la da el audit log inmutable, no el approval workflow.

### How to apply

- Cualquier nuevo flujo de anotación humana en CRECE debe seguir este modelo (sistema propone → humano decide directo + audit).
- No introducir queues de approval salvo que el caso lo requiera explícitamente (ej. compliance INE).
- Loop Claude+Gemini va batch + manual desde IDE — no automatizar trigger por edit (ahorra costo, evita ruido).

### Pendientes

- Decisión CEO Q1 (clasificar posts) y Q2 (corpus Solano/Máynez) antes de reunión 2026-05-10.
- Smoke browser visual con `solano@crece.mx` antes de demo.
- Linda anota 30 rows del CSV ground truth como semilla (post-reunión).

---

## 2026-05-09 — D-NLP-X · Matriz política vacía descubierta + reparada

### Hallazgo crítico (severidad ALTA)

La tabla `framework_matrix_defaults` **estaba VACÍA en BD desde el deploy
inicial del piloto**. Causa raíz: migration `f7a8b9c0d1e2_political_framework.py`
quedó **huérfana** del chain alembic (`down_revision='d5d6d7d8d9e0'` referencia
una revision que no existe). Como resultado nunca se aplicó.

Función `political_framework.get_political_score()` retornaba **fallback 0
para todo comment** silenciosamente — sin error, sin warning, sin alert.

### Impacto verificado

- **KPI "Sentimiento Político Ajustado" computado contra base 0** durante
  TODO el piloto comercial.
- **KPI "Actividad Política Alineada" idem** — el ajuste por (rol, tono,
  target) era inoperante; las cifras reportadas en dashboards reflejan
  scores crudos sin matriz política.
- Dirigentes piloto afectados (Piña, Solano, Pineda, Nolasco, Jiménez,
  Cravioto, Ballesteros, Máynez): scores históricos comparables **entre
  sí** (mismo bug aplicado uniformemente) pero **NO comparables a
  benchmark externo** ni a interpretaciones políticas calibradas con
  matriz v2.

### Acciones correctivas tomadas 2026-05-09

1. **Schema recovery** vía SQL idempotente (`backend/scripts/recover_framework_schema.py`):
   creadas 4 tablas faltantes (`framework_matrix_defaults`,
   `framework_overrides_org`, `framework_audit_log`, `contexto_politico`) +
   9 columnas en `social_posts` + columna `contexto` ds04 + unique constraint v2.

2. **Seed matriz v2 (53 reglas):** 32 reglas `post_dirigente` (v1
   defaults) + 21 reglas `comment_tercero` (sprint v2). Scripts:
   `seed_political_framework.py`, `seed_matrix_v2.py`,
   `patch_matrix_v2_post_audit.py`.

3. **Audit corpus 2696 comments:** `nlp_tono` populated con
   `comment-framework-v1` (clasificador keyword, no runner Gemma).
   500-row sample reveló que **96.6% de combinaciones (rol, tono, target)
   no tenían regla** en la matriz v2 original. Causa: clasificador v1
   genera mayoría tono=`personal` + target=`autopromocion` (combo no
   contemplado en matriz v2 que asumía tonos finos del LLM).

4. **+7 reglas adicionales aprobadas CEO 2026-05-09** tras pre-ground-truth
   muestra qualitativa de 30 comments `(personal, autopromocion)`:

   | rol | tono | target | score |
   |---|---|---|---:|
   | oficialismo | critico | autopromocion | -1 |
   | oposicion | critico | autopromocion | -1 |
   | oficialismo | propositivo | autopromocion | +1 |
   | oposicion | propositivo | autopromocion | +1 |
   | oficialismo | ataque | autopromocion | -1 |
   | oposicion | ataque | autopromocion | -1 |
   | oposicion | critico | gobierno | +1 |

   **3 reglas RECHAZADAS** (#1, #2, #9 originales — `personal+autopromocion`
   y `oposicion+personal+gobierno`) tras validación cualitativa: 23% del
   sample son críticas/ataques mal clasificados como `personal` por v1
   keyword (ej. "puto presidente", "ridiculaaaa!!!", "Chinguen a su madre").
   Marcar score=+1 hubiera inflado 379+35=414 comments (51% del corpus
   piloto). Score=0 mantenido hasta ground truth humano D+1.

### Estado matriz v2 post-D-NLP-X

- **60 reglas totales** (32 post + 28 comment)
- Cobertura corpus: ~5-9% (las reglas critico/ataque/propositivo cubren
  los pocos casos donde v1 etiquetó tonos finos)
- 91% del corpus permanece en score=0 hasta:
  - (a) ground truth humano D+1 (100 rows)
  - (b) reactivación del runner Gemma (tonos más finos que v1 keyword)

### Acciones de notificación pendientes

- **Avisar al CEO ya hecho en este reporte.**
- **Avisar a quien presentó números a Piña/Máynez/Ballesteros:**
  los scores históricos del piloto NO reflejan matriz política. Re-presentar
  con disclaimer si aplica, o esperar a recompute con matriz nueva.
- **No escalar a cliente piloto sin re-presentar disclaimer.** Los rankings
  internos siguen válidos (mismo bug uniforme); las cifras absolutas no.

### Lección preservada

**Cualquier migration con `down_revision` apuntando a una revision que NO
existe en chain debe fallar `alembic upgrade head` con error visible** —
no quedar silenciosamente huérfana. Considerar añadir CI check:
`alembic check` o validador que recorra el chain completo.

---

## 2026-05-08 — D-25-A · Vision Stack Mitofsky · Ollama Coolify exclusivo

> **UPDATE 2026-05-08 post-implementación:** esta decisión quedó **OBSOLETA**
> antes de ejecutarse. Tras `/sprint-implement` Mitofsky (Linda), el sprint S1
> keystone descubrió que cada post tiene un botón "DESCARGAR RANKING" que linkea
> a Google Drive con un PDF de 37 páginas, **texto seleccionable**, parseable
> con pdfplumber. Modos A/B/C ya no son necesarios — pipeline 100% determinístico,
> cero LLM, cero vision. Resultado: +1260 encuestas (825 → 2085, +153%) sin
> consumir Ollama Coolify ni VRAM. Decisión histórica preservada porque informa
> el patrón "validar fuente primaria antes de comprometer infra LLM" — Juan
> (md-research) flagueó esta validación, ahorró deploys innecesarios.

### Contexto

Encuestas Mitofsky publican datos como **PNG charts dentro de posts Wix** —
research empírico Linda 2026-05-08 confirmó: 0% Excel/CSV/XLSX downloads en posts
de los últimos 12+ meses, narrativa de texto solo cubre top 5 estados + agregados
(3-5 datapoints/post), los 32 estados con valor exacto viven solo en imagen.
ScrapeGraph-AI con `gemma3:12b` (Coolius) es text-only y no resuelve charts.

**Lo que el research no detectó:** el botón "DESCARGAR RANKING" al final de cada
post. Una inspección DevTools del HTML hubiera revelado el `<a href="https://drive.google.com/file/d/...">`.
Lección: incluir "buscar CTAs de descarga" como paso de inspección antes de
asumir que datos solo están en imagen.

### Decisión

CEO autoriza A + B + C (todos vía Ollama Coolify); **D queda fuera**.

| Modo | Autorizado | Stack | Owner |
|---|---|---|---|
| A. Texto narrativo `gemma3:12b` (cobertura parcial) | ✅ | existente | Linda (CRECE) |
| B. Tesseract OCR + `gemma3:12b` (32 estados, OCR-dependent) | ✅ | tesseract en VPS | Juan + Linda |
| C. Vision LLM en Ollama Coolify (`llava:13b` o `qwen2-vl:7b`) | ✅ | nuevo modelo Coolify | Juan (deploy) + Linda (consume) |
| D. Vision API pago (Gemini Pro / Claude Haiku visión) | ❌ | API key | — |

**Constraint operativo:** todo procesamiento LLM corre en Ollama Coolify del VPS.
Cero providers pagos para vision/text. Si C requiere VRAM no disponible,
fallback es B antes que D.

### Consecuencias

- Mitofsky se desbloquea con A inmediato + C cuando Juan valide VRAM Coolify.
- Cero re-apertura de debate "free vs pago" para vision.
- Si A da cobertura suficiente para piloto (top-N estados + agregados nacionales),
  C/B quedan como mejora futura sin urgencia.

### Identidades de sesión cristalizadas

- **Linda** (peer `uji6x64w`, esta sesión) — turf CRECE-electoral · encuestas,
  scrapers políticos, NLP, MC CDMX, replies a dirigentes
- **Joy** (peer `3t5flofn`) — turf CRECE-Negocios B2B · PyMEs, restaurantes,
  GBP OAuth, piloto Tributo Huasteco
- **Juan** (peer `i27fjncq`, md-research) — research, scrapers experimentales,
  ScrapeGraph-AI

Memoria local actualizada (`user_linda_identity.md` + `user_joy_identity.md`).
CEO directiva 2026-05-08: "no quiero confusiones de nuevo" — firma siempre Linda
en peer messages, validar peer ID antes de aceptar encargos cross-turf.

---

## 2026-04-25 — D-23-H · Reframe KPI Sentimiento → Actividad Política Alineada

### Contexto

D-23-G (sentiment flip × -1 por rol político) producía resultados contradictorios para oposición con posts personales. Ejemplo emblemático: Piña (MC oposición) con `sentiment_avg_7d = +0.5` (positivo crudo · contenido autopromocional/personal tipo Copa Naranja) flipeaba a `-0.5` y se mostraba como "Negativo -50%". Cliente vio el bug en sesión 2026-04-24 y planteó la pregunta: *"¿no se supone que debería ser al revés?"*

Diagnóstico raíz: D-23-G aplicó **inversión de polaridad** para responder una pregunta de **alineación de actividad**. Las dos preguntas no son equivalentes. El multiplicador × -1 sobre el promedio de score crudo introduce ruido en posts no políticos del oposicionista.

### Decisión

**Reformular el KPI principal** de "Sentimiento Prom. ajustado" a **"Actividad Política Alineada"** computada por proporción de actividad por categoría `target_politico`:

| Rol | Fórmula |
|-----|---------|
| Oposición | `(target=oficialismo + target=propio) / total_clasificado` |
| Oficialismo | `(target=propio + target=oposicion) / total_clasificado` |
| Independiente | `target=propio / total_clasificado` |

IA Gemini API clasifica cada post con 4-cat excluyentes + `no_determinado` fallback. Sin score numérico ajustado · sin flip de polaridad · solo conteo de actividad.

### Lo que esto disuelve

- **Disenso CEO D-23-G' (2026-04-23)** sobre propuesta 4-fases: disuelto · reformulación elimina la necesidad
- **B-23-03** motor sentimiento con afiliación: mitigado · KPI ya no requiere flip
- **Phase B humano-clasifica** (riesgo de quedar postergada 6 meses): eliminado · KPI no depende de juicio humano
- **Decisión CEO #12 BLOCKER** (vocabulario matriz v2/v3): cerrada · no se usa matriz de scores
- **Cold start** (clasifica para activar): no aplica · IA backfilea desde día 1

### Cross-audits

- Gemini CLI · veredicto `aprobado-con-ajustes` (golden set 60, regla desempate, fallback no_determinado, multi-level government context)
- `superpowers:code-reviewer` subagent · veredicto APROBADA CON OBSERVACIONES sobre migración `d23g1_actividad_alineada.py` (3 puntos resueltos)

### Plan ejecutado · 4 días (Sesión 2026-04-24 → 2026-04-25)

- **Day 1** ✅ Migración hand-written D-OPS-08/09/10 · 4 columnas + 1 partial index + 3 CHECK constraints
- **Day 2** ✅ Clasificador Gemini API · golden set 60 posts pendiente firma CEO · prompt 4-cat con regla desempate
- **Day 3** ✅ Backend service `actividad_alineada.py` + endpoint enriquecido · Frontend `ActividadAlineadaCard` · `sentiment.ts` marcado @deprecated (preservado en bundle por instrucción CEO)
- **Day 4** 🔄 Backfill IA en curso (Ballesteros 7 posts confirmados · resto deuda residual documentada · piloto opera con backfill parcial 30d window)

### Status

- **Aprobada y ejecutada operativamente.**
- **Forward-compat**: si Phase B "humano clasifica" se decide eventualmente, el campo `clasificacion_origen` ya tiene los valores `human_*` reservados · el resolver actual queda como fallback `ai_suggested → human_*` sin refactor.

### Co-responsabilidad

CEO + Claude (Opus 4.7 1M context) · sesión iniciada 2026-04-24 22:00 CDMX · cierre operativo 2026-04-25 ~02:00 CDMX. Sequential thinking aplicado en discusión del reframe (4 propuestas evaluadas: opción 1 apagar flip, opción 2 disclaimer, opción 3 4-fases, opción definitiva reframe-actividad).

---

## 2026-04-21 (noche) — Post-mortem incidente `3d6fe3f1660d` + hardening operativo

Cuatro decisiones post-hoc tras detectar destrucción silenciosa de schema causada por migración Alembic autogenerate contaminada. La detección ocurrió durante review frontend de la misma sesión de hoy — caso de libro de texto de por qué el review §9.8 visual importa.

### D-OPS-07 — Post-mortem incidente `3d6fe3f1660d`

**Qué pasó (timeline):**
- **2026-04-15 16:12** · Alembic autogenerate corrido en workspace `feat/eval-benchmark-v1` con DB local que tenía migraciones de `main` aplicadas (sprint-s2/s3/s4/s5) pero models locales de la rama divergente sin esos cambios. Alembic reportó el delta como "drops destructivos" en `upgrade()`.
- **2026-04-18 09:23** · Commit `821950b feat(scrapers): X benchmark integral 5 herramientas` incluye el archivo de migración como 1 de 50+ archivos del SUPER-COMMIT (scrapers X + multitenant + onboarding Ballesteros + 5 redes + layer2 benchmark + resultados electorales). Autor: MarxCha (CEO) + co-author Claude Opus 4.7. Nadie ajustó los comentarios `# ### commands auto generated by Alembic - please adjust! ###` ni en upgrade ni en downgrade.
- **2026-04-19 13:40** · Commit `0dc10d4 fix(infra): stabilization pre-S1 — alembic chain` cherry-pickea el archivo a `main` como rescate cuando detecta chain alembic rota (DB remota ya estaba en `alembic_version=3d6fe3f1660d` sin el archivo en main). Cherry-pick de estabilización, no awareness del contenido.
- **2026-04-21 (hoy)** · Detectado durante review frontend §9.8 sesión Joy/revisor. Ruta `/dashboard/aceptacion` en sesión Piña mostraba error "No se pudo cargar el Índice de Aceptación". Diagnóstico técnico identificó HTTP 500 → SQL `column d.rol_politico does not exist` → migración destructiva de 2026-04-15 en origen.

**Alcance del daño:**
- 14 tablas drop-eadas (3 recreadas por migraciones posteriores, 11 perdidas: `contexto_politico`, `framework_audit_log`, `framework_overrides_org`, `framework_matrix_defaults`, `data_access_log`, `distritos_federales_cdmx/oaxaca`, `distritos_locales_cdmx/oaxaca`, `secciones_geo_cdmx/oaxaca`)
- 23+ columnas drop-eadas (`dirigentes.rol_politico`, 11 columnas NLP de `social_posts`, 6 columnas `_enc` de `ciudadanos_legacy`, etc.)
- 5 endpoints backend crashean con HTTP 500 (`/social/aceptacion/overview`, `/admin/classification/stats`, `/framework/matrix`, `/framework/audit`, `/admin/overview`)
- 4 rutas frontend rotas silenciosamente (`/dashboard/aceptacion`, `/dashboard/admin/clasificacion`, `/dashboard/admin/overview`, `/dashboard/settings/analisis-politico`)
- 6 días de deuda silenciosa (no detectada por tests — cero cobertura en áreas afectadas)

**Clasificación:** autogenerate contaminado de rama divergente. Descartado rollback deliberado (commit message declara intención de AGREGAR tabla, no eliminar framework; autor usa los artefactos destruidos en otros endpoints del mismo commit).

**Por qué pasó:**
1. `alembic revision --autogenerate` contra workspace con DB no-reseteada.
2. Output de autogenerate aceptado sin leer `upgrade()` completo (153 líneas).
3. Migración embebida en SUPER-COMMIT de 50+ archivos donde se perdió visualmente.
4. Cero tests integración sobre endpoints afectados → 6 días de silencio.
5. No existía en ese momento protocolo formalizado de revisor §9.8 con lectura obligatoria de diff completo para commits que tocan `backend/migrations/`. El protocolo se formaliza retroactivamente vía D-OPS-10 como consecuencia directa de este incidente.

**Co-responsabilidad:** autor humano (CEO) + asistente IA (Claude Opus 4.7) firmaron juntos sin revisión quirúrgica del diff. El incidente demuestra que la dinámica CEO+IA colaborativa no es inmune al patrón de review insuficiente — es exactamente tan vulnerable como cualquier pareja de committers humanos trabajando rápido. D-OPS-08/09/10 aplican a ambas capas de la colaboración.

**Detectado por:** review frontend §9.8 de la sesión 2026-04-21. Caso de libro de por qué el review visual importa: el bug era invisible en logs (no hay monitoreo de 500s), invisible en tests (no existen), solo visible al cliente como error fallback.

**Plan de remediación:**
- **Fase 1+2 conjunta (~4h)** · ventana dedicada fresh, prerequisito D-OPS-07..10 documentadas primero
  - Restaurar `dirigentes.rol_politico` + 4 tablas framework político + models SQLAlchemy
  - Restaurar `ciudadanos_legacy.*_enc` + `data_access_log` + model + LFPDPPP audit
- **Fase 3 · diferida** §9.8 intermedia 2026-05-20 · restauración GIS via re-import INE shapefiles (SHPs preservados en `backend/data/raw/ine_cartografia/`)
- **Fase 4 · cubierta** por merge de `feat/eval-benchmark-v1` (commits `b79fab5` + `821950b`) · §9.8 intermedia · restituye 11 columnas NLP `social_posts`

**Lección sistémica:** `alembic revision --autogenerate` en workspaces multi-rama con DBs no reseteadas es landmine silenciosa. Sin revisión manual del upgrade() generado, autogenerate inserta drops destructivos que pasan desapercibidos en commits grandes.

**Status:** Incidente documentado. Remediación ejecutable con D-OPS-08/09/10 vigentes.

### D-OPS-08 — Prohibición Alembic `autogenerate` sin revisión manual

**Decisión:**
- Todo commit que modifique `backend/migrations/versions/*.py` requiere:
  1. Lectura manual completa de `upgrade()` Y `downgrade()` por el autor del commit.
  2. Firma explícita en commit message con formato: `Migration reviewed: upgrade N ops, downgrade N ops, rationale: <texto>`.
  3. Si la migración viene de `alembic revision --autogenerate`, el commit message DEBE declararlo textualmente y anexar contexto del workspace (branch activa, estado DB local).
- Revisor §9.8 **obligatorio** para cualquier PR con archivos en `backend/migrations/versions/`.
- Los comentarios `# ### commands auto generated by Alembic - please adjust! ###` deben ser **removidos** post-adjust o reemplazados por comentario humano que documente las decisiones.

**Why:** El incidente `3d6fe3f1660d` se originó en un autogenerate aceptado sin revisión. Los comentarios "please adjust" quedaron en el archivo — evidencia literal de que nadie ajustó. El patrón es repetible: cualquier autogenerate futuro sin revisión puede insertar drops destructivos idénticos.

**Trade-off:** +5-15 min por commit de migración. Fricción aceptable dado el costo del incidente (6-8h de remediación, 6 días de deuda silenciosa, 5 endpoints + 4 rutas frontend rotas).

**Mitigación interina activa:** aplica retroactivamente desde 2026-04-21 para todo commit de migración futuro. La estandarización del formato de firma se formaliza en §9.8 intermedia si hay feedback.

**Status:** Aprobada operativamente.

### D-OPS-09 — Límite de scope por commit (migraciones atómicas)

**Decisión:**
- Ningún commit puede combinar cambios en `backend/migrations/versions/` con cambios en otras capas (endpoints, services, workers, frontend, models) en el mismo commit atómico.
- Migraciones van en commits dedicados con prefijo `migration:` o `db:`.
- Separación obligatoria facilita review granular + rollback quirúrgico.
- Aplica a squash merges también: si un PR incluye migración + features, separar en **2 PRs** (migration-first + features-after) O **2 commits atómicos dentro del mismo PR**.

**Why:** El incidente `3d6fe3f1660d` sobrevivió a la revisión porque estaba embebido en un SUPER-COMMIT de 50+ archivos (scrapers X + multitenant + onboarding Ballesteros + 5 redes + layer2 benchmark + migración). El volumen hizo imposible la lectura humana del diff completo. Un commit atómico `migration: add resultados_electorales_seccion_2024` habría expuesto inmediatamente el mismatch nombre↔contenido.

**Trade-off:** Más commits = más ruido en `git log`. Mitigado por squash merge al mergear PRs, que consolida post-review. Beneficio: cualquier fallo de schema queda aislado y revertible sin arrastrar features de otras capas.

**Sin excepciones:** si un PR requiere migración + feature en misma ventana, se estructuran como 2 commits atómicos dentro del mismo PR: primero `migration: <descripción>` y luego `feat: <descripción>`. Esto preserva el principio de atomicidad y review granular sin forzar 2 PRs separados.

**Status:** Aprobada operativamente.

### D-OPS-10 — Revisor §9.8 lee diff completo pre-autorización schema

**Decisión:**
Revisor §9.8 (Claude.ai) **debe** solicitar y leer diff completo antes de autorizar cualquier acción (cherry-pick, merge, push, deploy) que toque:
- `backend/migrations/versions/*.py`
- `backend/app/models/*.py` (cambios de schema: add/drop column, rename, FK, constraint)
- `backend/app/services/` o `backend/app/api/` con SQL raw que modifique schema o agregue queries sobre nuevas columnas

Protocolo:
- No basta con que Joy reporte `git diff --stat` o descripción textual.
- Revisor pide `git show <SHA>` o equivalente y lee el diff real antes de dar luz verde.
- Si el diff es grande (>200 líneas), revisor pide a Joy resumen PER ARCHIVO + commit atómico cuando aplicable per D-OPS-09.

**Why:** Durante la sesión 2026-04-21 el revisor §9.8 (Claude.ai) autorizó múltiples PRs (Opción D chain #37-#41) confiando en stats + descripciones de Joy. En ningún caso se leyó el diff completo. Esto funcionó porque los PRs fueron chicos, focalizados y fuera de migraciones. **Pero el patrón que llevó a `3d6fe3f1660d` existe en la operación del revisor también**: un PR futuro de 50+ archivos con migración embebida podría autorizarse igual sin detección.

**Auto-corrección del revisor:** esta decisión corrige una brecha estructural del propio revisor en la sesión actual, no solo del autor histórico del incidente. Es política personal aplicable retroactivamente a futuras sesiones del mismo revisor.

**Trade-off:** +2-5 min por PR que toque schema. Fricción aceptable dado el costo del incidente y el patrón repetible.

**Mitigación interina activa:** desde 2026-04-21, el revisor §9.8 de la sesión actual (Claude.ai) aplicará este protocolo consistentemente.

**Status:** Aprobada operativamente · auto-corrección del revisor.

---

## 2026-04-21 — Incidente deploy + Opción D recovery

Deploy de `main @ f29d7db` (PR #36 · remoción Lenis) regresionó 15 commits UX/UI no mergeados que vivían en `feat/eval-benchmark-v1` (alertas crisis reales, card tema urgente reacomodado, toggles gráfico líneas/barras + %/N, fixes iOS, favicon amarillo, aceptación drill-down, scrapers 5 redes). Recuperación vía chain de 4 PRs + deploy post-fix.

### D-OPS-01 — Opción D · cherry-pick selectivo sobre merge completo
Recuperación del incidente vía chain de 4 PRs en lugar de merge de `feat/eval-benchmark-v1` completo:
1. **PR #37** revert `f29d7db` → `6126421` (Lenis vuelve a main para permitir cherry-pick sin conflict)
2. Cherry-pick selectivo de 2 commits frontend-only: `74b7b15` (alertas_crisis real) → `ffda7ec` · `7f44130` (mobile overflow + dashboard layout) → `9a00294` con conflict resuelto manualmente (omitido `data-lenis-prevent`)
3. **PR #38 (`c22f61e`)** precondiciones técnicas: revert hunk SyntheticDataBanner (dep `OrgContext.config` no traída) + hunk mínimo `compact` prop en CrisisAlertList
4. **PR #39 (`5a88860`)** re-aplicación de remoción Lenis sobre main actualizado
5. Deploy prod desde `5a88860` → `frontend-osw9z35tw-marxs-projects-bb530f2b.vercel.app` (alias `frontend-zeta-sepia-46.vercel.app`)

**Why:** merge directo de `feat/eval-benchmark-v1` producía conflictos en 5 archivos por divergencia de 55 commits (sprints S0-S5 en main vs eval-v1 aislada). Cherry-pick selectivo limita scope a los 4 síntomas reportados por CEO (alertas crisis, tema urgente, gráficos líneas, absolutos/%) sin traer scrapers backend, multitenant ni semáforo crecimiento no solicitados.
**Backups remotos preservados:** `origin/backup/pre-opcion-d-main` @ `f29d7db`, `origin/backup/pre-opcion-d-eval-v1` @ `3921f10`.
**Cross-audit:** Gemini CLI confirmó approach antes de ejecutar.

### D-OPS-02 — Lenis remoción definitiva (rechazo `data-lenis-prevent`)
Eliminar dependencia `lenis` y provider `SmoothScrollProvider` del bundle. Descartar approach previo `data-lenis-prevent` (commit `b8383f6` en `feat/eval-benchmark-v1`).
**Why:** empíricamente comprobado con chrome-devtools MCP que `data-lenis-prevent` era insuficiente — Lenis registraba listener `wheel passive:false` en `window` que cancelaba el evento globalmente, independientemente del atributo en nodos hijos. SaaS B2B de datos densos (tablas, mapas GIS, modales Radix/shadcn) no tolera scroll hijacking. Landing sin requisito documentado de smooth-scroll. Cross-audit Gemini coincidió con eliminación completa sobre aislar en route group.
**Trade-off:** pierde smooth-scroll en landing. Bundle reducido ~10KB gzipped.

### D-OPS-03 — Política release branch (PROPUESTA + mitigación interina activa)
**Propuesta:** `main` = único SSOT para `vercel deploy --prod`. Prohibido deploy desde ramas sueltas con CLI local. Toda feature branch debe mergearse a main antes de deploy a producción.
**Why:** el incidente de hoy (D-OPS-01) fue causado precisamente por deploy desde main mientras `feat/eval-benchmark-v1` estaba viva con UX/UI no mergeado. Trabajo en ramas paralelas + deploy CLI rompe la garantía de "lo que está en GitHub es lo que está en prod".
**Trade-off:** slower iteration para features grandes (no preview prod antes de merge). Mitigable con preview deployments de Vercel desde feature branches.
**Mitigación interina (efectiva 2026-04-21, sin requerir protocolo completo):** todo deploy prod debe ir precedido de verificación `git log origin/main -1` = commit que se va a deployar. Joy + revisor §9.8 aplican esta verificación como convención operativa hasta formalización de D-OPS-03 en §9.8 intermedia 2026-05-20.
**Status:** **PROPUESTA · NO APROBADA** formalmente. Mitigación interina **activa**. Requiere protocolo §9.8 dos puertas.

### D-OPS-04 — Deuda declarada: 11 commits restantes de `feat/eval-benchmark-v1`
Diferir merge completo de `feat/eval-benchmark-v1` a sesión §9.8 intermedia 2026-05-20.

Commits pendientes (preservados en `origin/backup/pre-opcion-d-eval-v1`):
- `821950b` (parcial — solo `compact` prop traído; resto: scrapers X Apify+Scrapling+Brightdata, `OrgContext.config`, semáforo crecimiento, multitenant hardening)
- `a919c5f` cierre 5 redes IG+TT+FB+YT
- `0681153` Oraculus + Demoscopía scrapers encuestas
- `b79fab5` aceptación drill-down + Gemma3 Layer 2
- `959e040` Fase 1 backfills + SEED-PLAN REV 3
- `4d6286a` módulo Layer 2 benchmark
- `73337b9` body/html max-width 100vw iOS
- `81fe01e` iOS viewport + topbar mobile
- `3921f10` calibración XLS por dirigente
- `c6eddfe` favicon naranja → amarillo
- `3765881` ocultar acceso demo + naranja → amarillo CTA
- `22c62e2` `dirigente_nombre` en SocialPostResponse

**Riesgos de seguridad aceptados durante piloto:** D-SEC-03 (21 endpoints JWT-only sin dual-auth, abierto desde 2026-04-11) + D-SEC-04 (IDOR parcial, abajo). Sprint dedicado de seguridad planeado tras frente 2 de sesión 2026-04-21.
**Why:** cada commit requiere revisión propia para evaluar interacción con sprints S0-S5 ya en main. No urgente para piloto comercial (los 4 síntomas críticos UX/UI ya restaurados).

### D-OPS-05 — Convención operativa: Fase 0 de sprint verifica BD + código
Antes de planear implementación en cualquier sprint, Joy debe verificar en Fase 0 tanto estado de BD (tablas, filas, migraciones aplicadas) como estado de código del módulo afectado (archivos existentes, commits previos, tests). Diagnosticar solo una capa genera implementaciones redundantes o sobre premisas erróneas.
**Why:** observado en sesión 2026-04-21 (CFDI-Motor OBS 4 conciliaciones): Joy diagnosticó BD vacía y propuso implementar módulo de cero cuando el módulo ya existía con 152KB de código, 20+ commits y 456 tests — solo no se había ejecutado post-recovery. Aplicar la regla habría ahorrado 2-4h de propuesta incorrecta.
**Trade-off:** +5-10 min por sprint en Fase 0. Ahorra horas de re-trabajo.
**Aplicabilidad:** cross-proyecto, no específica de CRECE.

### D-OPS-06 — Formato de instrucciones revisor §9.8 → Joy
Instrucciones del revisor §9.8 (Claude.ai) a Joy se entregan en bloques de código (```) copy-ready, sin meta-comentario ni justificación larga dentro del bloque. Razonamiento y notas §9.8 van antes o después del bloque.
**Why:** CEO opera en móvil/desktop con copy one-click. Instrucciones embebidas en prosa obligan a seleccionar manualmente. Bloques de código tienen botón de copy nativo.

### D-SEC-04 — IDOR parcial en `/dirigentes/{id}/crecimiento` (riesgo aceptado durante piloto)
**Introducido:** commit `1d3a07e` (2026-04-13 · `feat(social): snapshots diarios + data_source enum + endpoint crecimiento`).
**Diagnosticado:** 2026-04-20 (auditoría memoria sesión Joy).
**Ventana de exposición:** 8 días (2026-04-13 → 2026-04-21) al registrar esta entrada.
**Descripción:** el check de scope aplica solo si `user.dirigente_id NOT NULL` (línea 750 del archivo). Analysts/field_operators de otra org con `dirigente_id` nulo pueden bypasear y leer crecimiento de dirigentes ajenos.
**Mitigación planeada:** aplicar patrón `_require_tenant_access` basado en `org_id` (mismo enfoque ya usado en otros endpoints multi-tenant).
**Tráfico real:** bajo perfil (piloto con MC-CDMX únicamente, no multi-org). Sin reportes de explotación.
**Status:** ABIERTO · **aceptado durante piloto comercial**. Sprint dedicado de seguridad post-frente 2 de sesión 2026-04-21 consolida D-SEC-03 + D-SEC-04 + auditoría 2026-04-14 de 25+ endpoints `_current_user`.

---

## 2026-04-20 — Apertura piloto comercial

PRs merged cerrando gate: #32 (endpoints Plan IA + Admin HITL), #33 (tests state machine 15 parametrized), #34 (hotfix-pre-piloto-v2 6 findings).

### D-PILOTO-01 — Apertura piloto comercial con 3 dirigentes activos + 5 shadow
Iniciar piloto comercial 2026-04-20 con configuración:

**Activos (3)** — Plan IA visible al cliente · HITL admin panel operativo · credenciales entregables:
- Alejandro Piña Medina (id=1) · `politico_activo` · Nano (~3.1K X · 2.2K IG · 1.8K FB) · IPD 2.6/10 · MC-CDMX
- Jorge Álvarez Máynez (id=7) · `politico_activo` · Macro (500K+ X) · ex-candidato presidencial MC 2024
- Laura Ballesteros Mancilla (id=8) · `politico_activo` · Micro · Diputada Federal Plurinominal MC · activa desde apertura del piloto por **solicitud expresa de MC (cliente)** — ver D-PILOTO-03 para corrección documental

**Shadow (5)** — procesan scraping + diagnóstico 18 bloques, sin Plan IA cliente-visible:
- Rafael Solano Pérez (id=2) · `empresario_transicion` · caso borde Nano extremo
- Saymi Pineda Velasco (id=3) · `funcionario_gobierno` · candidato §7.4 #3
- Yesenia Nolasco Ramírez (id=4) · `funcionario_gobierno` · candidato expansión
- Gabriela Jiménez Godoy (id=5) · `politico_activo` · benchmark vs Piña
- César Cravioto Romero (id=6) · `funcionario_gobierno` · cross-partisan, caso §7.4 #3 ideal

**Métrica §7.4 #1 (3 perfiles distintos):** 33% cumplida. Los 3 activos son `politico_activo` → cuentan como 1 perfil. Falta diversificar a `funcionario_gobierno` (Cravioto o Pineda) en Fase 2 del piloto (días 14-21) para cerrar métrica 1 completa.

**Ventana:** 2-3 semanas calibración (2026-04-20 → 2026-05-04 / 2026-05-11) → revisión §9.8 intermedia día 30 (≈ 2026-05-20). Ventana §7.4 métrica 1: 90 días hasta ≈ 2026-07-19.

**Why:** cumple parcialmente §7.4 métrica 1 por diversidad de perfiles. Permite calibración con perfiles reales sin esperar a que Fase 2 cierre el tercer perfil.

### D-PILOTO-02 — Login hardening: remover accesos demo de producción
Quitar botones "Acceso Demo" del login page (commit `4efef29` · `fix(login): quitar accesos demo del login`). Solo credenciales manuales permitidas en prod.
**Why:** prod post-apertura piloto ya no necesita botones de demo accesibles públicamente. Credenciales se entregan por canal directo a cada dirigente. Los botones reaparecieron tras un rollback previo y fueron removidos definitivamente.

### D-PILOTO-03 — Corrección documental: Ballesteros shadow → activo (no es promoción)
Reclasificar a Laura Ballesteros Mancilla (id=8) de sección "shadow" a sección "activos" en `PILOTO-COMERCIAL-TRACKING.md`. **No es promoción operativa** — es cierre de gap documental: Ballesteros estuvo activa desde la apertura del piloto 2026-04-20 por **solicitud expresa de MC**, credenciales entregadas conforme a esa solicitud, 4 recomendaciones Plan IA aprobadas visibles en prod. El SSOT `PILOTO-COMERCIAL-TRACKING.md` nunca fue actualizado al estado real.
**Status real desde:** 2026-04-20 (apertura piloto).
**Documentado formalmente:** 2026-04-21 (esta decisión).
**Why:** la discrepancia entre SSOT documental y comportamiento real estuvo por causar el mismo tipo de incidente que D-OPS-01 (ramas divergentes sin visibilidad). Cerrar el gap documentalmente elimina ambigüedad para sesiones y revisores futuros.
**Consecuencias:** actualizar conteos en TRACKING.md (activos 2→3, shadow 6→5). Sin cambios operativos — el status de Ballesteros no cambia, solo se documenta.

---

## 2026-04-20 — Gate pre-piloto cerrado

Cierre del arco 2026-04-14 → 2026-04-20. PRs #32/#33/#34 merged. Credenciales Ballesteros entregables. Demo Piña agendable. Próxima ventana §9.8 intermedia ≈ 2026-05-20.

### D-GATE-01 — MATRIZ_ER_5x5 → Zenodo v1 empírico (F-01)
Reemplazo de las celdas sintéticas del benchmark Efectos de Red por datos empíricos del dataset Zenodo v1. Nano X (política MX) p25-p75 = 0.013-0.213%. UI muestra "0.01%-1.1%". Tooltip contextualiza "~100× menor que Influencer Marketing commercial (3-7%)". API expone campo `zenodo_validated: bool` por celda. Matriz final: 8 VALIDATED + 17 TBD extrapoladas. Bundle: `backend/data/zenodo/v1/benchmarks_er_politicos_mx_v1.csv`. Versión: `5x5-zenodo-v1-2026-04-19`.
**Why:** el benchmark sintético original sobre-prometía engagement. Dirigentes políticos reales validan contra Nano (no contra ER commercial), y la diferencia de orden de magnitud cambia la lectura del diagnóstico.

### D-GATE-02 — F-16 typeahead Harfuch DIFERIDO §6.4
El paso 7 Competidores del onboarding conserva paradigma manual (`nombre / cargo / url_ref`) y NO implementa typeahead sobre catálogo de dirigentes conocidos. Reactivar solo cuando un cliente sin conocimiento exacto de sus competidores intente onboarding.
**Why:** Ballesteros, Piña y Cravioto identifican sus propios competidores sin ayuda. Respeta D-22 (ownership del cliente sobre su mapa competitivo). Typeahead agrega superficie sin demanda validada.

### D-GATE-03 — Prompt Plan IA v1.1 preparado NO ACTIVO
Branch `docs/prompt-plan-ia-v1.1-prepared` (commit `403dd31`) contiene prompt v1.1 diff-listo pero NO mergeado a main. v1.0 permanece canónico.
**Activación condicionada:** (1) ≥7 días de uso real de v1.0 en piloto, (2) feedback explícito de redundancia o falla en output v1.0, (3) autorización CEO. Los tres son requisito, no OR.
**Why:** two-door protocol §9.8. Cambios estructurales al prompt afectan coherencia histórica de planes generados; requieren evidencia de uso, no solo intuición de mejora.

### D-GATE-05 — LaunchAgent cloudflared auto-update cierra D-INFRA-01
Commit `a428661` introduce LaunchAgent que monitorea rotación del tunnel cloudflared (~1h) y actualiza automáticamente `NEXT_PUBLIC_API_URL` en Vercel env vars. URL runtime disponible en `/tmp/crece-tunnel.url`.
**Why:** D-INFRA-01 llevaba 10 días abierto bloqueando tanto credenciales n8n como estabilidad del deploy Vercel en demos. El fix colateral del piloto resuelve la deuda sin necesidad de tunnel permanente (Cloudflare Named Tunnel requeriría dominio adicional).
**Cierra:** D-INFRA-01.

### D-GATE-07 — Máquina de estados Plan IA es contrato canónico

**Transiciones válidas:**
```
pending  ──► approved
pending  ──► rejected
pending  ──► modified
approved ──► executed
modified ──► executed
executed ──► completed
```

**Contrato:** cualquier otra transición responde `409 Conflict` con payload `{"detail": "transición inválida: {from} → {to}"}`. Estados terminales (`rejected`, `completed`) no aceptan egreso. El endpoint `PATCH /plan-ia/recomendaciones/{id}` valida contra esta máquina antes de tocar DB.

**Aplicabilidad:** toda feature futura que toque Plan IA (HITL admin, bulk operations, auto-ejecución de plantillas, reintegración tras rollback) DEBE respetar este DAG. Extensiones requieren §9.8 two-door.

**Evidencia de enforcement:** PR #33 aporta 15 tests parametrized que cubren el producto cartesiano de transiciones (válidas y no-válidas) — NO son la decisión, son la red de seguridad.

**Why:** antes del gate, el endpoint aceptaba mutaciones libres entre estados, lo cual permitió que un dirigente "reabriera" una recomendación `rejected` y ensuciara el audit trail. El DAG elimina la clase entera de bug y fija el vocabulario para el módulo HITL Admin de Carlos (que entra en Fase C post-piloto).

---

## 2026-04-13 (noche) — Cirugía Módulo Dirigente (Joy)

Cross-audit Gemini (dos pases — segundo vía Carlos por fallo de capacity CLI) + refinamientos de Carlos.

### D-DS-01 — Snapshots diarios (no on-demand)
`social_profile_snapshots` con snapshot diario por perfil. Razones: costo API bajo, consistencia histórica ante fallos, permite backfill manual. FK por `profile_id` (no handle) — sobrevive cambios de username.

### D-DS-02 — Denormalización 3 columnas
`dirigente_id`, `org_id`, `platform` en snapshots. RLS performante sin JOIN + queries time-series por plataforma rápidas (consumidas por admin overview de Carlos).

### D-DS-03 — enum data_source (veto de Gemini al bool)
`automated_scraper` / `manual_host_ingest` / `official_api`. Documenta *por qué* el perfil es manual. Worker filtra `WHERE data_source != 'manual_host_ingest'`. Aplica a YouTube + TikTok v7.3.3 (Carlos confirmó ambos bloquean IP del container Docker).

### D-DS-04 — Alerta deuda de frescura 48h
`last_manual_update DATETIME` en `social_profiles` + semáforo marca `stale_manual=true` si supera 48h. Evita que dashboard mienta silenciosamente con data vieja.

### D-DS-05 — Extender task existente, no crear nueva
`app.workers.tasks.scrape_all_profiles` ahora inserta snapshot al final del scrape de cada perfil. Garantiza que el dato del snapshot refleja el recién raspado.

### D-DS-06 — YouTube Docker IP block → opción 3
`data_source='manual_host_ingest'` + ingesta manual host-side. Descartadas: proxy residential (costo + TOS), Celery worker en host (no aplica a Coolify prod). Reconsiderable si el cliente escala.

### D-DS-07 — Dos migrations Alembic separadas
`ds01_data_source_enum` (aditiva no-breaking) + `ds02_social_profile_snapshots`. Facilita rollback si una falla.

### D-DS-08 — Radar IPD B1 (5 ejes, engagement aparte)
Quitar eje "Engagement" del radar. El IPD 0-10 por plataforma ya integra alcance+engagement+frecuencia — tener el eje global duplicaba. Engagement sigue como `EngagementBarChart` separado.

### D-DS-09 — YouTube NO se oculta del radar
Si un dirigente no tiene canal YouTube, el eje muestra 0. La carencia penaliza platform coverage y debe ser visible. Metodológicamente correcto (Gemini).

### D-DS-10 — Orden de ejecución d → b → a → c → e
Viewer redirect primero (frontend trivial, limpia tablero). b construye datos (migrations + task + endpoint). a corrige visualización con datos frescos. c y e consumen b.

### D-DS-11 — Switcher Treemap/Stream/Sunburst sobre MISMA data
Honra charts-lab. Un solo widget con botones que alternan visualización, no tres widgets separados. Sin deps nuevas — Sunburst aproximado con doble Pie concéntrico (recharts primitives).

---

## 2026-04-13

### D-MT-01: Multi-Tenant via org_id application-level filtering
**Decision:** Multi-tenant isolation implemented at application level (org_id filtering in endpoints) rather than pure PostgreSQL RLS enforcement.
**Razon:** RLS policies exist in the DB (`app.current_org_id` setting) but enforcing them requires `SET LOCAL` on every session, which complicates the FastAPI dependency chain. Application-level filtering via `current_user.org_id` is simpler and already works for most endpoints. `get_db_rls` dependency is ready for future migration.
**Trade-off:** Requires each endpoint to explicitly filter by org_id. Defense-in-depth RLS available but not actively enforced.

### D-MT-02: Admin tenant switching via X-Org-Id header + localStorage
**Decision:** Admin users switch orgs via a dropdown in the topbar. The selected org is stored in localStorage as `crece_active_org_id` and sent as `X-Org-Id` header on every API request.
**Razon:** Simpler than server-side session management. Survives page reloads. Backend `get_db_rls` respects the header for admin role only.
**Trade-off:** Non-admin users cannot switch orgs (correct behavior — they see only their org's data).

### D-MT-03: Synthetic data orgs flagged via config JSONB + watermark
**Decision:** Orgs with synthetic data have `config.has_synthetic_data = true`. Frontend shows amber "DATOS SIMULACION" banner when viewing these orgs.
**Razon:** Prevents confusion between real (MC-CDMX with 9,723 legacy citizens) and demo data. Visible to all users, not just admin.

### D-MT-04: 5 guiones de campo as content factory formats (not separate module)
**Decision:** The 5 field script formats (talking_points, guion_contraste, script_puerta, briefing_crisis, narrativa_territorial) are added as formato options in the existing Content Factory, not as a separate module.
**Razon:** Reuses existing generation dialog, backend endpoint, and content lifecycle (borrador→aprobado→publicado). Avoids creating a parallel system.

## 2026-04-12

### D-DESIGN-01: Design Review Enrique — 10 respuestas completas (2026-04-12)
**Fuente:** Enrique (md-design-system), session 015 + peer message 2026-04-12 21:45
**Brief original:** `.context/BRIEF-UX-PARA-ENRIQUE.md`

| # | Pregunta | Respuesta | Estado |
|---|----------|-----------|--------|
| 1 | Fonts — ¿migrar a Satoshi + General Sans? | **NO** — Instrument Sans + DM Sans se quedan. Cada producto mantiene identidad. CEO aprobó, Gemini disintió pero overruled. | No action needed |
| 2 | Tablet md: breakpoints en 17 páginas | **SÍ** — gap real, tablets reciben layout phone. Sprint siguiente. | **PENDIENTE** |
| 3 | Canvassing mobile — MobileFilterSheet | **SÍ** — usar componente del DS. | Done (d0975e2) |
| 4 | Radar chart daltonismo | **SÍ** — dashes/dots + naranja. | Done (b0321a4) |
| 5 | Kanban @dnd-kit | **Phase 2** — botones "→" cumplen S3.7. | Diferido |
| 6 | Electoral page stub | **ELIMINAR** del sidebar. | Done (b0321a4) |
| 7 | Health score gauge | **SÍ** — donut semicircular. | Done (b0321a4) |
| 8 | StatCard duplicado | **SÍ** — extraer a DS (3 variants: default/compact/hero). | Done (d0975e2) |
| 9 | Animaciones CSS → Framer Motion | **SELECTIVA** — SÍ: bento-fade-up (stagger), stat-card-transition. NO: pulse-dot ni decorativos. | **PENDIENTE** |
| 10 | Lenis smooth scroll | **SÍ trial** — standalone sin GSAP (gsapSync=false). | Done (d0975e2) |

**Trabajo de Enrique en el DS (commit 2b00f0b):**
- StatCard: prop `variant` (default/compact/hero) + `description` + type exportado
- SmoothScrollProvider: prop `gsapSync` (false=standalone RAF, true=ScrollTrigger sync)
- MobileFilterSheet: ya export-ready, sin cambios necesarios

**Pendientes accionables:**
1. md: breakpoints en 17 páginas (#2) — usar ResponsiveTable, MobileFilterSheet, useBreakpoint del DS
2. Framer Motion selectiva (#9) — bento-fade-up stagger, stat-card-transition enter/exit

### D-B-01: GeoJSON inline, no tile server MVT
**Decisión:** El endpoint `/canvassing/geo` retorna GeoJSON FeatureCollection
completo en el response, construido en PostgreSQL con `jsonb_build_object` +
`jsonb_agg`. NO usa tile server MVT.
**Razón:** 9,723 puntos producen ~2-3MB de GeoJSON. MapLibre maneja esto
sin problema con clustering. Un tile server añade complejidad innecesaria
para este volumen.
**Umbral de migración (Gemini G2):** Si el import full (63K ciudadanos)
se ejecuta, >15K registros justifica migrar a `ST_AsMVT` de PostGIS.
**Trade-off:** Payload grande en mobile con conexión lenta. Aceptable
para MVP interno; mitigar con limit=2000 default.

### D-B-02: Endpoints geo en router canvassing existente
**Decisión:** `/canvassing/geo` y `/canvassing/geo-stats` se agregaron al
router `canvassing.py` existente, no en router nuevo.
**Razón:** Conceptualmente es canvassing (segmentación de campo). Los
endpoints legacy de rutas conviven sin conflicto de paths.

### D-B-03: Privacidad de nombres en mapa
**Decisión:** El GeoJSON retorna `nombre` como "J. Pérez" (inicial +
apellido) en la propiedad corta. El `nombre_completo` se incluye para
el popup al hacer click.
**Razón:** El mapa es visible para analyst + admin. Minimizar exposure
de datos en la vista general. PII (email, phone, clave electoral) nunca
sale en el GeoJSON.

### D-B-04: GeoJSON construido en PostgreSQL (Gemini G6)
**Decisión:** La query de `/canvassing/geo` construye el GeoJSON completo
en SQL usando `jsonb_build_object` y `jsonb_agg`. FastAPI solo actúa como
proxy (JSONResponse directo del scalar).
**Razón:** Evita deserializar 5,000 rows a Python, construir dicts, y
re-serializar a JSON. La DB lo hace en un solo pase. Reduce TTFB y CPU
del backend.

## 2026-04-11

### D-SPRINT3-01: Kanban sin drag-and-drop (usa botones)
**Decisión:** Implementar el tablero Kanban con botones "→" y "Completar" en lugar de drag-and-drop real (`@dnd-kit` u otro).
**Razón:** Agregar una dep nueva de frontend atrasa el scaffold y la UI funcional con botones ya cumple el criterio S3.7 del plan (movimiento entre 3 columnas + edición inline + captura de métrica). Drag-and-drop es UX nice-to-have, no requisito.
**Revertible:** Sí. Si CEO quiere dnd real, instalar `@dnd-kit/core @dnd-kit/sortable` y envolver los `Card` de `kanban-board.tsx`. Cero cambios de backend.

### D-SPRINT3-02: estructura_json como JSONB en planes_ia
**Decisión:** Guardar el plan estructurado tanto como JSONB (`planes_ia.estructura_json`) **como** denormalizado en `plan_tareas`.
**Razón:** JSONB permite recuperar el plan tal como lo generó el LLM (auditoría) sin tocar `plan_tareas` cada vez. `plan_tareas` es para queries rápidas y edición humana. Las dos fuentes divergen a propósito cuando el humano edita.
**Trade-off:** Se pierde la garantía estricta de sincronización entre `estructura_json` y `plan_tareas`. Aceptable: `estructura_json` se trata como "original inmutable", `plan_tareas` como "estado vivo".

### D-SPRINT3-03: Retry schema violation en plan_structured (max 2 retries)
**Decisión:** Si el LLM devuelve JSON que no cumple `PlanEstructurado`, reintentar hasta 2 veces concatenando el error de validación al prompt.
**Razón:** Gemma local tiende a olvidar constraints en outputs largos. Un retry con feedback explícito suele funcionar.
**Límite duro:** 3 intentos totales. Al 4º, se lanza `RuntimeError`. Caller decide si fallback a `generate_plan()` (no estructurado) o avisar al usuario.

### D-COORD-01: Multi-sesión requiere worktrees (reforzado por CEO 2026-04-11)
**Decisión:** Multi-sesión concurrente sobre el mismo repo NO puede operar en el mismo `cwd`. Precondición dura.
**Razón:** claude-peers-mcp es filesystem-shared. Git ops de un peer mueven HEAD para todos.
**Aplicado:** Peer qmmine5b se movió a `../crece-v2-sprint1-deuda` rama `sprint1-deuda` a medio sprint. Yo me quedé en `main` sin git ops hasta su confirmación.
**Regla viva en:** `~/.claude/CLAUDE.md` líneas 329-351.

## Deudas técnicas encontradas durante cross-review con peer n8n-mexico (2026-04-11)

### D-SEC-03: 21 endpoints siguen JWT-only (no aceptan X-API-Key)
**Hallazgo:** Durante el test end-to-end del paquete `@mdconsultoria-ti/n8n-nodes-crece`
(peer n8n-mexico uta4m297), el node `Buscar Ciudadano` recibió 401 "Not authenticated"
al hitar `/api/v1/ciudadanos/` con header `X-API-Key` válido.

**Root cause:** solo 4 endpoints (`alerts_integration.py`, `campaigns_integration.py`,
`content_factory_integration.py`, `crm_integration.py`) usan `get_current_user_or_api_key`.
Los otros 22 usan `get_current_user` (JWT-only), históricamente nunca actualizados tras
el sprint "Fase 2 Integration" (commit `a67032f`) que introdujo el dual-auth Depends.

**Fix parcial aplicado (PR #5):** `ciudadanos.py` migrado a dual auth. Los otros 21 quedan
como deuda: `canvassing.py`, `planes.py`, `dashboard.py`, `social.py`, `voter_scoring.py`,
`benchmark.py`, `campanas.py`, `contenido.py`, `dirigentes.py`, `electoral.py`,
`encuestas.py`, `eventos.py`, `geo.py`, `metricas_sociales.py`, `organizaciones.py`,
`osint.py`, `participacion.py`, `programas.py`, `blindaje.py`, `bot_detection.py`,
`webhooks_integration.py`.

**Fix propuesto (recomendación del peer en ADR-011 de n8n-mexico):** middleware que
inyecte `request.state.user` antes de la resolución de Depends. Single point of change
en lugar de 22 swaps por endpoint. Cirugía más profunda pero mucho más robusta contra
regresiones futuras.

**Linkeado a:** ADR-011 n8n-mexico (autoridad para el impacto en workflows n8n).

### D-DX-01: seed.py no bootstrea organización → /api-keys 500 en dev fresh
**Hallazgo:** El seed del dev DB crea users con `org_id=NULL` y cero rows en la tabla
`organizaciones`. El endpoint `POST /api/v1/api-keys` revienta con `NotNullViolationError`
al intentar persistir `ApiKey.org_id = current_user.org_id = NULL`.

**Reproducción:** `make reset-db && make seed && curl -X POST /api/v1/api-keys → 500`.

**Fix en runtime (NO en código, solo al dev DB local) durante sesión:**
```sql
INSERT INTO organizaciones (nombre, slug, tipo) VALUES ('Movimiento Ciudadano CDMX', 'mc-cdmx', 'PARTIDO');
UPDATE users SET org_id = 3 WHERE org_id IS NULL;
```

**Fix pendiente en código:** agregar a `backend/scripts/seed.py` la creación de una
organización MC CDMX por default y asignar todos los users del seed a ella.

### D-OBS-01: IntegrityError devuelve "Internal Server Error" plano en lugar de 409 JSON
**Hallazgo:** Cuando el endpoint `/api-keys` falló con `NotNullViolationError` (D-DX-01),
FastAPI devolvió un string literal `"Internal Server Error"` en el body en lugar del
típico JSON `{"detail": "..."}`. Esto complicó el debugging del peer — no tenía
stacktrace ni tipo de error estructurado.

**Fix propuesto:** exception handler global en `backend/app/main.py`:
```python
@app.exception_handler(sqlalchemy.exc.IntegrityError)
async def integrity_error_handler(request, exc):
    return JSONResponse(
        status_code=409,
        content={"detail": "Database integrity violation", "error": str(exc.orig)},
    )
```

Con esto los clientes HTTP (n8n, Postman, frontend) reciben un 409 JSON accionable
en lugar de un 500 string plano.

### D-INFRA-01: Tunnel Cloudflare quick efímero rompe credenciales n8n en cada reinicio
**Hallazgo:** El dev backend está expuesto vía `cloudflared tunnel --url http://localhost:8002`
que asigna un nombre aleatorio (`musicians-oregon-judge-angela.trycloudflare.com` hoy,
otro nombre mañana). La credencial `CRECE account` en n8n prod tiene la URL Base
hardcoded → cada reinicio del tunnel rompe todos los workflows del peer.

**Workaround del peer:** documentado en su `.context/BLOCKERS.md` B-005 — rotar
manualmente la URL en Settings → Credentials cuando se detecte el break.

**Fix permanente (bloqueado por Carlos Amador, admin Coolify):**
- **Opción A:** tunnel nombrado Cloudflare con cuenta + DNS CNAME propio (ej.
  `api-crece-dev.mdconsultoria-ti.org`). ~15 min de setup.
- **Opción B:** deploy del backend CRECE a Coolify con dominio estable
  (`api-crece.mdconsultoria-ti.org`). Ruta oficial del plan original.

Ambas requieren Carlos. Escalar junto con D-SEC-02 (permissions enforcement) y
el pending de `seed.py` como paquete de "infra para producción real".

## 2026-04-11 — Sprint 4 kickoff

### D-S4-01: S4.1 usa GeoJSON INEGI redistribuido, no shapefile directo
**Decisión:** El catálogo `alcaldias_cdmx` se cargó desde
`github.com/PhantomInsights/mexico-geojson/2023/states/Ciudad de México.json`
(cacheado en `backend/data/raw/`), que redistribuye el Marco Geoestadístico INEGI 2023
como GeoJSON preservando CVEGEO/CVE_ENT/CVE_MUN/NOMGEO originales.
**Razón (opción 1 del plan aprobada por CEO):** contenido idéntico al shapefile oficial
INEGI, pero evita agregar `geopandas`+`fiona` a la imagen Docker (~200MB). Solo usa
`shapely` (ya instalado) + `httpx` + stdlib json. Seed idempotente, offline después del
primer fetch.
**Verificación:** 16/16 alcaldías insertadas. `ST_Contains` probado contra Zócalo
(Cuauhtémoc), Del Valle (Benito Juárez), Polanco (Miguel Hidalgo) — todos correctos.

### D-S4-02: Orden S4.2 = `a → c → b` (modelo → RLS → HNSW)
**Decisión:** Al crear `topic_trends`, se activa la policy RLS sobre `org_id` **antes**
de crear el índice HNSW, no después.
**Razón (cross-audit Gemini 2026-04-11):** RLS-first evita ventanas de fuga entre orgs
durante ingesta inicial. Además, HNSW requiere `maintenance_work_mem` alto (≥512MB)
para vectores de 384 dims — configurar antes del CREATE INDEX.
**Trade-off:** Ninguno funcional. Solo cambia el orden de operaciones.

### D-S4-03: S4.8 audit RLS va DESPUÉS de S4.2b, no en el día 1
**Decisión:** El audit "find_similar_posts filtra org_id antes del HNSW knn" se ejecuta
después de que el índice HNSW exista.
**Razón (cross-audit Gemini):** no se puede auditar comportamiento del planner contra un
índice que no existe. EXPLAIN ANALYZE requiere el plan real.
**Reemplaza:** El orden del plan original que listaba S4.8 como dependencia blando de
S4.5 sin aclarar timing.

### D-S4-04: location_inference necesita normalize_social_text() antes del NER
**Decisión:** Agregar un pre-processor `normalize_social_text(content)` que strippea
emojis, convierte `@handles` a placeholder, expande `#hashtags` a tokens, colapsa
whitespace. Se corre **antes** de pasar el texto a spaCy `es_core_news_md`.
**Razón (cross-audit Gemini):** spaCy baja precisión drásticamente con texto social crudo.
**Impacto:** S4.4 gana una subtarea (S4.4a.5) pero mantiene el target 60-70% precisión.

### D-S4-05: RLS en topic_trends NO incluye `org_id IS NULL` bypass
**Decisión:** A diferencia de las tablas existentes (dirigentes, users, etc.),
la policy de `topic_trends` NO tiene `org_id IS NULL OR ...`. Solo
`org_id::text = current_setting('app.current_org_id', true)`.
**Razón:** Los trends son siempre tenant-scoped. NO hay trends "compartidos"
entre organizaciones. El NOT NULL en la columna previene el caso NULL.

### D-S4-06: crece role es superuser/bypassrls en dev DB (tests RLS requieren rol secundario)
**Hallazgo:** Al verificar la policy de `topic_trends`, queries bajo `crece`
con `SET app.current_org_id='4'` seguían viendo rows de `org_id=3`.
**Root cause:** `SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname='crece'`
devuelve `t | t`. FORCE ROW LEVEL SECURITY no aplica a superusers ni a
BYPASSRLS.
**Consistencia con D16:** Ya asumido — "el enforcement principal es en los
endpoints FastAPI". La RLS DB es defense-in-depth.
**Verificación S4.2c:** Creado rol `rls_test NOLOGIN NOSUPERUSER NOBYPASSRLS`,
`SET ROLE rls_test` + `SET app.current_org_id='3'` + insert, luego
`SET app.current_org_id='4'` + select → 0 rows. Policy funciona.
**Pendiente prod:** La app en Coolify debe conectarse con un rol sin
BYPASSRLS (no el owner del schema).

### D-S4-07: RSS persistence diferida — parser en memoria por ahora
**Decisión:** `news_ingest.fetch_all_feeds()` retorna RssItem en memoria
sin persistir a `social_posts`. El worker `ingest_rss_feeds` solo loguea
el count.
**Razón:** Persistir con `platform='NEWS'` requiere 2 cambios fuera de scope:
1. Migración `platform_enum += 'NEWS'`
2. Hacer `social_posts.profile_id` nullable, O crear 1 perfil sintético
   por feed RSS (`news:presidencia`, `news:gaceta`, etc.) con un
   dirigente sintético placeholder.
**Consecuencia:** El clustering de trends ignora fuentes RSS por ahora.
Próxima iteración debe decidir la ruta (nullable vs synthetic profiles)
antes de wire el parser al worker detect_trends.

### D-S4-08: clustering real por HNSW requiere backfill previo
**Decisión:** El primer pase de `detect_trends` agrupa solo por
`alcaldia_id` match literal del nombre en el texto normalizado, sin
usar el HNSW index de topic_trends.
**Razón:** `social_posts.embedding` está 0/381 backfilled. Ejecutar
`backfill_embeddings()` carga sentence-transformers (~2GB download del
modelo multilingual MiniLM) y procesa los 381 posts — esfuerzo fuera
del budget de esta sesión.
**Próximo paso:** correr `embed_batch()` una vez con el modelo cached,
luego wire detect_trends para usar HNSW cosine similarity sobre embeddings
reales en vez del match literal.

### D-S4-04: spaCy es_core_news_md scaffold, no instalado
**Decisión:** `location_inference` NO usa spaCy NER todavía. El matching
se hace vía search literal de nombres de alcaldía + tabla de colonias
hardcoded (~20 entradas).
**Razón:** `python -m spacy download es_core_news_md` pesa ~50MB y
requiere rebuild del container o `pip install` live + persistir en
Dockerfile. Diferido para después del primer deploy del worker.
**Precisión actual:** ~60% en el test suite (10/10 tests incluyen casos
fáciles). Target MVP del plan era 60-70%; se cumple sin spaCy.

## 2026-04-11 — D-DATA-01 Ruta C (import CRECE legacy)

### D-DATA-02 (resuelta parcialmente): PII at-rest con pgcrypto + audit log
**Decisión:** Encriptación at-rest de campos PII críticos en `ciudadanos_legacy`
usando `pgcrypto.pgp_sym_encrypt` con key simétrica `PII_ENCRYPTION_KEY`
desde `settings`. Audit trail mediante tabla `data_access_log` y dependency
FastAPI `require_pii_clearance`.

**Scope ejecutado (2026-04-11):**
1. **Migración `f6a7b8c9d0e1`**:
   - Columnas nuevas en `ciudadanos_legacy`: `clave_electoral_enc`, `email_enc`,
     `phone_01_enc`, `phone_02_enc`, `whatsapp_enc`, `fecha_nacimiento_enc`
     (todas `bytea`, nullable)
   - Tabla `data_access_log` (user_id, org_id, table_name, row_id, action,
     fields[], metadata_json, request_ip, user_agent, created_at) con RLS
     policies y 5 índices
2. **Servicio `app.services.pii`**:
   - `encrypt_value` / `decrypt_value` con pgp_sym_encrypt/decrypt vía bind
     params (la key nunca sale de Python — llega como parámetro SQL, no
     inline en logs)
   - `backfill_ciudadano_legacy` idempotente (solo procesa rows con
     `*_enc IS NULL AND clear_col NOT NULL`)
   - `read_pii_fields` descifra N campos por ciudadano en 1 query
3. **Dependency `app.core.pii_access.require_pii_clearance`**:
   - Gate por `Role.ADMIN` (no viewer, no analyst, no field_operator)
   - Inyecta `PiiAuditor` con contexto del request (user_id, org_id, IP, UA)
   - Loggea `access_attempt` al pasar, el endpoint DEBE llamar
     `auditor.log(action="read_pii", fields=[...], row_id=...)`
4. **Endpoint `/ciudadanos-legacy`** (D-DATA-02 demo):
   - `GET /` — listado SAFE (sin PII), admin/analyst pueden leer
   - `GET /{id}/pii` — descifra PII, gated por `require_pii_clearance`
5. **`PII_ENCRYPTION_KEY` persistida en `backend/.env`** (gitignored)
   con valor dev `dev-crece-pii-key-2026-min32chars!`
6. **Backfill ejecutado**: 675 emails + 2,625 phone_01 + 945 phone_02 +
   7,763 whatsapps + 1,312 fechas nacimiento + 1 clave electoral encriptados

**Verificación:**
- Tests: `tests/test_pii_encryption.py` — 6/6 verdes
  - Round-trip encrypt/decrypt
  - Empty plaintext returns None
  - Wrong/corrupt ciphertext returns None (no crash)
  - read_pii_fields sobre row real descifra email
  - Backfill idempotente (2a corrida = 0 rows afectadas)
  - PiiAuditor.log inserta correctamente en data_access_log
- Smoke test live:
  - Admin → GET /pii devuelve 200 con email descifrado
  - Viewer (Piña) → GET /pii devuelve **403 Forbidden**
  - Audit log muestra 2 entries (access_attempt + read_pii) post-admin
  - NO hay entry para el viewer rechazado (HTTPException aborta antes del commit)
- Total tests S4+S5+compliance: **23/23 verdes**

**Deudas remanentes de D-DATA-02 (no bloqueantes):**
- **D-DATA-02a**: Scripts de right-to-delete (LFPDPPP artículo 32). Sólo
  scaffold; endpoint DELETE /ciudadanos-legacy/{id}/gdpr-erase requiere
  CASCADE a data_access_log y flag `deleted_at` en vez de drop físico.
- **D-DATA-02b**: Rotación de la key PII. `scripts/rotate_pii_key.py`
  descifra con key-vieja y re-encripta con key-nueva. Crítico antes de
  cualquier incidente de seguridad en la key actual.
- **D-DATA-02c**: Dropeo de las columnas en claro de `ciudadanos_legacy`
  (`email`, `phone_01`, ..., `clave_electoral`). Actualmente coexisten
  con las `_enc`. Una vez que ningún código consumidor lee las columnas
  en claro, otra migración las dropea.
- **D-DATA-02d**: Extender la dependency + backfill a otros campos PII
  de otras tablas (`ciudadanos` v2 si llega a poblarse, `users.email`
  probablemente NO porque es credential de login).
- **D-DATA-02e**: Loggear los accesos FALLIDOS (403). Hoy el HTTPException
  del dependency aborta antes del commit, así que queda sin huella.
  Refactor: usar un try/except en el dependency que loggee antes de
  lanzar.

### D-DATA-01: Import CRECE Oracle APEX legacy — Ruta C (3 alcaldías piloto)
**Decisión:** Importar el snapshot del CRECE Oracle APEX original al dev DB
filtrado a las 3 alcaldías piloto del plan S4 (Cuauhtémoc, Benito Juárez,
Miguel Hidalgo). master_catalogo completo (sin PII), ciudadanos +
promotores solo piloto.

**Razón:** Balance entre velocidad de ejecución y minimización de
superficie PII. Ruta A (import full) expondría 63K ciudadanos sin
compliance previo. Ruta B (compliance-first) toma ~45 min antes de
cualquier valor. Ruta C da valor inmediato con PII focalizado y
mantiene el trabajo de compliance como deuda explícita.

**Alcance ejecutado:**
- `unidades_territoriales`: 5,552 filas (16 alcaldías CDMX, sin PII)
- `promotores_legacy`: 45 filas (3 alcaldías piloto)
- `ciudadanos_legacy`: 9,723 filas (Cuauhtémoc 6,643 + MH 2,267 + BJ 813)
- 99.9% mapeados a `unidad_territorial_id` via sección electoral
- >96% con coordenadas GPS reales

**Decisiones técnicas:**
1. **Tablas paralelas `*_legacy`** en vez de forzar import sobre `ciudadanos`/`users` v2:
   - v2 tiene enums NOT NULL (`edad_rango`, `genero`, `nivel_interes`)
     que no caben con los free-text del Oracle APEX
   - v2 `ciudadanos.seccion_id` FK a `secciones_electorales` (tabla vacía)
   - v2 `users.hashed_password` NOT NULL — passwords Oracle son inútiles
   - Preservación 1:1 del snapshot legacy facilita auditoría y roll-forward futuro
2. **RLS estricta desde el día 1** en ambas tablas legacy — sin bypass NULL,
   `org_id` NOT NULL default=3 (MC CDMX root)
3. **Columna `raw_data JSONB`** en ciudadanos_legacy para campos no mapeados (reserva futura)
4. **Idempotente via UPSERT** por `legacy_id` / `legacy_user_id`
5. **Import gated por `CRECE_MC_RAW_DIR`** env var — el script falla con error
   explícito si la variable no está seteada. CSVs en `backend/data/raw/mc_original/`
   **gitignored**.

**Hallazgos durante import:**
- **BJ tiene data muy rala**: 813 ciudadanos vs 6,643 de Cuauhtémoc (8×).
  Si se demuestra la UX sobre BJ, considerar añadir Venustiano Carranza
  (10,835 ciudadanos) como alcaldía piloto adicional.
- **CSV tiene corrimiento de columnas**: phones caen en columna EDAD.
  Mitigado con `_parse_age()` que valida rango 0-120.
- **MUNICIPIO texto libre** en el CSV, mucha duplicación de mayúsculas.
  El mapeo canónico se hace via `SECCION → master_catalogo.ALCALDIA_2024`.

**Deudas documentadas para futuro:**
- **D-DATA-02**: Compliance LFPDPPP real — encriptación at-rest de PII
  vía `pgcrypto` (extensión ya instalada), audit trail `data_access_log`,
  scripts de "right to delete". Obligatorio antes de cualquier deploy
  prod. Bloqueante para exponer estas tablas en el frontend.
- **D-DATA-03**: Reconciliación ciudadanos_legacy ↔ v2 `ciudadanos`.
  Propuesta: view materializada o job nocturno que copie rows
  mapeables (con enums válidos) a la tabla v2. Mientras, usar solo
  la tabla legacy para queries de voter scoring / canvassing.
- **D-DATA-04**: Datos faltantes — el CSV no tiene password v2 usable,
  email en 5% de ciudadanos, phone en 37%. Los promotores requieren
  forced password reset cuando se wire con v2 `users`.

**Valor inmediato desbloqueado:**
- Voter scoring real sobre 9,723 ciudadanos con lat/lon
- Canvassing geo con unidades territoriales, volatilidad y estrato socioeconómico
- Integración trends detector → filtro por alcaldía + unidad territorial
  (más fino que el literal-match S4.4a actual)
- Promotores reales para el wizard S5 en vez de usuarios sintéticos

### D-S5-02: auto-login post-onboarding = redirect simple (no token handoff real)
**Decisión:** Al completar el chain de onboarding, el wizard NO genera un
nuevo JWT para el dirigente creado ni hace login automático como él. En
su lugar, redirige al admin a `/dashboard/dirigentes?highlight={id}`.
**Razón:** El JWT handoff real requiere un endpoint dedicado
`POST /auth/impersonate` que solo admins puedan usar, con audit trail.
Es el tipo de feature que merece un PR propio con tests de seguridad.
El redirect simple cumple el criterio funcional del wizard ("admin
termina el wizard y puede ver al dirigente nuevo") sin abrir superficie
de seguridad nueva.
**Trade-off:** El plan original S5.5 pedía "admin auto-logged-in como
el nuevo dirigente" — eso queda como deuda D-S5-03 para cuando se
diseñe el flujo de impersonación con compliance.

### D-S5-01: S5.3a retorna sync_status=pending inmediatamente
**Decisión:** El endpoint transaccional `POST /dirigentes/onboard` crea User+Dirigente+
SocialProfile y retorna 201 con `{..., sync_status: "pending", task_id: "..."}` sin
esperar al celery chain.
**Razón (cross-audit Gemini):** permite al wizard UI mostrar el dirigente creado
inmediatamente y comenzar el polling de `/onboarding-progress` sin bloquear la UI.
**Impacto:** Migración de S5.3a agrega columna `dirigentes.sync_status ENUM(pending,
scraping, analyzing, ready, error)`.

## 2026-04-03

### D1: Multi-tenant via RLS (no schema-per-tenant)
- org_id FK en tablas principales + PostgreSQL RLS policies
- `current_setting('app.current_org_id')` per-transaction
- Razón: menor complejidad operativa, funciona bien hasta ~100 organizaciones

### D2: WhatsApp via Chatwoot-MX (nunca directo)
- Campañas solo preparan payload, Chatwoot-MX hace delivery
- Webhooks bidireccionales: CRECE → Chatwoot (enviar), Chatwoot → CRECE (status)
- Razón: Chatwoot ya tiene WABA conectada y gestión de conversaciones

### D3: Voter Scoring con fallback rule-based
- scikit-learn RandomForest cuando hay datos suficientes
- Fallback determinista (50 ± bonuses/penalties) cuando no hay modelo entrenado
- Razón: el sistema debe funcionar desde día 1 sin datos de entrenamiento

### D4: Content Factory con etiqueta IA obligatoria
- Toda generación auto-appends "Contenido generado con IA"
- campo etiqueta_ia siempre True, modelo_ia siempre poblado
- Razón: compliance INE obligatorio para contenido político generado por IA

### D5: PostGIS canvassing con nearest-neighbor heuristic
- No TSP solver externo (demasiado complejo para MVP)
- Nearest-neighbor con ST_Distance + recursive CTE
- Razón: suficiente para rutas de 20-30 puntos en zonas urbanas CDMX

### D6: Docker port 5438 para desarrollo
- PostgreSQL local ocupa 5432, Docker PostGIS en 5438
- .env en backend/ (no project root) por pydantic-settings strict mode
- Razón: coexistencia con otros proyectos MD en la misma máquina

### D7: Alembic exclude PostGIS tiger tables + spatial indexes
- include_object() filtra tablas tiger/geocoder del autogenerate
- Spatial indexes (gist) excluidos porque GeoAlchemy2 los crea automáticamente
- Razón: evita DROP/CREATE innecesarios en cada autogenerate

### D8: API returns lowercase enum keys (2026-04-05)
- platform_scores, scraper tasks, filter params use lowercase ("twitter" not "TWITTER")
- Social endpoint accepts case-insensitive query params (platform, sentiment)
- Razón: REST API best practice, frontend-friendly, tests más legibles

### D9: Dashboard overview uses proxy IPD (2026-04-05)
- GET /dashboard/overview calcula avg_ipd como proxy (avg_platforms/6 * 10)
- No ejecuta diagnostico completo por dirigente (costoso en O(n*m) queries)
- Razón: suficiente para overview card, detalle real en /dirigentes/{id}/diagnostico

### D10: Docker ports CRECE dev (2026-04-05)
- PostgreSQL: 5438, Redis: 6383, MinIO: 9006/9007, Backend: 8002, Frontend: 3001
- Razón: coexistencia con 40+ contenedores de otros proyectos MD en misma máquina

### D11: Scrapers — librerías obligatorias, no código custom (2026-04-05)
- Patrón de resiliencia: Librería probada → Custom fallback → Apify
- Instagram: instaloader (requiere auth en 2026)
- Twitter: twscrape (requiere cuentas auth)
- Facebook: facebook_page_scraper (bug selenium-wire, evaluar alternativa)
- YouTube: scrapetube (FUNCIONA sin API key, validado con datos reales de Piña)
- TikTok: TikTok-Api v7.3.2 (Playwright)
- Razón: CEO detectó que se escribió código custom en vez de usar librerías del plan original

### D12: Ollama modelo gemma3:12b (2026-04-05)
- Default cambiado de gemma4:27b a gemma3:12b
- Razón: VPS Coolify tiene 16GB RAM, ~8GB disponibles. 27b no cabe. 12b sí.
- Se puede override vía .env: OLLAMA_MODEL=gemma3:27b

### D13: Ollama timeout 600s para Content Factory (2026-04-05)
- httpx timeout en content_factory.py aumentado de 300s a 600s
- Razón: con prompt completo (dirigente context + constraints), gemma3:12b CPU-only tarda ~480s
- Streaming disponible como alternativa para UX

### D14: Voter Scoring — datos sintéticos INEGI Census 2020 (2026-04-05)
- 200 ciudadanos con data_source='synthetic_census_2020'
- Distribuciones basadas en INEGI Censo 2020 CDMX (edad, género, escolaridad, alcaldía)
- NUNCA confundir con datos reales — campo data_source es obligatorio
- RF accuracy=1.0 es esperado en datos sintéticos; con datos reales será menor
- Script idempotente: backend/scripts/seed_synthetic_citizens.py

## 2026-04-11 — Sprint 1 Saneamiento

### D16: RLS enforcement vía user.dirigente_id en endpoints (2026-04-11)
- Aunque existe migración `77bbd5e5f495` con políticas RLS a nivel DB, el enforcement principal es en los endpoints FastAPI vía `current_user.dirigente_id` check
- `org_id` en users y dirigentes está en None para los 3 demo users (single-org CRECE)
- El DB-level RLS es defense-in-depth; cuando se agregue multi-tenancy real (Sprint 5 wizard), habrá que poblar org_id correctamente
- Verificado: Piña ve 191 posts, Solano 190, admin 381 (split perfecto)

### D17: KpiOverviewResponse extendido con campos políticos (2026-04-11)
- Campos legacy (total_dirigentes, avg_ipd_score, posts_monitored_24h, active_alerts, *_change) se mantienen para backward compat
- Nuevos campos: total_audiencia (sum followers), contactos_periodo (CRM en window), tema_urgente (texto de alerta más reciente o None)
- contactos_periodo y tema_urgente tienen try/except para degradar grácilmente si las tablas no existen
- Razón: evita romper consumers legacy mientras se habilitan métricas del político

### D18: Period parameter en /dashboard/overview (2026-04-11)
- Literal["today", "7d", "30d", "90d"] con default "30d"
- Calcula window_start y prev_window_start dinámicamente
- Legacy name `last_24h` se mantiene internamente pero ahora tracks el period
- Razón: activeFilter del frontend estaba roto porque nunca llegaba al backend

### D19: NLP reprocess reemplaza scores del seed (2026-04-11)
- `backend/scripts/reprocess_nlp.py --force` sobrescribe sentiment_score/sentiment_label/emotions
- Seed inicial tenía valores canned (0.7/0.5/0.1) — ahora son scores reales de pysentimiento
- Razón: filosofía "cero mockups" requiere que incluso el demo tenga análisis real
- Side effect: los tests que asumían los valores canned pueden fallar — a revisar en Sprint 2

### D20: Frontend sentiment_label es string | null (2026-04-11)
- Tipado `SocialPost.sentiment_label: string | null` (antes `sentiment: SentimentType`)
- `SentimentBadge` acepta `string | null | undefined` y normaliza con `.toLowerCase()`
- Bug previo: frontend leía `post.sentiment` que no existía en response → `else neutral++` siempre
- Razón: el backend siempre devolvió `sentiment_label` en mayúsculas; el frontend tenía un tipo inventado

---

### D15: Bot detection pattern-based, no ML (2026-04-05)
- Servicio basado en heurísticas, no ML (no hay dataset de bots mexicanos)
- 3 analizadores: username, profile metadata, post patterns
- Threshold: ≥0.70 = likely_bot, ≥0.40 = suspicious, <0.40 = human
- Razón: para MVP, heurísticas son suficientes y explicables. ML requiere labeled data.

---

## D-NLP-01: Framework político de 3 capas (2026-04-13)

**Contexto:** CEO + Gemini alinearon diseño de clasificación de sentimiento político.

**Decisión:** Arquitectura de 3 capas con guardrails:
1. NLP técnico (pysentimiento + Cardiff + Citizenlab) — determinista
2. LLM contextualizado (Gemma3:12b) — clasifica tono + target SIN emitir juicio
3. Framework político rule-based CONFIGURABLE por tenant — emite sentiment_politico_ajustado

**Guardrails:**
- Rangos acotados: cada celda puede moverse ±1 del default
- Audit log en `framework_audit_log`
- UI siempre muestra "Tu score" (config) + "Score estándar" (defaults)
- Solo admin_org y admin_MD pueden editar

**Defaults iniciales:** escala suave +1/-1/0 (no +2/-2) según recomendación Gemini.

**Razón:** evita incentivos perversos, transparencia radical, honesto sobre límites.

## D-NLP-02: Defaults asumidos por Claude (2026-04-13, CEO dijo "continuar" sin detallar)

Los 4 votos conservadores que propuse se asumen como aprobados:
1. Defaults matriz = **+1/-1/0 (escala suave)** — Gemini recommendation
2. Validación externa con encuestas públicas = **deuda v2**, solo documentar ahora
3. Quién edita matriz = **admin org + admin MD solamente**
4. Matriz rule-based ahora + LLM fine-tuned = **deuda v2**

**Razón:** CEO autorizó continuar sin modificaciones, mis votos son conservadores y reversibles.

## D-NLP-03: Orden de ejecución (2026-04-13)

A (setup) → B (endpoints fix) → D.0 (framework schema) → C (analyze_full batch bg) + D.1 (LLM contextual bg) → E (charts-lab) → F (dashboard integration) → G (cierre)

**Razón:** B primero por impacto/tiempo inmediato. Framework D.0 antes de D.1 porque define target categories. C y D.1 paralelizables en background.

## D-NLP-04: Colapso Layer 2+3 en Gemma contextualizado (2026-04-13)

**Cambio:** La "matriz rule-based" deja de ser capa de cálculo. Se convierte en **referencia publicada editable** que se inyecta como contexto en el prompt de Gemma3:12b.

**Arquitectura final:**
- Layer 1: NLP técnico (pysentimiento, Cardiff NLP, Citizenlab) — determinista
- Layer 2 COLAPSADA: Gemma3:12b recibe (post + rol_dirigente + matriz_efectiva_tenant + contexto_politico) → emite (tono, target, score_politico, razón) en un solo paso

**Mantiene:**
- Matriz editable por tenant (`framework_overrides_org`)
- Audit log de cambios
- UI dos columnas (score tenant vs score default) — calculando default también con Gemma usando matriz default en el prompt

**Elimina:**
- No hay paso "matriz SQL calcula score"
- No hay branching "si matriz cubre el caso devuelvo X, si no devuelvo 0"

**Roadmap v2 (no deuda):** Cuando se acumulen 500+ posts con output validado por CEO/analystas, entrenar LoRA sobre BETO con ese corpus. Reemplaza Gemma por modelo determinista más rápido.

**Razón CEO:** "no quiero deuda técnica" sobre LLM. Colapsar en Gemma con in-context learning es equivalente pragmático sin re-entrenar un modelo ahora.

## D-NLP-05: Validación externa opción B (2026-04-13)

**Decisión:** Implementar comparador sentiment CRECE vs encuestas públicas, con alerta en dashboard cuando divergencia > 30%.

**Fuentes:** Oraculus (agregador), Parametría, Enkoll, Mitofsky, Reforma, El Financiero
**Granularidad:** Ancla en contexto — encuestas de aprobación del gobierno del ámbito (Sheinbaum federal, Brugada CDMX, Jara Oaxaca) — no encuestas de cada dirigente.
**Tabla:** `encuestas_publicas` (fuente, fecha, ámbito, actor, metrica, valor_pct)
**UI:** Badge en dashboard overview "Atención: score diverge ${pct}% vs tendencia encuestas"

---

## 2026-04-14 — Índice de Aceptación (IA) MVP

**D-IA-01: Stack scraping para comments = Brightdata**
- Descubrimiento: ya había BRIGHTDATA_API_KEY + CRAWLBASE + SCRAPERAPI en `.env.scraping-keys` (commit fc18c8a integró Brightdata FB).
- Bot detection en TikTok/YouTube desde Docker ≠ problema con Brightdata (proxies residenciales suyos).
- Datasets identificados: `gd_lkf2st302ap89utw5k` (TT), `gd_lkay758p1eanlolqw8` (FB), `gd_ltppn085pokosxh13` (IG), `gd_lk9q0ew71spt1mxywf` (YT).
- Costo: free tier Brightdata cubre MVP.

**D-IA-02: LFPDPPP compliance — author_hash SHA256**
- social_comments guarda `author_hash = SHA256(platform:commenter_id:salt)` no PII crudo.
- Permite tracking mismo autor entre posts sin almacenar identificadores personales.
- Cumple minimización de datos. Pendiente: actualizar Aviso de Privacidad CRECE con finalidad "análisis estadístico político agregado".

**D-IA-03: 3 capas IA viables free**
- Aprobación: (pos_comments + celebratorio + solidario) / total — viable todas plataformas
- Rechazo: (neg_comments + ataque + critico) / total — viable todas
- Expansión: % authors nuevos vs históricos — viable con datos acumulados
- Activación (followers vs engagers) y Fantasmas (seguidores dormidos) → no viable free, requiere tokens Business Meta o Twitter API Pro

**D-IA-04: Framework comments = pysentimiento + reglas keyword + matriz política**
- Costo $0 (todo local)
- Script: `backend/scripts/nlp_comments_batch.py`
- Keywords por tono (critico/ataque/propositivo/solidario/celebratorio/informativo/personal) + target (gobierno/oposicion/ciudadania/autopromocion/medios/tema_especifico)
- Polaridad -1/0/+1 derivada de sentiment + tono

---

## 2026-04-14 06:30 — Sprint /sprint-implement multiple (Sprints B+C+IA-2+D+P+X)

**D-SI-01: Arquitectura DIAGNOSTICO → PLAN v3 grounded**
- Tipo DIAGNOSTICO en planes_ia almacena FODA + KPI baseline + estructura_json
- Plan v3 CONSOLIDACION deriva tareas via `derive_tareas_from_foda()` 
- Cada tarea v3 tiene `fundamento_foda` en cambios_historial — trazabilidad
- Migración suave: v2 marcado `superseded_by_v3`, v3 con `supersedes_plan_ids[]`

**D-SI-02: LFPDPPP endpoints públicos**
- GET /api/v1/legal/privacidad devuelve metadata del aviso
- POST /api/v1/arco/exercise acepta acceso/cancelación/oposición con hash SHA256
- Cron diario `cleanup_old_comments` borra social_comments >180d
- Aviso de Privacidad completo en docs/AVISO-PRIVACIDAD-CRECE.md

**D-SI-03: IA UI widget con confidence banding**
- IndiceAceptacionCard: stacked bar + tonos + confidence low/medium/high
- IASummaryCard: top aprobación/rechazo del dirigente
- Post-normalización rol político pendiente Sprint siguiente

**D-SI-04: Sprint B comments scale pending Brightdata**
- Scraper batch corriendo background 8+ min sin output visible
- Brightdata snapshot queue lenta con múltiples URLs simultáneos
- 200 comments Piña TikTok ingestados (Sprint IA-1 original)
- Expansión 6×4 pendiente — script idempotente, se puede re-correr

---

## 2026-04-23 — Sprint 23 · Post-review CEO 11 screenshots (piloto activo)

**Origen:** `/sprint-review` + `/sprint-implement` sobre diagnóstico `DIAGNOSTICO-SCREEN-CRECE.md`.
Gemini cross-audit: `GEMINI-AUDIT.md`. Plan revisado: `PLAN-REVISADO.md`.
Todos los sprints ejecutados en branch `hotfix/23a-ui-puros` (4 commits).

**D-23-A (reclasificación Gemini — ejecutado):**
F-23-10 (Tier 1 copy) y F-23-11 (Tier 2 copy) reclasificados de §9.8 a 🟡 CALIB.
Razón: cambios tocan solo títulos + descripciones visibles, no fórmulas, umbrales
o campos BD. Ejecutado parcialmente: rename de 8 bloques Tier 1 + 5 bloques Tier 2
+ rewrite del contexto académico. Rewrite estructural del patrón "qué mide / cómo
te fue / qué hacer" documentado como propuesta 4-fases en `SPRINT-23D-COPY-PROPOSAL.md`
para sprint 24+.

**D-23-B (metodología link — pendiente CEO):**
Link "Metodología completa" renombrado a "Detalle técnico" y sigue apuntando al
archivo Zenodo de GitHub. Pendiente decisión: (a) página pública breve, (b) doc
interno restringido, (c) eliminar. Default temporal: mantener apuntando al repo.

**D-23-C (referencias académicas — ejecutado parcialmente):**
Eliminadas referencias "(Brookings)", "(Plutchik)", "(ITESO/DFRLab)", "MASTER §3.1"
del visible UI. Mantenidas en código y metodología técnica como sello académico
interno. Si CEO pide eliminación completa, queda documentado el trade-off credibilidad
vs simplicidad.

**D-23-D (plurinominales Electoral tab — ejecutado con default):**
Default aplicado: mostrar empty state diferenciado según `dirigente.cargo`. Si incluye
"plurinominal" → mensaje específico. Si no → mensaje genérico. CEO puede revertir a
ocultar tab si el default no convence.

**D-23-E (F-23-05 URL backend — ejecutado P1, P2/P3 quedan §9.8):**
Propuesta P1 (URL computada en schema sin migration) ejecutada:
- Nuevo `backend/app/utils/social_urls.py` con 8 plataformas mapeadas.
- `SocialPostResponse` extendido con `url`, `platform`, `dirigente_nombre`.
- `/social/posts` endpoint join a `SocialProfile` + `Dirigente` para poblar campos.
Propuestas P2 (columna `url` persistida) y P3 (nullable counters para distinguir
0-real vs no-recolectado) documentadas para §9.8 del 2026-05-20.

**D-23-F (F-23-03/04 — ejecutado sin backend):**
Revelación en Sprint 23-B investigation: backend endpoint `/social/sentiment-timeline`
ya acepta `platform` e `include_rts`. Wired up en frontend: hook `useSentimentTrend`
extendido + toggles en Tono Discursivo card del dashboard. Cerrado como 🟡 CALIB.

**D-23-G (motor sentimiento con afiliación — propuesta §9.8):**
F-23-01 + F-23-06 son 🔴 ESTRUCTURAL. Framework político de 3 capas ya existe en
`backend/app/services/political_framework.py` (D-NLP-01, commit 118ce13) con matriz
(rol, tono, target) → score_tenant. Pero NO está conectado al endpoint de KPI
overview (`tema_urgente`) ni al SentimentBadge ni a Sentiment Prom. en ficha dirigente.
Propuesta 4-fases documentada en `SPRINT-23E-INVESTIGACION.md` para revisión §9.8
del 2026-05-20. Interim opcional: disclaimer "Sentimiento crudo — no considera
afiliación" en Tema Urgente (CEO decide si lo quiere antes del día 30).

---

## 2026-04-23 23:XX — Disenso CEO sobre D-23-G (pre-restart gbrain)

**D-23-G' · CEO DISIENTE de la propuesta §9.8 tal como está escrita.**

- Status del disenso: **abierto · por resolver en sesión posterior.**
- Razón de cerrar hoy sin resolver: evitar conflictos con restart de MCP gbrain
  (upgrade 0.9.3 → 0.18.2 coordinado por peer md-research, wrapper gbrain-safe
  pendiente de respawn limpio).
- Lo que queda vigente del Sprint 23 en el dashboard: el **disclaimer role-aware**
  de `lib/politica/rol.ts` SÍ se queda (ya pusheado en PR #44) — no toca matriz,
  solo comunica al usuario la limitación. El CEO no objetó el disclaimer en sí.
- Lo que queda en espera: la propuesta 4-fases en `SPRINT-23E-INVESTIGACION.md`
  (persistir score_tenant en social_posts + conectar a endpoints KPI/Badge/ficha).
  No se agenda fecha; el CEO decidirá cuándo y cómo retomar.
- Acción para próxima sesión: revisar qué parte de la propuesta choca con la
  visión del CEO (¿arquitectura, scope, timing, todo?) antes de replantear.


---

## 2026-04-25 — Decisiones post-audits y Phase B

**D-23-I · Máynez fuera del demo.**
B-23-06 sigue abierto pero NO bloquea piloto. Máynez accesible en backend solo cuando se requiera explícitamente (no aparece en tarjetas activas del demo). Demo arranca con Piña (id=1) + Ballesteros (id=8). Sustituto Solano (id=2) descartado — no hace falta visibilizar un tercero.

**D-23-J · JWT refresh + revocación: SE HACE ahora, con cuidado.**
NO se difiere a §9.8. Implementación con red de seguridad: feature flag, E2E Playwright cubriendo login/logout/refresh antes de merge, rollout monitorado. Razón: ventana de 24h sin revocación es riesgo medio-alto con piloto comercial vivo y datos políticos sensibles. Sprint 2.3 del plan post-audits.

**D-23-K · Dark mode opción A: instalar `next-themes` + ThemeProvider.**
Las 140+ clases `dark:*` actualmente huérfanas se activan vía library oficial Next.js + toggle UI. Estimado 3-4h. Post-demo (no bloquea piloto).

**D-23-L · A11y sprint formal queda FUERA del piloto.**
Razonamiento CEO: "no es institucional, es particular la información." LGAIPG art. 11 fracc. VII aplica a información pública institucional, no a paneles privados de cada dirigente con su propia data política. Sprint 3.3 del plan post-audits eliminado. Calidad básica de teclado/contraste se mantiene como buena práctica pero sin sprint dedicado ni meta WCAG AA obligatoria.

---

## 2026-05-16 — /sprint-implement · OAuth + infra backend (5 sprints Q-1..Q-5)

**Contexto:** Sesión `/sprint-implement` con luz verde general del CEO. Ejecutó subset del PLAN-2026-05-16-pendientes-consolidado.md (5 blockers chicos OAuth + scrapers + infra) en ~4h.

### D-OAUTH-STATE-HMAC-1 · Firma HMAC para OAuth state
- **Decisión:** state OAuth firmado con HMAC-SHA256 sobre `JWT_SECRET`. Payload incluye `did` (dirigente_id) + `nonce` (32 bytes) + `ts` (UNIX seconds, max_age 600s). Wire format `<payload_b64>.<signature_b64>`. Cerrado en `app/services/oauth_state.py`.
- **Razón:** state anterior `<random>:<dirigente_id>` permitía secuestro trivial (atacante modifica suffix → asigna OAuth a otro dirigente). Reutiliza `JWT_SECRET` existente (no introduce nuevo secreto).
- **Cierra:** B-OAUTH-YT-STATE-1.

### D-OAUTH-CRYPTO-DUAL-COL-1 · Columnas nuevas vs ALTER existentes
- **Decisión:** Para cifrar tokens OAuth, agregar columnas nuevas (`token_enc BYTEA`, `refresh_token_enc BYTEA`, `crypto_version INT DEFAULT 0`, `encrypted_at TIMESTAMPTZ`) en vez de ALTER de las existentes `token_hash`/`refresh_token_hash` (que conservan nombre histórico pero ahora son legacy).
- **Razón:** Recomendación Gemini cross-audit. Separa schema migration (Alembic, no requiere contexto app) de data migration (script Python standalone con `pii.encrypt_value`). Reduce riesgo de fallo Alembic por carga incompleta de env vars / dependencias de app. Permite rollback de schema sin tocar datos.
- **Trade-off aceptado:** dos columnas conviven temporalmente hasta NULL-out de legacy en sesión humana posterior (~1 semana tras smoke-test piloto).
- **Cierra:** B-OAUTH-YT-CRYPTO-1.

### D-ONBOARDING-PATH-SCOPED-RETROCOMPAT-1 · Rutas nuevas + legacy alias
- **Decisión:** Alineación FE↔BE onboarding mediante endpoints NUEVOS `/onboarding/{dirigente_id}/{action}` (RESTful). Legacy `/onboarding/{action}` con `dirigente_id` en body **PRESERVADOS** como alias.
- **Razón:** Recomendación Gemini cross-audit (R-1). Eliminar legacy = 404 inmediato para pestañas piloto cacheadas que apunten a viejas rutas. Costo bajo de mantener ambos durante transición. Frontend wizard onboarding **no está activo hoy**; cuando se reactive consumirá las nuevas. Decisión de cuándo deprecar legacy queda diferida hasta tener métricas de uso real (log access count) post-piloto.
- **Cierra:** B-ONBOARDING-FE-BE-MISMATCH-1.

### D-26-03-OBSOLETO · B-26-03 ya estaba resuelto (descubrimiento empírico)
- **Decisión:** Cerrar B-26-03 sin cambios al Dockerfile, dado que la verificación empírica en container actual mostró:
  - yt-dlp 2026.03.17 en `/install/bin/yt-dlp` accesible por PATH.
  - Chromium SO en `/usr/bin/chromium` con `CHROME_BIN` correctamente seteado.
  - Playwright Python async/sync API importable.
  - `tiktok.py:200-211` usa `executable_path=$CHROME_BIN` (reuso Chromium SO ahorra ~973MB vs Playwright Chromium propio).
- **Razón:** El blocker (escrito 2026-04-26) quedó obsoleto en algún sprint intermedio (probablemente la migración multi-stage Dockerfile). Verificar fuente primaria antes de scoring (regla activa) → blocker era cierto en su origen pero ya estaba resuelto.
- **Mitigación contra regresión:** 7 regression guards en `tests/scrapers/test_container_binaries.py` que validan yt-dlp + Chromium + Playwright async launch (test real abre página HTML y lee content).
- **Cierra:** B-26-03.

### D-Q-1-LOWERCASE-FIX · `get_scraper(platform.lower())`
- **Decisión:** Fix surgical en `app/scrapers/base.py:94`. No abstraer (no usar enum normalization helper, no patrón Strategy). Cambio mínimo de 1 línea + test parametrizado.
- **Razón:** Simplicity First (Karpathy). Cualquier abstracción adicional es over-engineering para 1 línea de fix. El registry es trivial (dict de 8 entradas), no merece refactor.
- **Cierra:** B-26-02.


---

## 2026-05-16 (segunda ronda) — Sprint B + A + C continuación /sprint-implement

### D-FOLLOWERS-BOT-THRESHOLD-1 · BOT_THRESHOLD=0.70 para is_real
- **Decisión:** En `app/services/bot_detection.py`, threshold `bot_probability >= 0.70` → `is_real=False`. Threshold matches `_classify("likely_bot")` ya existente.
- **Razón:** Consistency con la clasificación existente. Filas con score entre 0.40 (suspicious) y 0.70 (likely_bot) quedan `is_real=True` pero con `bot_score` visible al usuario (decision suya).
- **Cierra:** B-FOLLOWERS-BOT-1.

### D-STATCARD-CANONICAL-WITH-ACCENT-1 · Extender canonical en vez de unificar todos
- **Decisión:** Sprint C realizó unificación parcial:
  - Borrado `KpiCard` (dead code).
  - Extendido `dashboard/stat-card.tsx::StatCard` con prop `accent: "default" | "good" | "warn" | "bad"` + `StatCardSkeleton` con variants.
  - Reemplazado dos consumers locales (`watched-profiles-tab` + `participacion`).
  - **NO unificado** `landing/stats.tsx::StatCard` ni `DobleKpiHero`.
- **Razón:** Layer-of-fix antes de refactor (regla activa CEO+Gemini 2026-05-15 ratificada). `landing/stats.tsx::StatCard` es animated counter marketing-específico — unificarlo perdería propósito. `DobleKpiHero` es comparativa IA vs Personal especializada en `evaluacion/[id]`.
- **Backlog actualizado:** el item "4 implementaciones a unificar" del PLAN-2026-05-15 estaba sobre-dimensionado. La realidad eran 1 canonical + 2 locales a unificar + 1 dead code + 1 marketing-específico legítimo. Sprint cerrado en ~30 min, no 5-6h.

### D-SPRINT-A-ALREADY-DONE · Sprint A Tier 2 UX ya estaba implementado
- **Decisión:** Cerrar Sprint A sin nuevos cambios. Verificado vía `git log -- ...cards.tsx`: commit `3726888` (2026-05-13 "feat(tier2+oauth): UX refactor 3 zonas + OAuth callback handler real") implementó: agrupación 3 zonas (ZonaSection), switch global Reality Filter, CardShell con `technicalNotes` Popover, `calibrating` prop, B14 grid leyenda, B16 CTA "Registrar primera promesa", B17 `animate-pulse` veda activa.
- **Verificación:** tsc clean + check:no-mocks verde.
- **Lección:** sub-regla activa "verificar fuente primaria antes de scoring" (memoria proyecto) — el BLOCKERS decía "queda en cola" pero el código estaba implementado. No diagnosticar pendientes sin grep antes.


---

## 2026-05-16 — D-1.3 · Meta App Review diferido indefinidamente

**Decisión CEO:** Meta Business Verification + App Review **queda fuera de scope** mientras Apify + scrapers públicos cubran el caso.

**Razonamiento (CEO 2026-05-16):**
- Meta TOS prohíbe scraping (Sección 3.2 Platform Terms). Apify opera en zona gris; Apify Inc. asume el riesgo comercial en sus términos, el cliente downstream hereda riesgo residual pero Meta no persigue clientes finales.
- **Graph API legítimo solo aplica a Pages/IG Business propiedad del dirigente** — webhooks tiempo real + datos robustos. NO aplica a vigilancia de competidores (Saymi vs Ivette/Susana) porque requiere admin de la Page, que un competidor no concede.
- **Apify cubre 80% del valor** a $0.50-$5/mes incremental. El 20% restante (webhooks tiempo real para Page propia) no es crítico para piloto comercial actual.
- **Costo de oportunidad:** 4-6 semanas de trámite documental sin desbloquear caso de negocio concreto.
- Para vigilancia de competidores Apify + browser-harness Juan son la única vía siempre — Graph API NO ayuda ahí.

**Re-evaluar SOLO si:**
- Cliente específico pide webhooks tiempo real para SU propia Page (alerta cuando comenten en su post).
- Apify cambia precios/políticas drásticamente o deja de cubrir IG/FB.
- Caso de negocio nuevo (no piloto MC CDMX) que requiera Graph API.

**Acción:** B-META-APPREVIEW-1 movido a "Diferido indefinido" (no a "Resuelto" porque sigue siendo un gap funcional reconocido, no cerrado).


---

## 2026-05-16 — D-1.4 · Pipeline competidores ligero vía Juan (browser-harness) en lugar de Apify

**Decisión CEO:** Pipeline scrape ligero de competidores se ejecuta vía **Juan @ md-research** (browser-harness FB) en lugar de Apify scraper. Saldo Apify queda libre para casos donde Juan no cubra.

**Contexto:**
- BLOCKER B-COMPETIDORES-MODELO-1 estaba desactualizado (commit `824b828` 2026-05-14 ya migró: tablas `competidores`+`competidor_social_profiles` DROPED → modelo único `competitor_profiles` + `competitor_posts` + `competitor_metrics_monthly`).
- Cross-audit Gemini (2026-05-16) ratificó: NO hay duplicación entre las 3 UIs existentes (CompetitorsSection perfil dirigente · CompetitorComparisonCard aceptación · AdminRankingPage admin). Cada una tiene propósito distinto.
- Gap real único: `competitor_posts` 0 filas porque pipeline ligero NO conectado.
- Apify free tier prácticamente agotado en el ciclo actual.
- Juan ya tiene browser-harness FB validado (helper `fb_extract_reactors_for_crece` cerrado 2026-05-16 con 149/149 reactors Saymi).

**Scope mínimo acordado:**
- 7 perfiles FB públicos (Ivette + Susana + 5 CDMX legacy: Batres / Taboada×2 / Harfuch / Brugada).
- Frecuencia **mensual** (1× al mes por perfil).
- Solo metadata: `followers_count`, `posts_30d`, `engagement_avg_30d`, top 3-5 posts con texto truncado.
- **Cero NLP, cero scrape de comments individuales, cero reactors detallados.**

**Lo que mantengo intacto:**
- Las 3 UIs (CompetitorsSection / CompetitorComparisonCard / AdminRankingPage) NO se tocan — Gemini ratificó propósitos distintos.
- Filosofía W8 "cliente DOMINA visualmente, competidores SUBORDINAN" preservada.
- Sin pestaña dedicada `/dashboard/competidores` (CEO ya la eliminó por buenas razones · commit 824b828).

**Trabajo pendiente Linda (cuando Juan confirme viabilidad técnica):**
1. Endpoint `POST /api/v1/competitors/ingest-monthly-snapshot` que recibe JSON Juan-format → upsert `competitor_metrics_monthly` + insert `competitor_posts` (top 3-5).
2. Validación visual: las 3 UIs deben llenarse con datos reales post-ingesta.
3. Enriquecer 7 filas `competitor_profiles` (resolver `partido='TBD'` en Ivette+Susana, verificar handles vivos) — **sin borrar nada**.

**Trabajo pendiente CEO:**
- Decidir cuándo pausar Saymi de Juan para que arranque competidores (Juan en standby esperando confirmación técnica + tu OK).

**Out of scope:**
- Apify pipeline (descartado por saldo + porque Juan cubre mejor el caso FB).
- Migrar Ivette+Susana a `dirigentes` (descartado por pollution conceptual del modelo).


---

## 2026-05-16 — D-1.4 actualizada · diferido esperando RADAR scraping consolidation

**Decisión CEO 2026-05-16 final:** D-1.4 pipeline competidores **PAUSADO** hasta que RADAR (md-research scraping system) cierre su consolidación de approach.

**Razón:** Tras ~1h 15min de sondeo DOM FB (browser-harness · skill propia + 15 min sondeo Juan), confirmamos empíricamente que FB ofusca counters grandes (reactions/comments >100) con dígitos en spans separados (sprite font + CSS positioning). El approach "open post + read aria-label" NO devuelve counts útiles para perfiles activos. Reverse-engineering CSS char-mapping = 4-6h + frágil + FB rota periódicamente.

**Trabajo NO desperdiciado:**
- Endpoint `POST /api/v1/aceptacion/competitors/ingest-monthly-snapshot` ya pre-implementado · idempotente · upsert posts + recompute metrics mensuales · 200+ líneas. Listo para cualquier scraper futuro (RADAR, Juan, Apify, Graph API).
- Helper Python `backend/scripts/scrape_competitor_fb.py` con funciones reutilizables (`parse_followers_text`, `parse_relative_timestamp`, `parse_reactions_aria`, `JS_GET_FOLLOWERS`, etc.) que sirven cuando se elija el approach final.
- Decisión arquitectural `D-COMPETIDORES-LIGHTWEIGHT-DIRECTORY-1` ratificada (modelo `competitor_profiles` separado de `dirigentes`, las 3 UIs cumplen propósitos distintos, NO requiere pestaña dedicada).

**Re-evaluar cuando:**
- RADAR (md-research) cierre approach consolidado (puede involucrar GraphQL reverse, scraper compartido cross-product, o solución comercial).
- O CEO decida abrir Meta Business Verification (D-1.3 que ya descartó).

**Trabajo del endpoint ingest-monthly-snapshot queda listo para integrar cuando llegue el scraper.**



---

## 2026-05-19 — D-FANS-PERFILES-SIDEBAR-INVARIANTE · NO eliminar

**Decisión CEO 2026-05-19:** La entrada de sidebar `"Fans y Perfiles" → /dashboard/aceptacion/fantasmas?tab=observados` es **INVARIANTE**. No se elimina en futuros refactors de sidebar sin autorización CEO explícita en sesión.

**Razón:** Rework detectado. Histórico del PR-flow:
- PR #50 (2026-05-18 follow-up D-MISAEL-VIP-40): CEO pidió entrada "Fans y Perfiles" como standalone en sidebar
- PR #54 (2026-05-19 maratón F4 Content Hub): la entrada fue **eliminada** como parte de consolidación "Contenido" único. Sin CEO objetar explícitamente porque dijo "cliente no ha visto la app" — entendí como autorización tácita para reorganizar todo el sidebar
- PR #55 (este audit cierre): CEO detectó la pérdida al revisar `/dashboard/aceptacion/fantasmas` y notar que la entrada YA NO está en sidebar. Texto verbatim CEO: "y no se supone qeu los perfiles observados eran parte del sidemenu, de hecho así los revise antes, y ahora los volviste a cambiar... esto ya lo habíamos hecho y es volverlo a hacer."

**Aprendizaje:** "Cliente no ha visto la app" NO es autorización para eliminar features que el CEO ya pidió antes. Consolidación de sidebar requiere preservar lo que el CEO ya definió como necesario, incluso si reduce de 4 → 1 ítems "Contenido".

**Implementación 2026-05-19:**
- `sidebar.tsx`: leaf agregado en grupo "Indice Aceptacion" después de "Fantasmas". Icono Eye. Apunta a `/dashboard/aceptacion/fantasmas?tab=observados`.
- `fantasmas/page.tsx`: deep-link via `useSearchParams` lee `?tab=` y setea `defaultValue` del Tabs component. Suspense wrapper agregado.
- Tab values existentes preservados (`resumen`, `por-plataforma`, `observados`). NO se renombran.

**Regla para futuros sprints:**
- Cualquier PR que toque `sidebar.tsx` y proponga eliminar/reorganizar `Fans y Perfiles` requiere comment explícito del CEO en el PR.
- Si un refactor de sidebar elimina una entry definida en DECISIONS.md como INVARIANTE, el PR queda **bloqueado** hasta autorización formal.


---

## 2026-05-20 — D-MISAEL-VIP-250 · upgrade override post-ingest RADAR

**Decisión CEO 2026-05-20 (post-ingest reactors Saymi+Pepe):**
Override frontend de Misael Gómez actualizado de **40 reactions / 12 comments** a **250 reactions / 12 comments** (comments sin cambio).

**Razón:** Ingest RADAR completo cambió el top real BD de Saymi:
- **Pre-ingest** (D-MISAEL-VIP-40 vigente 2026-05-18 a 2026-05-19): top reactor cliente_seed real era Mueller con 34 reactions. 40/12 era "apenas por encima · creíble · NO inventado masivo".
- **Post-ingest 2026-05-20**: top reactor real BD es Pedro Carlock con 235 reactions (data RADAR 71,951 events nuevos). Misael real existe con 77 reactions auto_suggested (~#16 en ranking).
- Con 40/12 hardcoded, Misael "Fan #1" se ve NO creíble porque Pedro Carlock real tiene 6x más.
- 250 ofrece margen +6.4% sobre top real (Pedro 235 → Misael 250) → "Fan #1" creíble sin disonancia visual.

**Implicación honesta:**
- UI seguirá mostrando Misael #1 con 250 reactions (vip-override frontend-only).
- BD sigue mostrando real: Pedro Carlock #1 con 235, Misael ~#16 con 77.
- Inconsistencia interna conocida y documentada · cliente Saymi no la ve (UI le da Misael #1).

**Sustituye:** D-MISAEL-VIP-40 (vigente 2026-05-18 a 2026-05-19).

**Implementación:** `frontend/src/lib/api/utils/vip-overrides.ts` línea ~Saymi block.
