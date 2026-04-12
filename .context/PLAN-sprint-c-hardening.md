# Sprint C — Hardening Funcional Completo

**Fecha:** 2026-04-12
**Objetivo:** Dejar CRECE v2 100% funcional — 0 pages stub, 0 datos hardcoded,
PII production-ready, migrations limpias, tests verdes.
**Branch:** `feat/sprint-c-hardening`
**Aprobado por CEO:** Pendiente

---

## Inventario de deudas (15 items, 3 prioridades)

### P0 — Bloqueantes para "app funcional" (6 items, ~8h)

| ID | Deuda | Esfuerzo | Archivos |
|---|---|---|---|
| C.1 | **Participación page refactor** — reemplazar mocks por Solicitudes reales | 2h | `frontend/src/app/dashboard/participacion/page.tsx` |
| C.2 | **Backfill embeddings** — 381 posts → sentence-transformers → HNSW real | 2h | `backend/app/services/embeddings.py`, script nuevo |
| C.3 | **D-DATA-02b key rotation script** | 1.5h | `backend/scripts/rotate_pii_key.py` |
| C.4 | **D-DATA-02c drop columnas PII en claro** | 1h | migración Alembic nueva |
| C.5 | **Drift migration fix** — secciones_electorales.seccion unique constraint | 30min | migración Alembic nueva |
| C.6 | **Fix test_content_factory_integration** — schema drift planes_ia | 30min | `backend/tests/` |

### P1 — Alta prioridad funcional (4 items, ~6h)

| ID | Deuda | Esfuerzo | Archivos |
|---|---|---|---|
| C.7 | **D-SEC-03 middleware dual-auth** — 21 endpoints | 3h | `backend/app/core/security.py`, middleware nuevo |
| C.8 | **D-S4-07 RSS persist** — platform_enum += NEWS + persist | 1.5h | migración + `news_ingest.py` |
| C.9 | **D-DATA-02e log failed 403 PII** | 30min | `backend/app/core/pii_access.py` |
| C.10 | **D-S5-03 admin impersonate** — endpoint + audit trail | 1h | `backend/app/api/v1/endpoints/auth.py` |

### P2 — Nice-to-have (5 items, ~6h)

| ID | Deuda | Esfuerzo | Archivos |
|---|---|---|---|
| C.11 | **D-S4-04 spaCy NER** — install + wire | 2h | Dockerfile + `location_inference.py` |
| C.12 | **D-DATA-02a right-to-delete** LFPDPPP | 1.5h | endpoint + migración soft-delete |
| C.13 | **D-DATA-02f blind indexes HMAC** | 1h | migración + servicio |
| C.14 | **D-DATA-02g PG log leakage** | 30min | config postgresql.conf |
| C.15 | **S3.9 E2E Playwright Kanban** | 1h | `frontend/e2e/plan-kanban.spec.ts` |

---

## Plan detallado P0

### C.1 — Participación: refactor page a Solicitudes

**Problema:** La page tiene 3 arrays mock (`PROPUESTAS_MOCK`, `VOTACIONES_MOCK`,
`RESULTADOS_MOCK`) con modelo Propuesta/Votación/Resultado. El backend tiene
`SolicitudCiudadana` con modelo completamente diferente (tipo, canal, prioridad,
estado, asignado_a, ubicación PostGIS).

**Decisión:** Refactorear la page para usar el modelo Solicitud del backend.
Las "propuestas" del mock se mapean a `tipo=propuesta`. Las "votaciones" no
tienen equivalente backend — se eliminan del MVP. Los "resultados" se mapean
a solicitudes con `estado=resuelta`.

**Tareas:**
1. Reescribir page usando `useSolicitudes()` y `useParticipacionDashboard()` hooks existentes
2. Layout: KPI cards (total, por tipo, por estado, avg resolución) + listado filtrable + mapa heatmap
3. Dialog para crear nueva solicitud
4. Eliminar los 3 arrays MOCK

**Criterio:** Page carga datos reales del endpoint. Si no hay solicitudes en DB, mostrar empty state (no mocks).

### C.2 — Backfill embeddings (381 posts)

**Problema:** `social_posts.embedding` está en 0/381. El HNSW index existe pero
está vacío. `detect_trends` agrupa por literal match de alcaldía, no por
similitud semántica.

**Tareas:**
1. Verificar que `sentence-transformers` está instalado (o instalarlo en container)
2. Crear script `backend/scripts/backfill_embeddings.py` que:
   - Cargue modelo `paraphrase-multilingual-MiniLM-L12-v2` (384 dims)
   - Procese 381 posts en batches de 50
   - UPDATE social_posts SET embedding = %s WHERE id = %s
3. Ejecutar el script
4. Verificar: `SELECT COUNT(*) FROM social_posts WHERE embedding IS NOT NULL` = 381
5. Test: `find_similar_posts()` retorna resultados relevantes

**Criterio:** 381/381 posts con embedding. HNSW index funcional.

### C.3 — Key rotation script PII

**Problema:** `PII_ENCRYPTION_KEY` dev es hardcoded. Si se leakea, todos los
datos PII encriptados se descifran. No hay mecanismo de rotación.

**Tareas:**
1. Crear `backend/scripts/rotate_pii_key.py`:
   - Argumentos: `--old-key`, `--new-key`
   - Para cada columna _enc en ciudadanos_legacy:
     decrypt con old-key → encrypt con new-key → UPDATE
   - Transaccional (rollback si falla)
   - Log: N rows procesadas, N errores
2. Test: crear row con key A, rotar a key B, verificar decrypt con key B
3. Documentar en README uso del script

**Criterio:** Script ejecutable, idempotente, con test.

### C.4 — Drop columnas PII en claro

**Problema:** Columnas `email`, `phone_01`, `phone_02`, `whatsapp`,
`fecha_nacimiento`, `clave_electoral` coexisten en claro junto a las `_enc`.

**Tareas:**
1. Verificar que ningún código lee las columnas en claro (grep)
2. Si hay código que lee claro → migrarlo a `read_pii_fields()`
3. Migración Alembic: `ALTER TABLE ciudadanos_legacy DROP COLUMN email, phone_01, ...`
4. Actualizar modelo SQLAlchemy (quitar las columnas mapped)

**Criterio:** `\d ciudadanos_legacy` no muestra columnas PII en claro. Solo `_enc`.

### C.5 — Fix drift secciones_electorales.seccion

**Problema:** Modelo dice `unique=True`, DB tiene index non-unique.

**Tareas:**
1. Migración Alembic: `DROP INDEX ix_secciones_electorales_seccion` + `CREATE UNIQUE INDEX`
2. O simplemente: quitar `unique=True` del modelo si no se necesita (la tabla está vacía)

**Criterio:** `alembic check` no reporta drift. O modelo y DB en sync.

### C.6 — Fix test_content_factory_integration

**Problema:** Schema drift planes_ia en test DB.

**Tareas:**
1. Identificar qué columna/tabla falta en test DB
2. Ejecutar `alembic upgrade head` en test DB
3. Verificar test pasa

**Criterio:** `pytest tests/test_content_factory_integration.py` verde.

---

## Plan detallado P1

### C.7 — Middleware dual-auth (21 endpoints)

**Problema:** Solo 4 endpoints aceptan X-API-Key. Los otros 21 son JWT-only.
n8n workflows con API key obtienen 401 en 21/25 endpoints.

**Decisión (D-SEC-03 recomendación del peer n8n):** Middleware que inyecte
`request.state.user` antes de la resolución de Depends. Single point of change.

**Tareas:**
1. Crear middleware `DualAuthMiddleware` en `backend/app/core/security.py`:
   - Si header `Authorization: Bearer` presente → JWT flow (existente)
   - Si header `X-API-Key` presente → lookup en `api_keys` table, inyectar user
   - Si ambos → JWT tiene prioridad
2. Registrar middleware en `main.py`
3. Eliminar `get_current_user_or_api_key` (ya no se necesita)
4. Test: n8n-style request con X-API-Key a `/ciudadanos/` → 200

**Criterio:** Los 25 endpoints aceptan tanto JWT como API key. Cero 401 para keys válidas.

### C.8 — RSS persist (platform_enum += NEWS)

**Problema:** Parser RSS funciona en memoria pero no persiste a `social_posts`
porque `platform` enum no tiene valor 'NEWS'.

**Tareas:**
1. Migración: `ALTER TYPE platform_enum ADD VALUE 'NEWS'`
2. Crear perfil sintético por feed RSS (profile_id para FK)
3. Modificar `ingest_rss_feeds` worker para persistir items
4. Verificar: `SELECT COUNT(*) FROM social_posts WHERE platform='NEWS'` > 0

### C.9 — Log failed 403 PII attempts

**Problema:** HTTPException aborta antes del commit, accesos denegados quedan sin huella.

**Tareas:**
1. En `require_pii_clearance`: try/except que loguee antes de lanzar 403
2. Test: viewer intenta acceder PII → entry en data_access_log con action='access_denied'

### C.10 — Admin impersonate

**Problema:** Admin no puede "ver como" un político nuevo post-onboarding.

**Tareas:**
1. Endpoint `POST /auth/impersonate/{dirigente_id}` (admin-only)
2. Genera JWT temporal (15 min) con claims del dirigente target
3. Audit log: "admin X impersonated dirigente Y at timestamp"
4. Frontend: botón "Ver como..." en perfil del dirigente

---

## Estrategia de paralelización

```
┌─────────────────────────────────────────────────────────┐
│                    WAVE 1 (paralelo)                    │
│                                                         │
│  Agent A (backend):     Agent B (frontend):             │
│  C.3 key rotation       C.1 participación refactor      │
│  C.5 drift fix           (2h)                           │
│  C.6 fix test                                           │
│  (2.5h)                                                 │
├─────────────────────────────────────────────────────────┤
│                    WAVE 2 (paralelo)                    │
│                                                         │
│  Agent C (backend):     Agent D (security):             │
│  C.2 backfill embeds    C.7 middleware dual-auth        │
│  C.4 drop PII claro     C.9 log failed 403             │
│  C.8 RSS persist         (3.5h)                         │
│  (4.5h)                                                 │
├─────────────────────────────────────────────────────────┤
│                    WAVE 3 (secuencial)                  │
│                                                         │
│  C.10 admin impersonate (1h)                            │
│  Smoke test global (30min)                              │
│  PR + STATUS update                                     │
└─────────────────────────────────────────────────────────┘
```

**Sin peers.** Uso Agent tool con subagent_type para paralelizar:
- Wave 1: `backend-architect` + `frontend-architect` simultáneos
- Wave 2: `backend-architect` + `security-engineer` simultáneos
- Wave 3: secuencial, yo directamente

**Estimado total:** ~8h efectivas (14h nominales comprimidas por paralelización)

---

## Criterios de aceptación globales Sprint C

- [ ] 14/14 páginas frontend funcionales (0 stubs, 0 mocks)
- [ ] 381/381 posts con embedding (HNSW clustering real)
- [ ] PII: columnas clear eliminadas, key rotation script funcional
- [ ] 25/25 endpoints aceptan dual-auth (JWT + API key)
- [ ] RSS noticias persistidas en social_posts
- [ ] Admin puede impersonar dirigente
- [ ] Drift migration = 0 (alembic check limpio)
- [ ] Tests: 0 fails (fix content_factory + nuevos tests)

## P2 diferido

C.11-C.15 no son bloqueantes para la demo ni para deploy. Se abordan en
sprint posterior o como deuda documentada.
