# PLAN-2026-05-15 · Sprints dedicados post-quick-wins

**Origen:** CEO 2026-05-15 — "Ok, si, pero quiero hacer los sprints dedicados tambien. Los vemos al final que termines, te parece?"

**Disparado por:** `/sprint-review` del CEO. Luz verde para todo. Reportar al final.

**Restricciones operativas vigentes:**
- "Eficiencia y Calidad > tiempo de entrega" pero NO sobre-ingeniería (regla CEO, sesión 2026-05-15)
- Ollama dormant — solo se prende cuando haya VPS (decisión CEO 2026-05-15)
- No tocar Docker volumes ni datos sin confirmación explícita en sesión (regla CLAUDE.md global)
- LFPDPPP: hash público OK, PII directa NO sin consentimiento
- Cache hygiene: archivos estables (DECISIONS.md, ARCHITECTURE.md) **NO modificar mid-sesión**

**Branch:** `feat/phase-b-pesos-editables` (mismo) — los sprints van como commits chicos, no nueva branch (audit ya está merged).

---

## Lo ya cerrado en esta sesión (no toco)

| Sprint | Estado | Commit |
|---|---|---|
| Audit multi-dimensión 4 fases | CLOSED | merged a `feat/phase-b-pesos-editables` |
| Hotfix 7 endpoints RBAC + SQLi + JWT guard | CLOSED | `0f232ea` |
| Fix encuestas A1+A2 | CLOSED | `15b4e39` |
| Fix Saymi audiencia 86.8% (KPI Tu Audiencia) | CLOSED | merged |
| Scraper light Apify FB (Ivette + Susana) | CLOSED | merged |
| Quick-wins UX 9 puntos (Gemini cross-audit drawer + perfil) | CLOSED | hoy (último commit) |
| A3 ALTO fix overview vs ia-summary mismatch | CLOSED | hoy |

---

## Sprints dedicados a ejecutar (priorizados por impacto + reversibilidad)

### Tanda 1 · Data quality + ops hygiene (~5-6h, bajo riesgo, alto valor)

#### **S2 · Engagement = 0 con 30 posts (Gemini A1.4)**
- **Síntoma:** Card "Engagement (7d)" muestra 0 cuando Posts=30. CEO observó en perfil Saymi.
- **Hipótesis:** (a) cálculo está vivo pero las plataformas no entregan reactions/comments; (b) cálculo bugueado (división por cero, NULL coalesce mal); (c) ventana 7d no captura posts con interacción.
- **Diagnóstico (no fix todavía):**
  - Leer `backend/app/services/*engagement*` o equivalente.
  - SQL: `SELECT platform, COUNT(*), SUM(reactions+comments+shares) FROM social_posts WHERE dirigente_id=3 AND published_at > NOW() - INTERVAL '7 days'`
  - Validar si reactions están en cero (data issue) o si el cálculo es el problema.
- **Fix posibles:**
  - Si data: tooltip "Sincronizando — métricas se actualizan cada 4h". NO inventar números.
  - Si cálculo: corregir fórmula + agregar nullable counter (D-23-E P3).
- **Criterio aceptación:** un dirigente con posts y reactions reales muestra un % > 0; un dirigente sin reactions muestra "—" + tooltip explicativo (no "0").
- **Archivos sospechosos:** `backend/app/api/v1/endpoints/dashboard.py`, `backend/app/services/diagnostic_service.py`, `frontend/src/app/dashboard/dirigentes/[id]/page.tsx` (donde se muestra).
- **Estimado:** 1h diagnóstico + 1h fix.

#### **S9 · IPD stale recalc detector (audit A4)**
- **Problema:** IPD score (6.7 mostrado) puede no reflejar datos actualizados.
- **Solución mínima:** management command `python manage.py audit_ipd_stale` que liste dirigentes con `ipd_calculated_at < NOW() - 7 days`. NO recalcular automático (riesgo de side effects). Reportar al CEO la lista.
- **Criterio aceptación:** `docker exec crece-backend python -m backend.scripts.audit_ipd_stale` imprime tabla con dirigente_id, full_name, ipd_score, days_stale.
- **Estimado:** 1h.

#### **S10 · Back-off scrapers (audit A11)**
- **Problema:** scrapers nativos pueden golpear rate limit sin retry. Si IG/X devuelve 429, el job falla.
- **Solución mínima:** decorador `@with_backoff(retries=3, base_delay=5)` en `update_profile_stats` de cada scraper.
- **Criterio aceptación:** test unitario que simula 429 en intento 1+2, success en intento 3.
- **Estimado:** 1.5h.

#### **S7 · F-PERF-01 N+1 list_dirigentes**
- **Problema:** endpoint `/dirigentes/` hace 1 query por dirigente para `social_accounts` (N+1).
- **Solución:** eager load `selectinload(Dirigente.social_accounts)` en la query principal.
- **Validación:** `EXPLAIN` antes/después; debe pasar de N+1 queries a 1+1.
- **Criterio aceptación:** profile log muestra 2 queries (no N+1).
- **Estimado:** 1h.

#### **S5 · Auto-refresh mensual competitor_metrics (Celery beat)**
- **Problema:** `competitor_metrics_monthly` se llena manualmente. Saymi tiene 1 medición, sin tendencia.
- **Solución mínima:** Celery beat task `scrape_competitors_monthly` que corre el 1° de cada mes, llama `scrape_competitors_light_apify.py` para todos los `competitor_profiles` activos con platform=FACEBOOK.
- **Cap:** budget Apify $0.50 por run para no quemar el free tier.
- **Criterio aceptación:** beat schedule visible en `celery beat -l info`, task se puede invocar manualmente via `celery call`.
- **Estimado:** 1.5h.

### Tanda 2 · Compliance (~3-4h, medio riesgo)

#### **S8 · F-ALTO-03 audit log destructivo (LFPDPPP)**
- **Problema:** DELETE/UPDATE de tablas con PII (social_followers, watched_profiles, social_comments) no quedan en audit log. LFPDPPP art. 32 requiere trazabilidad.
- **Solución mínima:** tabla `audit_log` (action, model, record_id, user_id, timestamp, payload_json) + middleware FastAPI que registra ops DELETE/UPDATE en endpoints sensibles.
- **No incluye:** GUI para ver el log (sprint UI futuro). Solo persistencia + endpoint admin para query.
- **Criterio aceptación:** `DELETE /watched-profiles/{id}` deja 1 fila en `audit_log` con user_id correcto.
- **Estimado:** 2-3h.

### Tanda 3 · UX sistémica (~4-6h, medio riesgo)

#### **S1 · Unificación KPI cards (F-MED-02, Gemini A3.1)**
- **Problema:** 4 implementaciones de tarjetas de métricas con espaciados/sombras/tipografías distintos (dashboard overview, dirigente page, aceptación detalle, fantasmas).
- **Solución mínima:** componente único `<MetricCard variant="kpi" | "delta" | "audience" />` que englobe los casos. Replace en cada llamada existente.
- **Riesgo:** visual regression. Tomar screenshots antes/después de las 4 vistas.
- **Criterio aceptación:** misma data, mismo look, código DRY.
- **Estimado:** 3-4h.

---

## Sprints DIFERIDOS explícitamente

| Sprint | Razón |
|---|---|
| **S3 · Mobile audit completo** (6-8h) | Requiere validación visual extensiva + decisión Sheet→BottomSheet sistémica. Sprint dedicado en sesión propia con CEO. |
| **S4 · Score IPD competidores** (8-12h) | Requiere expandir scraper + presupuesto Apify ($0.43 disponible insuficiente). Bloqueado por B-APIFY-CREDIT. |
| **S6 · Onboarding UI admin competidores** (4h) | Alcance UI grande, no urgente. Admin puede agregar via psql por ahora. |

---

## Skills/agents asignados

| Sprint | Agent | Modo |
|---|---|---|
| S2 | `root-cause-analyst` (diagnóstico) + `python-expert` (fix) | implementación |
| S5, S7, S10 | `python-expert` + `quality-engineer` (tests) | implementación |
| S8 | `security-engineer` (LFPDPPP) + `backend-architect` | implementación |
| S9 | `python-expert` (script management) | implementación |
| S1 | `frontend-architect` + `ui-visual-validator` (screenshot diff) | implementación |
| Cross-audit | `/gemini review` del propio plan | read-only |

---

## Plan secuenciado · Tandas

### Orden de ejecución (post-Gemini cross-audit 2026-05-15)

Gemini ajustó el orden por dependencias ocultas (S7 antes que S2 porque S2 puede iterar `social_accounts` y S7 evita enmascarar perf), y movió S8 antes que S5/S10 para que cualquier op destructiva subsecuente quede registrada en audit_log.

1. **S7 · N+1 fix** — beneficio sistémico inmediato, menor riesgo. Cambia eager loading de `social_accounts`.
2. **S2 · Engagement 0** — bug visible CEO. Después de S7 para no enmascarar perf si la fórmula itera accounts.
3. **S8 · Audit log (Fase A solamente)** — modelo + SQLAlchemy Event Listeners (NO middleware FastAPI según Gemini, porque middleware no captura cascade deletes ni `Model.query.update()` en tasks de fondo). Fase B (admin UI) DIFERIDA.
4. **S9 · IPD stale detector** — riesgo nulo, CLI puro.
5. **S5 · Celery beat** — task aislada. Timeout Celery > tiempo máximo Apify run (Gemini gotcha).
6. **S10 · Back-off scrapers** — al final. CAMBIO: usar `asyncio.sleep` (no `time.sleep`), retries=2 (no 3 para no bloquear workers), y solo para 5xx + timeout. Si 429 es persistente, log + abort sin reintentar — escalable a sprint proxies futuro.
7. **S1 · Unificación KPI cards** — UI sistémica al final. Estimado revisado: 5-6h (Gemini).

### Ajustes de estimación (Gemini)

| Sprint | Estimado original | Estimado ajustado |
|---|---|---|
| S8 | 2-3h | 4-6h (Event Listeners + serialización + masking PII) |
| S1 | 3-4h | 5-6h (edge cases CSS/responsive de 4 vistas) |
| S10 | 1.5h | 1.5h (asíncrono + solo transitorios, scope reducido) |

### Riesgos nuevos identificados (Gemini)

- **S8**: middleware FastAPI no captura cascade deletes ni updates background → usar Event Listeners SQLAlchemy.
- **S10**: si IG/X dan 429 persistente, decorador `with_backoff` no es suficiente — requeriría proxy rotation. Documentar en plan futuro si lo vemos.
- **S5**: Celery default task timeout puede ser menor que el run Apify → setear `time_limit=600` en la task.

### Verificación por sprint (loop interno)
Cada sprint cierra con:
- ✅ TypeCheck si toca frontend
- ✅ `pytest` específico de los tests nuevos (no suite completa)
- ✅ Smoke contra prod si toca endpoint
- ✅ Commit chico con D-* en mensaje
- ✅ Push (sin abrir PR — branch ya activa)

---

## Criterios de cierre del /sprint-review

- ✅ 7 sprints (S2, S5, S7, S8, S9, S10, S1) ejecutados o reportados con razón si quedan a medias.
- ✅ Diferidos S3, S4, S6 documentados en STATUS.md con razón.
- ✅ Cross-audit Gemini ejecutado sobre este plan.
- ✅ STATUS.md y DECISIONS.md actualizados.
- ✅ Reporte final al CEO con desvíos y próximos pasos.

---

## Garantías de no-alteración

- Branch `feat/phase-b-pesos-editables` — commits chicos, push tras cada uno.
- NO tocar `competitor_metrics_monthly`, `social_followers`, `social_comments` data existente.
- NO ejecutar destructivos en BD sin confirmación textual del CEO en sesión.
- S5 Celery beat se agrega como **disabled by default** (CEO activa cuando quiera).
- S8 audit_log se aplica a nuevos eventos, no backfill histórico (riesgo de PII en logs).
- Vercel deploy SOLO al final de la tanda 1 (no deploy parcial mid-sprint).

---

## Out of scope explícito

- Refactor masivo (no es alcance).
- Touch a Ollama (decisión CEO).
- Touch a planes_ia generator (CRIT-PLAN-IA pendiente).
- Cambio de modelo IA (Claude/Gemini ya estables).
- Tests E2E nuevos completos (solo tests específicos para los fixes).
- Documentación nueva (solo update STATUS/DECISIONS).
