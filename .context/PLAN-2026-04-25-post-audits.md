# Plan post-auditorías 2026-04-25 · CRECE v2

> **Origen:** diagnóstico paralelo 5 agentes (backend+DB, frontend+git, lectura 7 audits, planes vs realidad, recuperación memoria).
> **Score global audits:** 62/100 · Seguridad 50 · Hardening IA 52 · más bajos.
> **Branch activa:** `feat/phase-b-pesos-editables` · 4 commits ahead main · 7 archivos sin commit · BD live con 4,156 posts 100% clasificados.
> **Estado preexistente confirmado DONE:** D-23-G' Days 1-4 · D-23-H Phase B Days 1+2 · Backfill IA · Ollama Coolify activo en runtime.
> **Disciplina §9.8:** próxima ventana ≈ 2026-05-20. Bugs críticos = hotfix directo. Cambios estructurales D-01..D-24 esperan §9.8.

---

## Fase 0 · Captura (commits sin perder lo hecho) — HOY

> Trabajo en working tree desde audits del 25-abr; cero código nuevo, solo persistir lo que ya está en disco.

### Sprint 0.1 · Commit hardening seguridad backend (~30 min)

**Files:** `backend/app/api/v1/endpoints/planes.py` · `backend/app/main.py` · `backend/app/schemas/plan_ia.py`
**Cubre:** A-FULL H-01 (IDOR org_id) · H-06 (rate limit 5/h) · C-01 (VedaElectoralMiddleware) · C-02 (Sentry PII scrub)
**Acceptance:**
- `git diff HEAD~0 -- backend/` clean post-commit
- `pytest backend/tests/api/test_planes.py -v` verde (si falla por org_id, ajustar fixtures)
- Mensaje commit: `fix(security): hardening AUDIT 2026-04-25 · org_id scoping + rate limit + Veda + Sentry PII`
**Bloquea:** nada · listo

### Sprint 0.2 · Commit ops Coolify Ollama (~10 min)

**Files:** `docker-compose.yml` · `backend/app/services/plan_generator.py`
**Cubre:** decisión CEO 2026-04-25 (libera RAM Mac Mini) + streaming refactor (`stream:True` + `keep_alive 30m` + timeout 1h + `num_predict 4096`)
**Acceptance:**
- Containers ya corren con esta config (env verificado: `OLLAMA_BASE_URL=http://163.245.208.96:11434`)
- Mensaje commit: `chore(ops): Ollama Coolify migration · streaming + keep_alive 30m + timeout 1h`
**Bloquea:** nada

### Sprint 0.3 · Commit bump Next.js (~5 min)

**Files:** `frontend/package.json` · `frontend/package-lock.json`
**Cubre:** CVE-2026 Next 14.2.21 → 14.2.35 (Authorization Bypass CVSS 9.1)
**Acceptance:**
- `cd frontend && npm install` ya aplicado (lock al día)
- `npx tsc --noEmit` clean (verificado)
- Mensaje commit: `chore(deps): bump Next.js 14.2.35 (CVE-9.1 Authorization Bypass)`

### Sprint 0.4 · Actualizar redirect plan + abrir PR Phase B (~15 min)

**Files:** `.context/PLAN-current.md` (cambiar `ACTIVE:` a este archivo) · `.context/STATUS.md` (anotar Phase B mergeable)
**Acción:** push branch + `gh pr create` con cuerpo documentando los 4 commits Phase B + 3 commits hardening
**Acceptance:**
- PR creado con CI verde
- `PLAN-current.md` redirige a este plan
**Bloquea:** Sprint 0.1, 0.2, 0.3

---

## Fase 1 · Demo blockers (pre-piloto Piña + Ballesteros) — 1-2 días

> Demo agendable cuando los 4 ítems cierren. Máynez fuera de demo si Sprint 1.1 no rescata su data.

### Sprint 1.1 · Diagnóstico Máynez handles + decisión incluir/excluir (~1h)

**Files:** crear `.context/diagnostico-maynez-2026-04-26.md`
**Acción:**
1. `SELECT username, platform, status, last_scraped FROM social_profiles WHERE dirigente_id=7;`
2. Verificar manualmente cada handle vivo en navegador (X, IG, FB, TT, YT)
3. Si activos: lanzar `scrape_profile.delay(profile_id)` per-platform y revisar logs
4. Si inactivos: documentar y escalar
**Acceptance:**
- 5 handles verificados (vivo/muerto/privado)
- Decisión documentada: incluir Máynez en demo o sustituir por Solano
- Si vivo: ≥10 posts scraped post-diagnóstico
**Cierra:** B-23-06

### Sprint 1.2 · Refrescar scrapers 7 dirigentes activos (~1.5h)

**Files:** ninguno; ejecución de tasks Celery existentes
**Acción:** disparar `scrape_all_profiles.delay()` o per-dirigente; monitorear Flower
**Acceptance:**
- `MAX(posted_at) FROM social_posts` ≥ ayer
- Hero KPI "Actividad Alineada" deja de estar vacío en `/dashboard/dirigentes/8`
- Posts nuevos pasan por classifier `target_politico` (background backfill)
**Cierra:** B-23-07

### Sprint 1.3 · Generar 1 Plan IA Ballesteros smoke real (~30 min + 5-7 min inferencia)

**Files:** ninguno; smoke test contra endpoint
**Acción:**
1. Pre-warm Coolify: `curl -X POST http://163.245.208.96:11434/api/generate -d '{"model":"gemma3:12b","prompt":"hola","stream":false,"keep_alive":"30m"}'` (~34s cold-start)
2. Disparar endpoint Plan IA Ballesteros vía UI o `curl POST /api/v1/dirigentes/8/planes/generar`
3. Validar respuesta llegó y plan persistido en BD
**Acceptance:**
- Nuevo row en `planes_ia` para `dirigente_id=8` post-2026-04-25
- `LENGTH(contenido) > 500` chars
- Coolify `/api/ps` muestra modelo cargado durante inferencia
**Bloquea:** Sprint 0.2 commiteado · Coolify reachable

### Sprint 1.4 · Decisión CEO Máynez en demo (~5 min decisión)

**Acción:** CEO responde A o B basado en Sprint 1.1
- (A) Máynez incluido con disclaimer "activación en proceso"
- (B) Sustituir Máynez por Solano (id=2 · 8 perfiles, datos completos)
**Acceptance:** decisión registrada en `DECISIONS.md` como D-23-I

---

## Fase 2 · Seguridad bloqueante LFPDPPP/INE — 2-3 días

> A-02 + A-01 son riesgos legales reales con piloto comercial vivo. C-03 es estructural §9.8.

### Sprint 2.1 · A-02 ARCO endpoint auth (~1.5h)

**Files:** `backend/app/api/v1/endpoints/arco.py` · `backend/tests/api/test_arco.py`
**Problema:** `POST /arco/exercise` sin auth → DELETE masivo posible vía LFPDPPP
**Acción:**
1. Test que verifica 401 sin token
2. Decorator `Depends(get_current_user)` + verificación org_id matching
3. Audit log de quién ejerció derecho ARCO + sobre qué entidad
**Acceptance:**
- 401 sin token · 403 con token de otra org · 200 con dueño legítimo
- Row en `audit_log` por cada request
**Cubre:** AUDIT-SEGURIDAD A-02

### Sprint 2.2 · A-01 trusted_hosts fix (~30 min)

**Files:** `backend/app/main.py`
**Problema:** `TrustedHostMiddleware(allowed_hosts=["*"])` permite IP spoof en `X-Forwarded-For` → bypass rate-limit en `/login`
**Acción:** lista explícita de hosts (incluyendo Cloudflare tunnel + Vercel), o usar `client.host` directo en limiter key
**Acceptance:**
- Test rate-limit `/login` 5 attempts → 429 (no se puede saltar con header spoof)
**Cubre:** AUDIT-SEGURIDAD A-01

### Sprint 2.3 · A-04 JWT refresh + revocación (~3h backend + 1-2h frontend · CEO D-23-J: AHORA con cuidado)

**Files:** `backend/app/core/auth.py` · `backend/app/api/v1/endpoints/auth.py` · `backend/tests/api/test_auth.py` · `frontend/src/lib/api/auth.ts` · `frontend/e2e/auth-flow.spec.ts`
**Problema:** JWT 24h sin refresh ni revocación → sesión robada vive 24h sin posibilidad de invalidar
**Decisión CEO 2026-04-25:** D-23-J = AHORA, no se difiere a §9.8. Ejecutar con red de seguridad por riesgo medio-alto al login.
**Red de seguridad obligatoria:**
1. Feature flag `JWT_REFRESH_ENABLED=false` por default; activar primero en staging, luego prod.
2. E2E Playwright cubriendo: login → access expira → refresh exitoso → logout → access revocado → refresh revocado → relogin.
3. Test backend cubriendo cada path: `test_login_returns_both_tokens`, `test_refresh_rotates_access`, `test_logout_blacklists_jti`, `test_revoked_token_denies_access`.
4. Rollout monitorado: 24h en staging con observabilidad activa antes de prod.
5. Plan de rollback documentado: `JWT_REFRESH_ENABLED=false` revierte a comportamiento actual sin downtime.

**Acción técnica:** access tokens 15min + refresh tokens 7d + denylist Redis para revocación (key `jwt:revoked:{jti}` con TTL = lifetime restante)
**Acceptance:**
- Login devuelve `access_token` (15min) + `refresh_token` (7d)
- `POST /auth/refresh` rota access · revoca refresh anterior
- `POST /auth/logout` añade JTI access + refresh a denylist
- E2E Playwright verde end-to-end
- Feature flag activa solo tras 24h staging clean
**Cubre:** AUDIT-SEGURIDAD A-04

### Sprint 2.4 · H-07 Ollama firewall VPS (~1h CEO directo)

**Files:** Coolify UI / SSH al VPS · NO toca código
**Problema:** puerto `11434` Coolify expuesto sin auth → cualquiera puede usar gemma3:12b
**Acción CEO:**
1. SSH al VPS, agregar regla iptables: solo accept desde IP del Mac Mini
2. O: configurar reverse proxy Coolify con basic auth + agregar credenciales a `OLLAMA_BASE_URL`
**Acceptance:**
- `curl http://163.245.208.96:11434/api/tags` desde IP no-autorizada → timeout/403
- Backend CRECE sigue funcionando
**Asignado:** CEO directo

---

## Fase 3 · Calidad sostenida — 1 semana

### Sprint 3.1 · xlsx → exceljs migration (~2h)

**Files:** `frontend/package.json` · cualquier `*.tsx` que importe `xlsx`
**Problema:** `xlsx` tiene CVE sin fix oficial · `exceljs` es alternativa mantenida
**Acción:** `npm uninstall xlsx && npm install exceljs` + reescribir 3-5 callsites
**Acceptance:** todos los exports Excel siguen funcionando · `npm audit` sin críticos
**Cubre:** AUDIT-CALIDAD finding #1

### Sprint 3.2 · Dark mode opción A · instalar `next-themes` (~3-4h · CEO D-23-K)

**Files:** `frontend/src/app/layout.tsx` · `frontend/src/components/theme-provider.tsx` (nuevo) · `frontend/src/components/theme-toggle.tsx` (nuevo) · ajustes en navbar/header
**Acción:**
1. `npm install next-themes`
2. ThemeProvider envolviendo `<body>` con `attribute="class"` + `defaultTheme="system"` + `enableSystem`
3. Componente toggle (sun/moon icon) en navbar derecho usando shadcn `DropdownMenu`
4. Audit visual: revisar las 140+ clases `dark:*` existentes — mantener las correctas, ajustar las que rompan en modo oscuro
5. Verificar contraste WCAG AA básico en modo oscuro (no obligatorio per D-23-L pero buena práctica)
**Acceptance:**
- Toggle funcional · persistencia en localStorage
- Modo oscuro respeta `prefers-color-scheme` por default
- Sin flash de tema incorrecto (FOUC) al cargar página
- Screenshot Playwright modo claro + oscuro de 3 páginas core (dashboard, ficha dirigente, evaluación)
**Cubre:** AUDIT-DISENO finding crítico
**Nota:** post-demo, no bloquea piloto Ballesteros

### Sprint 3.3 · A11y sprint formal · DESCARTADO (CEO D-23-L)

**Razón:** información de CRECE es **particular del dirigente, no institucional pública**. LGAIPG art. 11 fracc. VII aplica a info pública institucional → no obliga a CRECE.
**Decisión:** sin sprint dedicado, sin meta WCAG AA obligatoria, sin Lighthouse ≥90.
**Mantener como buena práctica (no sprint):** semántica HTML básica, navegación teclado funcional en login y dashboard principal. Se atiende oportunísticamente cuando se toque cada componente, no como bloque dedicado.
**Cubre:** decisión D-23-L · AUDIT-A11Y se archiva como referencia, no como deuda activa

### Sprint 3.4 · Responsive login mobile + touch targets (~1h)

**Files:** `frontend/src/app/login/page.tsx` (o equivalente)
**Acción:** wordmark `text-4xl` → responsive · touch targets 36-40px → 44px iOS-compliant
**Acceptance:** screenshot mobile <375px sin overflow · Lighthouse mobile a11y ≥ 90
**Cubre:** AUDIT-RESPONSIVE finding crítico

---

## Fase 4 · Hardening continuo + Phase C — §9.8 ventana

### Sprint 4.1 · Pre-warm Coolify Ollama scheduled (~1h)

**Files:** `backend/app/workers/tasks.py` (existe `ollama_prewarm`)
**Acción:** verificar Celery beat schedule lo dispara cada 25 min (justo antes de keep_alive 30m timeout) · si beat unhealthy, diagnosticar
**Acceptance:**
- `/api/ps` siempre muestra `gemma3:12b` cargado
- Próxima generación de plan no paga cold-start
**Hallazgo previo:** `crece-celery-beat` actualmente unhealthy

### Sprint 4.2 · Cierre formal B-23-03 + DECISIONS D-23-H (~30 min docs)

**Files:** `.context/BLOCKERS.md` · `.context/DECISIONS.md`
**Acción:** mover B-23-03 a "Resueltos" · agregar D-23-H reframe Phase B como decisión persistida
**Acceptance:** consistency BLOCKERS ↔ DECISIONS ↔ STATUS

### Sprint 4.3 · Phase C plan (override per-post manual) — diferido §9.8

**Files:** crear `.context/PLAN-D-23-I-phase-C-override.md`
**Estado:** plan no escrito · escribir solo si CEO valida feature en §9.8 review
**Acceptance:** plan completo con 4-5 días estimados · listo para sprint dedicado post-mayo

### Sprint 4.4 · C-03 RLS runtime enforcement — §9.8

**Files:** `backend/app/api/dependencies.py` · todos los endpoints
**Problema:** endpoints usan `get_db` no `get_db_rls` → RLS sin enforcement
**Estado:** cambio invasivo · no hotfix · diferido §9.8 2026-05-20
**Cubre:** AUDIT-SEGURIDAD C-03

---

## Tabla resumen ejecutivo

| Fase | Sprints | Total | Hoy/Esta sem | Bloqueante demo |
|---|---:|---:|---|---|
| 0 · Captura commits | 4 | ~1h | ✅ HOY | sí (orden trazabilidad) |
| 1 · Demo blockers | 4 | ~3-4h + 5min decisión | esta sem | sí |
| 2 · Seguridad LFPDPPP | 4 | ~5h + CEO firewall | esta sem | parcial (A-02 sí) |
| 3 · Calidad sostenida | 3 (3.3 descartado) | ~6-8h | próxima sem | no (post-demo) |
| 4 · Hardening + §9.8 | 4 | ~1.5h + diferidos | mes | no |

**Total acotable:** ~20h trabajo + 3 decisiones CEO + 1 acción CEO directa firewall.

## Decisiones pendientes consolidadas

| ID | Pregunta | Sprint asociado | Urgencia |
|---|---|---|---|
| D-23-I | Máynez | ✅ B · fuera del demo, accesible solo si se requiere |
| D-23-J | JWT refresh | ✅ AHORA con red de seguridad (feature flag + E2E + 24h staging) |
| D-23-K | Dark mode | ✅ A · instalar `next-themes` post-demo |
| D-23-L | A11y formal | ✅ FUERA · info particular, no institucional pública |

## Riesgos transversales

| Riesgo | Mitigación |
|---|---|
| Coolify cold-start 34s degrada UX Plan IA | Sprint 4.1 prewarm scheduled |
| Sprint 1.2 dispara load excesivo en BD | lotes per-dirigente, no `scrape_all` simultáneo |
| PR Phase B + hardening en mismo branch genera conflicto al merge | Sprint 0.4 abre 2 PRs separados (Phase B + hardening) si CEO prefiere atomicidad |
| Sprint 2.3 (JWT refresh) toca contratos → frontend regression | Cubrir con E2E Playwright antes de mergear |
| Reinicios Docker durante Phase 2 matan plans inflight | Cero `docker compose restart` sin OK CEO; cambios via env vars hot-reload donde aplique |

## Trazabilidad

- Plan supersedido `.context/PLAN-current.md` apuntaba a `PLAN-D-23-G-actividad-alineada-2026-04-24.md` (cerrado) → este plan toma el ACTIVE
- Audits fuente: `.context/AUDIT-{FULL,FUNCIONAL,CALIDAD,DISENO,RESPONSIVE,A11Y,SEGURIDAD}-2026-04-25.md`
- Branch base: `feat/phase-b-pesos-editables` ahead 4 commits de main
