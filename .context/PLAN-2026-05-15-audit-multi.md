# PLAN-2026-05-15 — Auditoría multi-dimensión CRECE v2

**Origen:** CEO 2026-05-15 02:00 — "ya hicimos audits UX/UI, faltan info/estructura/lógica. Encuestas: faltan municipios + comparativa se amontona. Cómo usamos todas nuestras skills".

**Restricción dura:** NO alterar resultados actuales (datos en BD, métricas ya scrapeadas, sesiones, deploys). SELECT-only en BD durante diagnóstico. Branch separada para fixes.

**Branch:** `audit/multi-2026-05-15` (a crear desde `feat/phase-b-pesos-editables` HEAD=`48fadf5`).

---

## Lo ya auditado (no toco)

| Ámbito | Cuándo | Evidencia |
|---|---|---|
| UX/UI fantasmas + war-room | 2026-05-14 | Sprints 0/1/2/4 cerrados, deploy zeta-sepia-46 |
| Multi-tenant scope `watched_profiles` | 2026-05-14 | Helpers `_assert_dirigente_access`, `_assert_watched_access` |
| Data quality pipeline 4 capas (followers) | 2026-05-13 | Commit `2a3ab2d` |
| Cross-audit Gemini en planes IA | 2026-05-09 (cierre) | CD oficial |
| Cumplimiento §9.8 día 30 piloto | 2026-05-12 | DECISIONS.md |
| Sprint NLP matriz v2 53 reglas | 2026-04-14 | PR #12 |

---

## Dimensiones pendientes (6)

### A · Información / veracidad (PRIORIDAD ALTA — incluye bugs reportados)

**Bugs ya reportados por CEO (2026-05-15):**
- **A1 · encuestas: municipios/alcaldías no se ven al seleccionar.** Bug observado en módulo encuestas; falta identificación geográfica visible al elegir filas.
- **A2 · encuestas: comparativa "todas" se amontona.** Overlap visual cuando se comparan múltiples; UX inutilizable.

**Otros checks de info:**
- A3 · sentiment counts consistentes entre `/aceptacion/overview`, `/aceptacion/{dirigente_id}`, `/aceptacion/fantasmas` (mismas filas, mismos totales).
- A4 · IPD scoring: fórmula declarada en código vs valor mostrado en UI coinciden para los 6 dirigentes reales.
- A5 · `data_source` nunca `'UNKNOWN'` en `social_followers`, `social_metrics`, `competitor_metrics_monthly`.
- A6 · coords MX en bounds (lat 14.5-32.7, lon -118.4 a -86.7) en `dirigentes`, `eventos`, `puntos_canvassing`.
- A7 · followers totales por dirigente = suma `social_accounts.followers_count` agregada por plataforma.
- A8 · `competitor_metrics_monthly.followers_total` refleja último scrape (verificable contra `competitor_profiles.last_scraped_at`).
- A9 · `modelo_ia` poblado en TODO contenido IA-generado (`contenido_pieza`, `plan_ia`).

### B · Estructura / RBAC (PRIORIDAD ALTA — patrón ya identificado en watched_profiles)

**Hipótesis:** El leak multi-tenant cerrado en `watched_profiles` existe también en otros endpoints. DECISIONS.md ya lo flageó.

**Mapeo sospechosos:**
- B1 · `/aceptacion/*` endpoints distintos de fantasmas (overview, dirigente, por-plataforma, sugerencias).
- B2 · `/social/*` (followers, posts, comments).
- B3 · `/planes_ia/*` (lectura, listing).
- B4 · `/dirigentes/{id}` directo (sin filtro por org).
- B5 · `/competitors/*` (acabo de reescribir — verificar `_assert_competitor_access` aplicado en TODOS los handlers).
- B6 · `/diagnostico/*`, `/diferenciadores/*`, `/foda/*`.

**Otros checks RBAC:**
- B7 · RoleChecker presente en endpoints write-mode (POST/PATCH/DELETE).
- B8 · Pydantic schemas vs SQLAlchemy models (drift de campos, nullability mismatch).
- B9 · Endpoints que aceptan `dirigente_id` query param sin validación org.

### C · Lógica / reglas de negocio

- C1 · Veda mode: ¿qué endpoints/jobs se pausan cuando `OrganizationFlag.veda_activa=true`?
- C2 · Plan IA: cascada Claude → Gemini → Ollama. Cuándo cae a cada fallback. Logging de qué modelo se usó.
- C3 · Mapeo comments → aceptación: matriz v2 53 reglas aplicadas correctamente en `/aceptacion/overview`.
- C4 · Cron jobs (Celery beat): qué tareas corren, cuándo, idempotencia (re-runs no rompen).
- C5 · Cálculo de IPD (fórmula): coherencia entre 7 plataformas y peso por seguidor.

### D · Seguridad / compliance (LFPDPPP + INE)

- D1 · LFPDPPP: `author_hash` SHA256 + SALT consistente; SALT no logueado; no PII directa persistida sin consentimiento.
- D2 · SQL injection en `text()` raw queries (binding de params via `:name`, no f-strings).
- D3 · JWT: expiry razonable, refresh flow, scope-bound tokens.
- D4 · CORS allowlist explícito (no `*`).
- D5 · Audit log para ops sensibles: delete watched_profile, delete competitor, plan IA generate.
- D6 · Trazabilidad gastos electorales INE: `gasto_electoral` con campos requeridos (concepto, monto, fecha, fuente).
- D7 · Secretos: `APIFY_TOKEN`, `BACKEND_TUNNEL_URL`, OAuth tokens no en client bundle (Next.js).
- D8 · CFDI: si hay módulo de facturación en CRECE (no debería) verificar.
- D9 · IA-generated content: etiquetado `modelo_ia` cumple requisito INE de etiquetado IA.

### E · Performance

- E1 · EXPLAIN ANALYZE en `/aceptacion/overview` (endpoint pesado).
- E2 · EXPLAIN ANALYZE en `/competitors/{id}` (recién creado).
- E3 · N+1 detection: planes_ia listing, social_followers detalle.
- E4 · Indexes faltantes (postgres `pg_stat_user_indexes` + `pg_stat_user_tables.seq_scan` ratio).
- E5 · Next.js bundle size por route (`.next/analyze`).
- E6 · TTI/TTFB en pages calientes (Lighthouse via Playwright).

### F · Coverage (no crítico esta sesión, audit ligero)

- F1 · pytest coverage backend por módulo (sin re-correr suite completa — leer reporte existente).
- F2 · E2E Playwright: qué features tienen smoke vs no.
- F3 · Migrations: idempotencia (alembic downgrade + upgrade contra DB snapshot).

---

## Skills/agents asignados

| Dimensión | Agent primario | Modo |
|---|---|---|
| A · info | `root-cause-analyst` (bugs A1+A2) + `quality-engineer` (A3-A9) | A1+A2 implementación; resto read-only |
| B · RBAC | `Explore` (mapeo) → `system-architect` (análisis) | read-only |
| C · lógica | `func-audit` (custom agent del proyecto) | read-only |
| D · compliance | `security-engineer` + `government-audit` (paralelos) | read-only |
| E · performance | `performance-engineer` + `database-architect` | read-only (EXPLAIN sin alterar) |
| F · coverage | `quality-engineer` (continuación de A) | read-only |
| Cross-audit | `/gemini review` del propio plan + reportes | read-only |

---

## Cross-audit Gemini (2026-05-15 04:30) — AJUSTES APLICADOS

Gemini revisó este plan v1 y devolvió veredicto **AJUSTAR** con 5 críticas válidas. Integradas abajo:

| # | Crítica Gemini | Ajuste aplicado |
|---|---|---|
| 1 | Falta auditoría cuotas Apify/rate-limits | Añadido a A (info): A10 · estado MTD Apify, A11 · rate-limits scrapers |
| 2 | Falta auditoría connection pooling + deadlocks | Añadido a E: E7 · pool config SQLAlchemy, E8 · Celery deadlock potencial |
| 3 | Sobre-engineering 8 agentes paralelos | **REDUCIDO a 3 agentes paralelos**: (1) Info+Data, (2) RBAC+Security+Compliance unidos, (3) Perf+DB. Logic+Coverage = sub-tareas de agente 1. |
| 4 | Prioridad invertida (UI encuestas antes que RBAC leak) | **Reordenado:** Fase 0 (encuestas) **MOVIDA al final** como Fase 4. RBAC leak es crítico — va PRIMERO. |
| 5 | Playwright contra Vercel = riesgo alteración BD | **Cambiado:** validación Fase 1 vía `curl` + `psql SELECT` directo. Playwright solo lectura DOM (no acciones POST/PATCH). |
| 5b | `EXPLAIN ANALYZE` ejecuta query → contención | **Cambiado:** usar `EXPLAIN` (sin ANALYZE) en queries pesadas. ANALYZE solo en queries verificadamente baratas (<10ms estimated). |

**Orden NUEVO (post-ajuste):**

### Fase 1 (NUEVA) · Audit RBAC + Compliance + Security (CRÍTICO)

Antes era Fase 1 B + Fase 3 D. Ahora unido por ser el riesgo más alto (scope leak en producción).

### Fase 2 (NUEVA) · Audit Info + Data Integrity + Lógica + Coverage

Antes era Fase 1 A + Fase 3 C + Fase 3 F. Unido en 1 agente.

### Fase 3 (NUEVA) · Audit Performance + DB

Antes era Fase 1 E. Sin cambios.

### Fase 4 (NUEVA) · Triage + Fix encuestas A1+A2 + Plan remediación

Antes era Fase 0 (encuestas) + Fase 2 (triage) + Fase 4 (plan remediación). Combinado al final.

---

## Plan secuenciado v2 (ajustado post-Gemini)

### Fase 1 · Audit RBAC + Security + Compliance (1-1.5h) — CRÍTICO PRIMERO

**Objetivo:** Mapear scope leak multi-tenant en endpoints fuera de `watched_profiles` + LFPDPPP + cumplimiento INE en código.

**Agent único:** `security-engineer` (que también tiene contexto LFPDPPP+SAT+COFEPRIS y entiende multi-tenant).

**Scope:**
- B1-B9 (todos los sospechosos de scope leak)
- D1-D9 (LFPDPPP, SQL injection, JWT, CORS, audit log, trazabilidad INE)

**Validación dura por finding:**
- Si flagea endpoint sospechoso, validar con curl real (TOKEN_A vs dirigente_de_B → debe ser 403).
- SI 200: CRÍTICO + escalar inmediato al CEO.

**Output:** `.context/AUDIT-SECURITY-RBAC-2026-05-15.md`

### Fase 2 · Audit Info + Data + Lógica + Coverage (1-1.5h)

**Agent único:** `quality-engineer`.

**Scope:**
- A3-A11 (data integrity + cuotas Apify)
- C1-C5 (veda mode, plan IA, modelo_ia, matriz v2)
- F1-F3 (coverage check ligero)

**Output:** `.context/AUDIT-INFO-LOGIC-2026-05-15.md`

### Fase 3 · Audit Performance + DB (45 min)

**Agent único:** `performance-engineer`.

**Scope:**
- E1-E8 (EXPLAIN sin ANALYZE en queries pesadas; ANALYZE solo en baratas <10ms)
- E7 connection pool SQLAlchemy
- E8 deadlocks Celery
- Indexes via `pg_stat_user_indexes`

**Output:** `.context/AUDIT-PERF-2026-05-15.md`

### Fase 4 · Triage + Fix encuestas + Plan remediación (1.5h)

**Pasos:**
1. **Triage** (15 min): consolidar 3 reportes en `.context/AUDIT-TRIAGE-2026-05-15.md`. Si severity=CRÍTICO encontrado en Fase 1, ESCALAR ANTES de continuar.
2. **Fix encuestas A1+A2** (45 min): identificar módulo (no es ruta "encuestas" directa — probablemente `/dashboard/aceptacion/*` o `/dashboard/diagnostico-tier2/*` con comparativa). Reproducir local. Fix. Validación visual con Playwright en MODO LECTURA contra prod (sin POST/PATCH/DELETE).
3. **Plan remediación** (30 min): `.context/AUDIT-REMEDIACION-2026-05-15.md` con sprints concretos para findings NO arreglados aún.

**Output Fase 4:**
- Commit `fix(encuestas): municipios visibles + comparativa overlap` (si A1+A2 son frontend-only).
- 1 archivo `.context/AUDIT-TRIAGE-*.md`.
- 1 archivo `.context/AUDIT-REMEDIACION-*.md`.

---

## Garantías de no-alteración

1. Branch `audit/multi-2026-05-15` — todos los commits aquí, cero merge hasta luz verde del CEO.
2. Agentes Fase 1 y 3 reciben prompt explícito "no escribir archivos, no ejecutar UPDATE/DELETE en BD".
3. Backups previos: NO requiere backup BD adicional porque Fase 0-3 son read-only en BD; Fase 0 sí modifica frontend pero en branch separada.
4. Vercel: NO desplegar la branch de audit a prod. Si se requiere preview deploy, usar branch alias separado.
5. Cron Celery NO pausar (los jobs siguen poblando datos; el audit los lee en momento dado).
6. Reportes en `.context/` nunca tocan código.

---

## Criterios de cierre

Esta auditoría se considera CERRADA cuando:
- ✅ Bugs encuestas A1+A2 arreglados y validados Playwright contra Vercel.
- ✅ 6 reportes diagnóstico generados (`AUDIT-INFO`, `AUDIT-RBAC`, `AUDIT-PERF`, `AUDIT-LOGIC`, `AUDIT-SECURITY`, `AUDIT-COMPLIANCE`).
- ✅ Triage consolidado con severidad.
- ✅ Plan remediación entregable al CEO.
- ✅ Cross-audit Gemini ejecutado contra los reportes (catch blind spots).
- ✅ `.context/STATUS.md` y `DECISIONS.md` actualizados.

---

## Out of scope explícito

- Fix de findings NO-bug-reportado en esta sesión (solo plan).
- Refactor de arquitectura (no es audit).
- Re-correr suite pytest completa (audit ligero de coverage solo).
- Touch a competitors_metrics_monthly recién poblado (es resultado válido, no se altera).
- Touch a `feat/phase-b-pesos-editables` mainstream (audit en branch aparte).

---

## Riesgos

| Riesgo | Mitigación |
|---|---|
| Findings críticos en producción que requieran fix inmediato (ej. scope leak filtrando PII) | Escalar a CEO en Fase 2 antes de continuar Fase 3 |
| Costo tokens excesivo (3 agentes Explore concurrentes) | Cap budget tokens por agent + prompts focalizados |
| Falso positivo en RBAC mapping | Cross-validar con curl tests reales antes de reportar CRÍTICO |
| Bugs encuestas más profundos que UI (afectan datos) | Si Fase 0 detecta corruption en BD, parar y reportar al CEO |
