# CRECE v2.0 — Decisiones Arquitecturales

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
