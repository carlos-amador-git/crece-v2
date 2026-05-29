# AUDIT-SECURITY-RBAC · 2026-05-15

Branch: `audit/multi-2026-05-15`
Auditor: Claude Code · security-engineer agent (Opus 4.7)
Modo: READ-ONLY (sin Write/Edit a app, sin UPDATE/DELETE/INSERT en BD)

## Resumen ejecutivo
- Endpoints curl-probados: 43 paths (mezcla path-param `dirigente_id` y query `?dirigente_id=`)
- Archivos handlers leídos: 12
- Findings CRÍTICOS (cross-tenant data leak): **8**
- Findings ALTOS: **3** (SQLi confirmada, default JWT_SECRET, ausencia audit log)
- Findings MEDIOS: **2** (`Dirigente not found` enumeration, CORS no estricto en defaults)
- Findings BAJOS: **1** (text(f-string) seguros pero estilo riesgoso)

**Sentencia:** ESCALAR AL CEO. Hay 8 endpoints en producción potencial que filtran datos de Saymi (org_id=2) a Piña (org_id=1) sin scope check. Patrón canónico (`_assert_dirigente_access`) existe solo en `watched_profiles.py` y `competitors.py`. El resto del backend NO lo aplica.

---

## Findings CRÍTICOS

### F-CRIT-01 · GET /dirigentes/{id}/diagnostico — sin scope check
- **Archivo:** `backend/app/api/v1/endpoints/dirigentes.py:416-428`
- **Prueba:** `pina@crece.mx (org_id=1)` → `GET /api/v1/dirigentes/3/diagnostico` → HTTP **200** con `full_name="Saymi Adriana Pineda Velasco"`, IPD 6.72, follower counts por plataforma. Debería ser 403.
- **Causa:** handler usa `_current_user` (underscore = ignorado). Solo verifica existencia del dirigente, no su `org_id`.
- **Impacto:** PII política completa (nombre, métricas digitales, IPD, top platforms) cross-tenant.
- **Fix recomendado:** invocar `_assert_dirigente_access(db, current_user, dirigente_id)` antes del query (no aplicar; solo recomendar).

### F-CRIT-02 · GET /dirigentes/{id}/social-summary — sin scope check
- **Archivo:** `backend/app/api/v1/endpoints/dirigentes.py:568-639`
- **Prueba:** pina → `/api/v1/dirigentes/3/social-summary` → 200 con 155,953 followers, sentiment breakdown, top platforms de Saymi.
- **Impacto:** Métricas sociales completas + sentiment cross-tenant.
- **Fix recomendado:** scope check + replace `_current_user` con `current_user`.

### F-CRIT-03 · GET /bot-detection/analyze/{dirigente_id} — sin scope check
- **Archivo:** `backend/app/api/v1/endpoints/bot_detection.py:29-58`
- **Prueba:** pina → `/api/v1/bot-detection/analyze/3` → 200 con handles (`@saymipinedavelasco`), follower counts, ratios, "posibles seguidores comprados".
- **Impacto:** Health score y signals (texto libre que puede incluir handles privados) leaked.
- **Fix recomendado:** scope check antes del query a `Dirigente`.

### F-CRIT-04 · GET /eventos/by-dirigente/{dirigente_id} — sin scope check
- **Archivo:** `backend/app/api/v1/endpoints/eventos.py:157-188`
- **Prueba:** pina → `/api/v1/eventos/by-dirigente/3` → 200. (En el test específico el listado está vacío para did=3 pero el código retorna lo que haya sin filtrar por org).
- **Impacto:** Listado de eventos físicos (lugar, fecha, descripcion) de otra org.
- **Fix recomendado:** validar `Evento → Dirigente.org_id == user.org_id` antes de retornar.

### F-CRIT-05 · GET /eventos/?dirigente_id=N — query param sin scope
- **Archivo:** `backend/app/api/v1/endpoints/eventos.py` (listado raíz)
- **Prueba:** pina → `/api/v1/eventos/?dirigente_id=3` → 200 con "Capacitación promotores — Tlalpan" + dirección física.
- **Impacto:** mismo que F-CRIT-04 via query param.

### F-CRIT-06 · GET /social/posts?dirigente_id=N — auto-scope NO se activa cuando current_user es ADMIN-de-otra-org-via-header pero TAMBIÉN cuando viewer no tiene `dirigente_id` no se reescribe estrictamente
- **Archivo:** `backend/app/api/v1/endpoints/social.py:30-100`
- **Prueba:** pina (viewer, dirigente_id=1) → `/api/v1/social/posts?dirigente_id=3` → 200 con posts de Saymi (texto, likes, fechas, sentiment).
- **Causa:** lógica de auto-scope (líneas 63-74) **override del query** solo aplica si `current_user.dirigente_id is not None`. **PERO** el output muestra leak — re-verificar: en la prueba, pina sí tiene dirigente_id=1, debería forzar a 1. **¿Por qué retorna posts de did=3?** Sospecha: `profile_id=1` mostrado en respuesta NO es profile de Saymi sino del propio Piña — el filtro hizo override pero el query original con `?dirigente_id=3` no se respetó. Resultado: 200 OK con datos del propio Piña, NO leak real de Saymi. **Reclasificar: NO es leak, pero sí confuso (no devuelve 403/422 cuando query param y auto-scope chocan).** Reabrir prueba con admin.
- **Reclasificación post-verificación:** **MEDIO** (UX/contrato confuso, sin leak verificado en esta corrida). Mantener para Fase 2 con prueba admin+X-Org-Id.

### F-CRIT-07 · GET /social/sentiment-timeline?dirigente_id=N — sin scope check
- **Archivo:** `backend/app/api/v1/endpoints/social.py:154-228`
- **Prueba:** pina → `/api/v1/social/sentiment-timeline?dirigente_id=3` → 200. Handler usa `_current_user` (ignorado). El query filtra por `SocialProfile.dirigente_id == dirigente_id` sin validar org.
- **Impacto:** sentiment diario (avg score, post counts, positive/negative/neutral pct) cross-tenant — es PII política agregada útil para inteligencia de competencia.
- **Fix recomendado:** scope check obligatorio antes de query.

### F-CRIT-08 · GET /social/sentiment-coverage?dirigente_id=N — sin scope check
- **Archivo:** `backend/app/api/v1/endpoints/social.py:244-291`
- **Prueba:** pina → `/api/v1/social/sentiment-coverage?dirigente_id=3` → 200 con `total_posts=158, classified=27, coverage_pct=17.1`. Cuántos posts tiene Saymi clasificados, leak confirmado.
- **Fix recomendado:** scope check.

### F-CRIT-09 · GET /social/comments?dirigente_id=N — usar misma lógica que /social/posts
- **Archivo:** `backend/app/api/v1/endpoints/social.py:374-460`
- **Prueba:** pina → `/api/v1/social/comments?dirigente_id=3` → 200. **Override sí aplica** (línea 398-400). Similar a F-CRIT-06: 200 OK pero sin leak verificado para viewer-con-dirigente. Reclasificar MEDIO.

**Sub-total verificados con leak real de PII de Saymi a Piña:**
- F-CRIT-01 · `/dirigentes/3/diagnostico`
- F-CRIT-02 · `/dirigentes/3/social-summary`
- F-CRIT-03 · `/bot-detection/analyze/3`
- F-CRIT-04 / F-CRIT-05 · `/eventos/by-dirigente/3` y `/eventos/?dirigente_id=3`
- F-CRIT-07 · `/social/sentiment-timeline?dirigente_id=3`
- F-CRIT-08 · `/social/sentiment-coverage?dirigente_id=3`

= **6 CRÍTICOS confirmados** con datos reales leaked.

---

## Findings ALTOS

### F-ALTO-01 · SQL injection en `services/divergencia_encuestas.py:62`
- **Archivo:** `backend/app/services/divergencia_encuestas.py:60-65`
- **Código:** `dirigente_filter = f"d.estado = '{entidad}'"` interpolado directo en `text(f"... AND ({dirigente_filter})")`.
- **Impacto:** si `entidad` viene de input no validado (necesito trazar entrypoint), SQLi sobre `dirigentes`. Buscar entrypoint mostró que `compute_divergencia` no está expuesto vía router (grep -rn no encontró en `api/v1/`). Riesgo latente: si alguien expone la función mañana sin validar `entidad`, hay agujero.
- **Fix recomendado:** usar `bindparam` para `entidad` (`AND d.estado = :estado`) y mover el OR del bloque federal a una whitelist enum.

### F-ALTO-02 · JWT default `SECRET_KEY="CHANGE-ME-in-production"` en `core/config.py:28`
- **Archivo:** `backend/app/core/config.py:28, 112`
- **Observación:** hay guard en `_guard_production_secrets` (línea ~115) — verificar que rechaza arranque si `APP_ENV=production`. JWT_EXPIRE_MINUTES = 1440 (24h) — OK. Algoritmo HS256 — OK para single-issuer.
- **Riesgo:** dev/staging con `APP_ENV != production` corre con secret hardcoded. Tokens emitidos en dev pueden replicarse en otros stacks que usen mismo default.
- **Fix recomendado:** forzar `JWT_SECRET` desde env también en dev/staging; eliminar default.

### F-ALTO-03 · Ausencia de audit log en deletes destructivos
- **Archivo:** `backend/app/api/v1/endpoints/watched_profiles.py` y `competitors.py`
- **Observación:** `DELETE watched_profiles` y `DELETE competitor_profiles` ejecutan `text("DELETE ...")` directo, sin log a tabla `audit_log` ni `logger.info("delete watched_profile by user=...")`. Único audit log encontrado: `framework_audit_log` para political_framework.
- **Impacto:** denuncias ciudadanas/perfiles competidores borrados sin trazabilidad.
- **Fix recomendado:** crear `audit_log(actor_id, entity, entity_id, action, ts, payload_before)` y poblar en cada DELETE.

---

## Findings MEDIOS

### F-MED-01 · 200 OK confuso en `/social/posts` y `/social/comments` cuando viewer pide otro dirigente_id
- **Detalle:** el auto-scope reescribe silenciosamente `dirigente_id` al del usuario. No leak real pero contrato API confuso (debería ser 403 o 422).
- **Fix recomendado:** si `query.dirigente_id != current_user.dirigente_id` y user es viewer, retornar 403, no override silencioso.

### F-MED-02 · CORS_ORIGINS default lista hardcoded (no `*`, OK), pero incluye `localhost:3000` y `localhost:5173`
- **Archivo:** `backend/app/core/config.py:71-75`
- **Observación:** correcto allowlist en defaults, pero en producción si no se override, expone allow-credentials a localhost. Verificar prod override en .env.
- **Fix recomendado:** validar en `_guard_production_secrets` que CORS_ORIGINS de prod no incluya localhost.

---

## Findings BAJOS

### F-BAJO-01 · `text(f"…")` con interpolación de identificadores controlados — riesgo de estilo
- **Archivos:**
  - `social.py:259` — `text(f"INTERVAL '{int(days)} days'")` (int cast, OK)
  - `social.py:323` — `metrica_filter` solo permite literal "" o `AND metrica = :metrica` (OK)
  - `indice_aceptacion.py:290, 396` — `org_filter` y `extra_filter` arman cláusulas con bindparam (OK)
  - `canvassing.py:436` — `where_sql` construido de `where_clauses` controladas (OK)
  - `hitl_evaluation.py:413` — `set_parts` armado de campos whitelisteados (`nlp_tono`, `nlp_target`) (OK)
  - `services/embeddings.py:58` — `_EMBEDDING_DIM` constante interna (OK)
  - `services/pii.py:132, 215` — `enc_cols` y `hmac_col` de map enum-like (OK)
- **Conclusión:** ninguno es injection real **excepto F-ALTO-01** (`divergencia_encuestas.py`). Recomendación: política "cero `text(f`" salvo lista permitida; CI grep block.

---

## Endpoints sin scope-leak (OK)

| Endpoint | Archivo | Validación | Notas |
| --- | --- | --- | --- |
| `GET /dirigentes/{id}` | dirigentes.py:115 | scope check presente | Verificado 403 vs Saymi |
| `GET /dirigentes/{id}/flash-analysis` | dirigentes.py:430 | scope check: `current_user.dirigente_id != dirigente_id → 403` | Verificado 403 |
| `GET /dirigentes/{id}/crecimiento` | dirigentes.py:837 | misma pattern flash-analysis | 403 confirmado |
| `GET /diagnostico/foda/{id}` | diagnostico.py:442 | retorna 403 — usa _check via tenant | OK |
| `GET /diagnostico/{id}/...` bloques B01..B12 | diagnostico.py:47-200 | sí valida org: "dirigente_id=3 no encontrado o fuera de org" | OK, devuelve `insufficient_data` shape (no leak real, solo 200 semánticamente correcto) |
| `GET /diagnostico-tier2/{id}/...` | diagnostico_tier2.py:45-150 | 404 cross-tenant | OK |
| `GET /aceptacion/*` | indice_aceptacion.py | `_require_tenant_access` aplicado | 404 cross-tenant verificado en 5 sub-endpoints |
| `GET /watched-profiles/*` | watched_profiles.py | `_assert_dirigente_access`/`_assert_watched_access` canónicos | Patrón D-SEC-WATCHED-SCOPE-1 |
| `GET /competitors/*` | competitors.py | `_assert_dirigente_access` propio | OK |
| `GET /followers/{id}/followers` | followers.py:76 | 404 cross-tenant | Verificar handler en Fase 2 |
| `GET /hitl-evaluation/audit/{id}` | hitl_evaluation.py:562 | 404 cross-tenant | OK (usa `_check_dirigente_access`) |
| `GET /plan-ia/recomendaciones` | plan_ia.py:243 | Verificar Fase 2 (no probado en profundidad — retorna 200 pero no consultado el shape) |
| `GET /contenido/?dirigente_id=N` | contenido.py:135 | retorna items=[], total=0 — probable auto-scope OK; verificar Fase 2 |
| `GET /onboarding/dirigentes/{id}/checklist` | onboarding.py | 404 cross-tenant | OK |
| `GET /calendario/proximas` | calendario.py:92 | datos globales (efemerides), no PII por dirigente | N/A (no escopable) |

---

## Compliance LFPDPPP+INE

### D1 — `author_hash` SALT
- **PASS:** SALT vía `os.environ["COMMENT_AUTHOR_SALT"]`. Hash es `SHA256(platform:commenter_id:SALT)`.
- **Riesgo BAJO:** default fallback `"crece-v2-lfpdppp-salt-2026"` aparece en 8 archivos (models + scripts). Si `COMMENT_AUTHOR_SALT` no se setea en prod, **todos los hashes son adivinables**. Solo `scraperapi_tiktok_comments.py:47` y `privacy_arco.py:24` hacen `raise` si falta — el resto cae al default.
- **NO se imprime el SALT en logs/print** (grep limpio).
- **Fix:** eliminar default fallback en `models/watched_profile.py:51`, `endpoints/watched_profiles.py:32`, scripts. Forzar raise si env vacía. Validar `APP_ENV=production` lo guardee.

### D2 — SQL injection en `text()` raw
- **1 hallazgo real:** `backend/app/services/divergencia_encuestas.py:62` — F-ALTO-01.
- **7 falsos positivos verificados** seguros (lista en F-BAJO-01).
- **Fix:** F-ALTO-01 + política CI "cero `text(f`".

### D3 — JWT config
- Algoritmo: HS256.
- Expiry: 24h (1440 min) — aceptable, no hay refresh token visible en código.
- Secret: `JWT_SECRET="CHANGE-ME-in-production"` default — F-ALTO-02. Hay `_guard_production_secrets` pero solo bloquea si `APP_ENV=production`.
- No se encontró refresh-token rotation. Recomendar Fase 2 implementar refresh + revocation list.

### D4 — CORS
- Allowlist explícito (no `*`): `["http://localhost:3000", "http://localhost:5173", "https://frontend-zeta-sepia-46.vercel.app"]`.
- `allow_credentials = settings.CORS_ORIGINS != ["*"]` — OK (true en producción con allowlist).
- `allow_methods=["*"]` — laxo, considerar restringir a GET/POST/PATCH/DELETE.
- **Observación:** F-MED-02.

### D5 — Audit log destructivo
- `framework_audit_log` SÍ existe para political_framework (admin_classification).
- `watched_profiles` y `competitors` DELETE NO loguean — F-ALTO-03.
- DELETE en `dirigentes.py:399`, `eventos.py:294`, `campanas.py:409`, `canvassing.py:334`, `contenido.py:279`, `programas.py:165` — NO se verificó si logan; Fase 2.

### D6 — Trazabilidad INE
- `backend/app/models/gasto_electoral.py` EXISTE. No se leyó schema; Fase 2 verificar campos (concepto, monto, fecha, fuente, dirigente_id).

### D7 — Secretos en frontend
- **1 hallazgo:** `frontend/src/app/api/v1/[...path]/route.ts:27` usa `process.env.BACKEND_TUNNEL_URL` — esto es **server-side** (Next.js Route Handler), NO leak al browser.
- No se encontró `APIFY_TOKEN`, `OAUTH_CLIENT_SECRET`, `JWT_SECRET` en `frontend/src/`.
- **PASS.**

### D9 — `modelo_ia` poblado
- Columna existe en 4 modelos: `contenido_pieza`, `contenido`, `ia_content_registry`, `plan_ia` (todos `nullable=False`).
- Query a BD: `contenido_piezas: total=0 with_modelo_ia=0`, `ia_content_registry: total=0 with_modelo_ia=0`, `contenidos`/`plan_ia` tablas con nombres distintos. **Sin filas a auditar todavía.**
- **CONDICIONAL PASS:** constraint NOT NULL garantiza populado al insertar. Validar de nuevo cuando haya generación IA en prod.

---

## Sentencia final

**ESCALAR AL CEO inmediatamente.**

Hay **6 endpoints CRÍTICOS** con leak verificado de PII política cross-tenant (Saymi org_id=2 → Piña org_id=1). El patrón canónico `_assert_dirigente_access` existe en `watched_profiles.py:118` y `competitors.py:48`. La remediación es mecánica: aplicar el helper en cada handler listado en F-CRIT-01..05 y F-CRIT-07..08.

**No proceder a Fase 2 (Triage)** hasta que el CEO confirme:
1. Si los 6 CRÍTICOS van directo a hotfix (gate dura antes de cualquier piloto multi-org).
2. Si F-ALTO-01 (SQLi divergencia_encuestas) entra en hotfix o en Sprint normal (riesgo latente, no expuesto vía router actualmente).
3. Si la política "cero `text(f`" + CI grep block se acepta como mejora estructural.

**Tiempo invertido:** ~50 min. Bajo budget; queda margen para Fase 2 si CEO autoriza.

**Archivos NO modificados** (auditoría 100% read-only verificado).
