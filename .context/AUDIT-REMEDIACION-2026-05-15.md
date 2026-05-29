# AUDIT-REMEDIACION · 2026-05-15

Branch: `feat/phase-b-pesos-editables` (deployado prod Vercel)
Sesión audit: 6 horas (PLAN + 3 fases + triage + Sprint Q parcial + cross-audits)

## Resumen ejecutivo

| Métrica | Valor |
|---|---|
| Findings totales | 19 (3 fases) + 2 bugs CEO |
| **CERRADOS en prod** | **9** (6 RBAC CRÍTICOS + 2 ALTOS Sec + 2 bugs CEO + 1 leak listing eventos) |
| Pendientes decisión CEO | 2 (A5 data_source, A8 Taboada dup + scrape) |
| Diferidos a sprint | 9 |
| Producción status | **APTA PARA PILOTO** |

---

## Cerrados en esta sesión (deployados Vercel prod)

### Hotfix `0f232ea` — Multi-tenant + SQLi + JWT

| ID | Finding | Validación |
|---|---|---|
| F-CRIT-01 | `/dirigentes/{id}/diagnostico` | curl 403 ✓ |
| F-CRIT-02 | `/dirigentes/{id}/social-summary` | curl 403 ✓ |
| F-CRIT-03 | `/bot-detection/analyze/{id}` | curl 403 ✓ |
| F-CRIT-04 | `/eventos/by-dirigente/{id}` | curl 403 ✓ |
| F-CRIT-05 | `/eventos/?dirigente_id=N` (listing) | scope by user.org_id ✓ |
| F-CRIT-07 | `/social/sentiment-timeline?dirigente_id=N` | curl 403 ✓ |
| F-CRIT-08 | `/social/sentiment-coverage?dirigente_id=N` | curl 403 ✓ |
| F-ALTO-01 | SQLi latente divergencia_encuestas | bindparam aplicado ✓ |
| F-ALTO-02 | JWT default | staging+production guard ✓ |

**Validación E2E Vercel prod:** 18/18 curl OK (6 cross→403, 6 admin→200, 6 propio→200).

### Encuestas `15b4e39` — Bugs reportados por CEO

| ID | Finding | Validación |
|---|---|---|
| A1 CEO | Encuestas: municipios no visibles en alcaldes | Playwright Vercel: "Acapulco de Juárez, Guerrero" visible ✓ |
| A2 CEO | Encuestas: comparativa 877 series amontonadas | Chip-toggle default 65 series (Federal+Gob), opt-in +alcaldes/Todos ✓ |

---

## Pendientes decisión CEO

### A5 · data_source NULL 306 rows (~14%)

**Lo que requiere:** UPDATE bulk + Alembic migration NOT NULL.

**Plan propuesto:**
```sql
UPDATE social_comments
SET data_source = 'legacy-pre-2026-04-13'
WHERE data_source IS NULL;
```
+ migration ALTER COLUMN data_source SET NOT NULL.

**Riesgo:** modifica metadata (no contenido analítico) en 306 filas. Es irreversible una vez aplicado. NO altera resultados de análisis IA/sentiment — los comments siguen siendo los mismos.

**Decisión requerida:** ¿proceder o diferir? Recomendación: **proceder** — etiqueta honesta legacy es mejor que NULL, y constraint NOT NULL previene reincidencia.

### A8 · Competitor sin métricas + Taboada duplicado

**Subitem 1: DELETE Taboada dup**
- `competitor_profiles` tiene 2 rows con `display_name='Santiago Taboada Cortina'` (ids 4 y 5).
- id=4 es TWITTER. id=5 es INSTAGRAM. Tal vez intencional (mismo dirigente, plataformas distintas). Verificar antes de DELETE.

**Subitem 2: Scrape Ballesteros (6 competitors sin métricas)**
- 5 TWITTER + 1 INSTAGRAM. Requiere actores Apify distintos:
  - TW: ~$0.10/perfil × 5 = $0.50
  - IG: ~$0.05/perfil × 1 = $0.05
  - Total estimado: $0.55. **Saldo Apify INICIAL: $0.43 hasta 2026-05-23 → insuficiente.**
- Alternativa: usar scrapers nativos `twscrape` y `instaloader` que están en `backend/app/scrapers/`. Requiere `TWITTER_AUTH_TOKEN` configurado en container (A10 ENV).

**Recomendación:** diferir hasta resolver A10 (APIFY_TOKEN no inyectado) y/o renovar saldo Apify mes siguiente.

---

## Diferidos a sprints siguientes

### Sprint S · Compliance & RBAC (siguiente sesión, ~2-3h)

| ID | Finding | Plan |
|---|---|---|
| F-ALTO-03 | DELETE watched/competitors sin audit log | Crear tabla `audit_log` + uso en endpoints destructivos |
| F-MED-01 | `/social/posts` `/social/comments` override silencioso vs 403 | Cambiar a 403 explícito + actualizar frontend |
| F-MED-02 | CORS_ORIGINS default localhost en prod | Guard en `_guard_production_secrets` |

### Sprint D · Decisión producto CRIT-PLAN-IA

| ID | Finding | Decisión requerida |
|---|---|---|
| CRIT-PLAN-IA | `plan_generator` no implementa cascada Claude→Gemini→Ollama documentada | (a) implementar real (2-3h), (b) actualizar docs a single-provider, (c) gap conocido en backlog |

### Sprint P · Performance & DB (no urgente, ~4h)

| ID | Finding | Plan |
|---|---|---|
| F-PERF-01 | N+1 list_dirigentes (cold 9.4s) | Refactor batch SQL para platform_count + materializar IPD |
| F-PERF-02 | N+1 _gather_context plan_generator | Acoplado con CRIT-PLAN-IA |
| F-PERF-03 | `/aceptacion/overview` 4 LEFT JOINs encadenados | Materialized view + Celery beat refresh |
| F-PERF-04 | recharts + maplibre eager-loaded | `next/dynamic` + suspense en 3 pages + 9 componentes |
| F-PERF-08 | Falta index `ix_social_posts(profile_id, published_at DESC)` | Alembic migration |
| F-PERF-06 | `pool_recycle` ausente | Setear 1800s en `core/database.py` |

### Sprint I · Info quality (siguiente sesión, ~1.5h)

| ID | Finding | Plan |
|---|---|---|
| A3 | Sentiment mismatch overview vs ia-summary | Mapear UI dónde se renderiza cada uno; añadir campo `total_comments_analyzed` (con HAVING) y `total_comments` (sin filtro) explícitos |
| A4 | IPD stale 30d + escala mezclada engagement_rate | Celery beat recalc diario + normalizar engagement_rate a [0,1] |
| A11 | Solo `twitter.py` tiene back-off | Aplicar patrón a FB/YT/Threads/Telegram/Bluesky |

### Sprint UX (small, ~30 min)

| ID | Finding | Plan |
|---|---|---|
| F-PERF-05 | `/dirigentes/{id}/ia-summary` 404 mounting irregular | Revisar `api/v1/__init__.py` prefix |

---

## Out of scope (backlog)

| ID | Finding | Razón |
|---|---|---|
| F-BAJO-01 | Política CI "cero `text(f`" | Infra change, sprint dedicado |
| A10/ENV | APIFY_TOKEN no inyectado al container | Mac local config, no afecta prod Mac |
| Refactor calculate_ipd | (de F-PERF-01) | Riesgo de romper IPD scoring |

---

## Recomendación CEO

**Estado prod:** APTO PARA PILOTO. Leaks críticos cerrados, bugs UI reportados arreglados.

**Próximas decisiones inmediatas:**
1. **A5** (data_source NULL): aprobar UPDATE legacy (15 min).
2. **A8 Taboada dup**: verificar si dup intencional (5 min check); decidir DELETE o keep.
3. **CRIT-PLAN-IA**: elegir camino (a/b/c) — bloquea Sprint P (perf) ya que F-PERF-02 depende.

**Próximas sesiones (orden sugerido):**
1. Sprint S (compliance audit log + 403 override) — 2-3h
2. Sprint I (sentiment mismatch + IPD recalc) — 1.5h
3. Sprint P (perf wins F-PERF-01 + index + dynamic imports) — 3-4h

**Tiempo total restante para cierre estructural:** ~7-9h en 3-4 sesiones.

---

## Cross-audit Gemini (2026-05-15) · veredicto final

**PROCEDER** con piloto. Auditoría cross-validada.

Hallazgos adicionales que Gemini destacó:
- **Riesgo operativo CRIT-PLAN-IA:** al fallar Claude, BD guarda `"Error generando plan."` literal que el usuario final ve. Mitigación: usuarios beta del piloto deben saberlo, o decidir camino (a/b/c) antes de uso intensivo.
- **A10 APIFY_TOKEN container:** la ingesta puede fallar silenciosamente durante piloto si scrapers nativos también caen. Mitigación: validar `docker exec crece-backend env | grep APIFY_TOKEN` antes de demo.
- **Cold-start F-PERF-01 9.4s:** primera impresión del cliente. Mitigación recomendada por Gemini: script de warm-up antes de demo.

**Blind spot recurrente identificado:** fragilidad en inyección de entorno (defaults hardcoded fallback inseguros + variables `.env` raíz que no cruzan al container). Sprint S debería incluir guard explícito en `_guard_production_secrets` para SALT, APIFY_TOKEN, y validar `APP_ENV` no acepta defaults de prod.

**Recomendación operativa para piloto:**
1. Pre-demo: warm-up `curl /dashboard/dirigentes` 2-3 veces para llenar cache.
2. Pre-demo: validar `docker exec crece-backend env | grep -E "APIFY|TWITTER|JWT"` muestre valores reales.
3. Documentar al usuario beta que `plan_generator` actualmente Claude-only sin cascada documentada.
