# CRECE v2.0 — Decisiones Arquitecturales

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
