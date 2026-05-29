# AUDIT-TRIAGE · 2026-05-15

Branch: `feat/phase-b-pesos-editables` (merged hotfix RBAC)
Insumos: `AUDIT-SECURITY-RBAC`, `AUDIT-INFO-LOGIC`, `AUDIT-PERF` (2026-05-15)

## Estado pre-triage

| Hotfix ya aplicado en prod | Commit |
|---|---|
| 6 CRÍTICOS scope leak | `0f232ea` |
| F-ALTO-01 SQLi divergencia_encuestas | `0f232ea` |
| F-ALTO-02 JWT default staging guard | `0f232ea` |

Validado: smoke Vercel prod 18/18 verde (6 cross→403 + 6 admin→200 + 6 propio→200).

---

## Findings consolidados (15 abiertos)

### P0 · Bloqueador piloto (decidir en esta sesión)

| ID | Origen | Finding | LOC fix | Tiempo | Acción |
|---|---|---|---|---|---|
| **CRIT-PLAN-IA** | F2 | `plan_generator` NO implementa cascada Claude→Gemini→Ollama documentada. Switch binario por `AI_PROVIDER`. En fallo persiste literal `"Error generando plan."` y loguea modelo como Claude. **Docs vs realidad.** | ~80 LOC O cambio docs | 2-3h código / 10 min docs | DECISIÓN CEO: (a) implementar cascada real, (b) actualizar docs a "single-provider con fallback manual", (c) marcar como sprint posterior pero documentar el gap |

### P1 · Alto · debe arreglar antes de demo MC

| ID | Origen | Finding | LOC | Tiempo | Sprint sugerido |
|---|---|---|---|---|---|
| F-ALTO-03 | F1 | DELETE `watched_profiles` + `competitors` sin audit log. Denuncias borradas sin trazabilidad. | ~50 LOC nuevo modelo + uso | 1h | Sprint Compliance |
| **A3 ALTO** | F2 | Sentiment counts mismatch entre `/aceptacion/overview` y `/dirigentes/{id}/ia-summary`. Piña 430 vs 336, Solano 24 vs 15, Saymi 510 vs 402. UI muestra dos verdades. | ~10 LOC (alinear filtros) | 45 min | Quick fix |
| **A5 ALTO** | F2 | 306 rows `social_comments.data_source = NULL` (14% del total) | UPDATE SQL bulk + constraint NOT NULL | 30 min | Quick fix |
| **A8 ALTO** | F2 | 6/8 competitor_profiles sin métricas. Duplicado Taboada ids 4 y 5. | scraper run + DELETE dup | 30 min + scrape window | Quick fix |
| **F-PERF-01 ALTO** | F3 | N+1 en `list_dirigentes`: 2 queries/dirigente, TTFB cold 9.4s. | refactor a 1 query con JOIN | 30 min | Quick fix |
| **A1 CEO** | CEO | Encuestas: nombres municipios/alcaldías no visibles al seleccionar | depende del módulo | 30-60 min | Fix encuestas YA |
| **A2 CEO** | CEO | Encuestas: comparativa "todas" se amontona | layout responsive | 30-60 min | Fix encuestas YA |

### P2 · Medio · siguiente sprint (1-2 semanas)

| ID | Origen | Finding | Notas |
|---|---|---|---|
| F-MED-01 | F1 | `/social/posts` y `/social/comments` 200 OK confuso cuando viewer pide otro dirigente_id (override silencioso) — debería ser 403 | UX/contrato API |
| F-MED-02 | F1 | CORS_ORIGINS default incluye localhost — validar que prod env override correctamente | Compliance |
| A10/ENV | F2 | APIFY_TOKEN definido en `.env` raíz pero no inyectado al container `crece-backend` | Limita fallback scrapers |
| A4 | F2 | IPD stale 30d (último cálculo 2026-04-15). Sin Celery beat task. `engagement_rate` escala mezclada (-0.029 a 35.04) | Recalc diario + normalizar |
| A11 | F2 | Solo `twitter.py` tiene back-off. FB/YT/Threads/Telegram/Bluesky sin retry/circuit breaker | Robustness |
| F-PERF-02 | F3 | N+1 en `plan_generator._gather_context` | Acoplado con CRIT-PLAN-IA |
| F-PERF-03 | F3 | `/aceptacion/overview` 4 LEFT JOINs encadenados, cost 1102. Crece O(posts×comments) | Materialized view + Celery refresh |
| F-PERF-04 | F3 | recharts + maplibre eager-loaded en 3 pages + 9 componentes | `next/dynamic` + suspense |

### P3 · Bajo · backlog

| ID | Origen | Finding |
|---|---|---|
| F-BAJO-01 | F1 | Política CI "cero `text(f`" + grep block. Mejora estructural |
| F-PERF-05 | F3 | `/dirigentes/{id}/ia-summary` 404 — mounting irregular en `__init__.py` |
| F-PERF-06 | F3 | `pool_recycle` ausente en `database.py` (default -1). Recomendar 1800s |
| F-PERF-08 | F3 | Falta `ix_social_posts(profile_id, published_at DESC)` para >30k posts |

---

## Plan de remediación esta sesión

### Sprint Q · Quick wins (90-120 min)

Ordenados por riesgo decreciente:

1. **A1+A2 encuestas** (30-60 min) — bugs ya identificados por CEO, demo blocker visual.
2. **A3 sentiment mismatch** (45 min) — alinear filtros (HAVING ≥5 o quitarlo de ia-summary).
3. **A5 data_source NULL** (30 min) — UPDATE bulk con heurística (default por tabla origen) + constraint.
4. **A8 competitor sin métricas** (30 min) — re-correr `scrape_competitors_light_apify.py` para Ballesteros + DELETE duplicado Taboada (id=5 si 4 es el canónico).
5. **F-PERF-01 N+1 list_dirigentes** (30 min) — refactor a 1 query con JOIN agregado.

Total estimado: ~3 horas.

### Sprint S · Compliance/audit log (siguiente sesión, 2-3h)

- F-ALTO-03: tabla `audit_log` + uso en DELETE destructivos.
- F-MED-01: cambiar override silencioso a 403 en social/posts y social/comments.
- F-MED-02: validar CORS prod env.

### Sprint Decisión CRIT-PLAN-IA (paralelo, decisión CEO requerida)

Sin código hasta decisión CEO:
- (a) implementar cascada real (~2-3h)
- (b) actualizar docs a "single-provider"
- (c) marcar gap conocido

### Sprint Perf (backlog, no urgente)

F-PERF-02..08, A10, A4, A11.

---

## Out of scope esta sesión

- Refactor mayor de `plan_generator` (depende decisión CRIT-PLAN-IA)
- Materialized view de aceptacion (requiere análisis carga real)
- Pull-up cascada de scrapers retry/backoff (>4h)
- Política CI grep block (sprint infra)

---

## Sentencia

Sistema **APTO PARA PILOTO** post-hotfix RBAC + Sprint Q. Las decisiones P0+P1 pendientes son:
1. Confirmar Sprint Q ahora (5 quick wins en 3h).
2. Decidir CRIT-PLAN-IA (b o c — implementación cascada queda para sprint dedicado).
3. Confirmar Sprint S+Perf en sesiones siguientes.

---

## Progreso Sprint Q (en sesión 2026-05-15)

| Finding | Estado | Commit/Notas |
|---|---|---|
| A1 encuestas municipios | ✅ FIXED | Backend retorna `municipio`, frontend renderiza "Municipio, Estado" en alcaldes |
| A2 comparativa amontonada | ✅ FIXED | Chip-toggle Federal+Gob (default ~30 series) / +top10 alcaldes / Todos |
| A3 sentiment mismatch | ⏳ PENDIENTE | Requiere mapeo UI para entender qué número se muestra dónde. Diferir a sprint dedicado. |
| A5 data_source NULL 306 rows | ⏳ DECISIÓN CEO | UPDATE bulk requeriría modificar `social_comments` (resultado en BD). Pregunta: ¿cuenta metadata histórica como "resultado"? Si no → procedo con `UPDATE SET data_source='legacy-pre-2026-04-13'` + migration NOT NULL. |
| A8 Taboada dup + Ballesteros sin métricas | ⏳ MISMO | DELETE FROM competitor_profiles WHERE id=5 + run scrape Ballesteros. ¿OK alterar tabla competitors? |
| F-PERF-01 N+1 list_dirigentes | ⏳ PENDIENTE | Refactor SQL — sin riesgo a datos. Procedo. |
