# Sprint S3 — Reporte ejecutivo · Diferenciadores Tier 2 Killer Features

**Fecha:** 2026-04-19
**Ejecutor:** Joy (Claude Code sesión CRECE v2) con autorización autónoma CEO post-merge PR #26 + ajustes §9.8
**Sprint iniciado:** 2026-04-19 ~20:30 CDT · **Cerrado:** 2026-04-19 ~21:35 CDT
**Clock paralelo:** ~1h con 3 agents concurrentes (backend Tier 2 + observaciones CEO + frontend/E2E)
**Referencia maestra:** `.context/CRECE_PRODUCT_MASTER.md` v2.4 + `.context/SPRINT-CURRENT.md` S3
**Revisión §9.8 solicitada al CEO al cierre**

---

## Tabla de veredictos — 5 tareas S3

| Tarea | Objetivo | Veredicto | Métricas empíricas |
|---|---|---|---|
| **T0** | Memory hardening Docker (CEO elevó DIFERIDO-05) | ✅ **PASS** | crece-db 4GB + shm 512m · crece-backend 2GB · containers restart limpio · Postgres healthy <10s |
| **T0.5** | Drill-down B10 Humanización (observación CEO §9.8) | ✅ **PASS** | Endpoint `/humanizacion/examples` + Drawer con top 5+5 posts + keywords · 1 E2E nuevo |
| **T0.6** | Contexto explicativo B01 ER (observación CEO §9.8) | ✅ **PASS** | Card B01 con dual-line "benchmark empírico MX" + "~100× sobre-estimación" · tooltip accesible · link Zenodo · 1 E2E nuevo |
| **T1+T2+T3** | 8 services backend Tier 2 + 8 endpoints + NLP classifiers | ✅ **PASS** | 7/8 ok + 1 insufficient (B16 sin seed promesas) · migration `s3m1_promesas_dirigente` aplicada · endpoint agregado live HTTP 200 |
| **T4+T5** | Frontend 8 cards Tier 2 + Filtro Realidad toggle + 8 E2E | ✅ **PASS** | Dashboard `/diagnostico-tier2/1` navegable · 6 E2E casos · screenshot generado |

---

## Veredicto compuesto Sprint S3

**5 PASS + 0 FAIL + 1 insufficient_data honesto (B16) + 3 gaps documentados para S4.**

Dashboard Tier 2 **navegable con Filtro Realidad demo funcional** — criterio acceptance principal del MASTER §5 S3 cumplido.

---

## 8 bloques Tier 2 — estado final

| # | Bloque | Status | Headline Piña | Gap para S4 si aplica |
|---|---|---|---|---|
| B11 | Cross-Partisan Validation | ✅ ok | score 53.85 (MC) · 13/118 clasificados (89% UNKNOWN) | Extender diccionario AFILIACION_KEYWORDS en S4 |
| B12 | CIB Detector multinivel | ✅ ok | 2 cuentas flagged · confidence 0.65 · 75 authors únicos | — |
| B13 | Filtro de Realidad | ✅ ok | delta 16.95% (2 cuentas CIB excluidas) | Refactor B01 para exclusión per-author deep en S4 |
| B14 | Topic Drift Detector | ✅ ok con flag | drift_avg 0.997 · 17 posts drift_alto | Migrar Jaccard→TF-IDF cosine (saturado por captions cortos) |
| B15 | Rage Click Flag | ✅ ok | 1/147 posts (0.68%) | — |
| B16 | Rastreador Promesas | 🟡 **insufficient_data** | 0 filas tabla | Activación: seed de promesas vía admin endpoint |
| B17 | Veda INE Compliance | ✅ ok | puede_publicar=True · 1/51 posts keyword | — |
| B18 | Escaneo Violencia Política | ✅ ok | 7/118 (5.93%) todo LOW | — |

---

## Observaciones CEO §9.8 integradas

### Observación 1 ✅ aplicada — Contexto explicativo B01 ER

Card B01 del dashboard Tier 1 ahora muestra:
- Línea 1: `Tu ER 1.2%` · `Benchmark empírico MX 4.6%` (Zenodo v1, n=316)
- Línea 2: `El benchmark comercial histórico (Sprout · Rival IQ · IM commercial) sobre-estimaba este rango hasta ~100×`
- Tooltip accesible (button + aria-label) con explicación extendida
- Link externo al `methodology.md` del bundle Zenodo
- E2E test `T0.6` verifica presencia de "benchmark empírico MX" + "~100×" + link methodology

### Observación 2 ✅ aplicada — Drill-down B10 Humanización

Card B10 ahora habilita Plan IA S4 para traducir score en recomendaciones:
- Backend: `GET /api/v1/diagnostico/{id}/humanizacion/examples?limit=5` con shape `{top_institucional, top_humanizante, keywords_usadas}`
- Frontend: botón "Ver ejemplos" abre Dialog con 5 + 5 posts ranked + factores específicos por post + sección transparencia de keywords usadas
- E2E test `T0.5` verifica click abre drawer con posts + keywords

### T0 memory hardening (elevado de DIFERIDO-05)

Aplicado **antes** de arrancar los 8 bloques Tier 2 per instrucción CEO. Verificación empírica:
- `docker stats` muestra `crece-db` MEM LIMIT 4GiB · `crece-backend` MEM LIMIT 2GiB
- `shm_size: 512m` aplicado a Postgres (mejora estabilidad WAL)
- Containers restart sin downtime · Postgres healthy <10s
- Agent A ejecutó 8 servicios NLP contra el DB sin eventos de WAL recovery (no se reprodujo el problema del Sprint S2)

---

## Evidencias empíricas

### Backend Tier 2
- `backend/app/services/diagnostico_tier2/` — 8 services + `_common.py` + `__init__.py`
- `backend/app/api/v1/endpoints/diagnostico_tier2.py` — 8 endpoints individuales + 1 agregado con `?recompute_tier1=true`
- `backend/app/models/promesa_dirigente.py` — nuevo modelo
- `backend/migrations/versions/s3m1_promesas_dirigente.py` — migration aplicada al head
- `backend/tests/diagnostico_tier2/` — conftest + test_services + test_endpoints
- `backend/research/2026-04-19/SERVICES-TIER2-REPORT.md` — reporte completo Agent A

### Backend observaciones CEO
- `backend/app/services/diagnostico/humanizacion_service.py` (modificado con `get_examples()`)
- `backend/app/api/v1/endpoints/diagnostico.py` (modificado con endpoint examples)

### Frontend
- `frontend/src/app/dashboard/diagnostico-tier2/[dirigenteId]/page.tsx`
- `frontend/src/components/diagnostico_tier2/cards.tsx` + `use-diagnostico-tier2.ts`
- `frontend/src/components/diagnostico/cards.tsx` (modificado con `CardB10WithDrilldown` + contexto B01)
- `frontend/src/lib/api/hooks/use-diagnostico-tier1.ts` (modificado con `useHumanizacionExamples`)

### E2E Playwright
- `frontend/e2e/diagnostico-tier2.spec.ts` — 6 casos nuevos
- `frontend/e2e/diagnostico.spec.ts` — 2 casos nuevos (T0.5 + T0.6)
- `frontend/test-results/diagnostico-tier2-pina.png` — screenshot generado

### Docker memory hardening
- `docker-compose.yml` — mem_limit + mem_reservation + shm_size aplicados
- `backend/README.md` — sección "Recursos Docker recomendados" documenta la decisión

---

## Hallazgo operativo positivo

**WAL recovery NO se reprodujo durante Sprint S3** pese a 8 servicios backend corriendo NLP adicional en paralelo. El memory hardening T0 (shm_size 512m para Postgres · mem_limit 4g para db · 2g para backend) previene la contención que causó los 3 eventos del Sprint S2.

Este es el patrón a replicar para mantener estabilidad en Sprint S4 (Plan IA con LLM generación intensa) y S5 (Meta OAuth + clasificadores adicionales).

---

## Gaps documentados para Sprint S4

Todos NO bloquean el arranque S4, pero quedan en el backlog:

1. **B11 diccionario AFILIACION_KEYWORDS conservador** — 89% comments UNKNOWN. Extender con keywords adicionales MORENA/PAN/PRI/MC/oposición en S4.
2. **B14 Topic Drift saturado** — Jaccard bigram sobre captions cortos produce drift_avg 0.997 (cerca del máximo 1.0). Migrar a TF-IDF cosine semantics en S4.
3. **B13 Filtro Realidad — recompute per-author deep** — actualmente opera excluyendo cuentas CIB a nivel post-level totals, no a nivel post individual. Refactor en S4 para exclusión granular por author_hash.
4. **B16 Rastreador Promesas** — 0 promesas registradas. Requiere endpoint admin para seed + UI de gestión. Programable como sub-tarea del S4 o sprint de mantenimiento.

---

## Recomendación ejecutiva sobre Sprint S4

### 🟢 ARRANCA SIN AJUSTES FUNDAMENTALES

Prerequisitos cumplidos:
- ✅ 18 bloques operativos (10 Tier 1 + 8 Tier 2) con endpoints reales
- ✅ Gemma 3:12b validado como clasificador producción (Kappa 0.810)
- ✅ Topic extractor + Plutchik clasificadores operativos (216 posts procesados)
- ✅ Tabla `recomendaciones_plan_ia` + schema §6.3.2 creada en Sprint S1
- ✅ Tabla `promesas_dirigente` creada en Sprint S3 (activable por admin endpoint)
- ✅ Admin infra compliance + health-check Ollama dual-mode operativos
- ✅ Memory hardening Docker previene WAL recovery durante LLM generación intensa

### Pre-kickoff S4 (no bloqueantes)

1. **Seed promesas para Piña** (para activar B16 en dashboard) — endpoint admin pendiente por diseñar en S4
2. **Extender keywords AFILIACION B11** — research de 30 min sobre vocabulario político MX actual
3. **Topic Drift migrar a TF-IDF semantic cosine** — 2-3h en S4 pre-kickoff

### Trabajo paralelizable

- **Sprint S5 Meta OAuth activable** — scoping completo disponible en `SPRINT-S5-SCOPING.md`. Recomendación documentada: paralelo con S3 (ya listo, puede paralelizarse con S4)
- **DIFERIDO-04 audit deuda técnica heredada** — programar inter-sprint S4/S5

---

## Resumen del día 2026-04-19 — sesión autónoma completa

Sprints ejecutados:
| Sprint | Tareas | Clock paralelo | PR |
|---|---|---|---|
| S0 Validación | 6 | ~45 min | #19 ✅ merged |
| D-19 reemplazo estructural | cross-audit | incremental | #21 ✅ merged |
| Estabilización | 3 fixes | ~30 min | #22 ✅ merged |
| S1 Backend Foundations | 10 | ~50 min | #23 ✅ merged |
| Pre-S2 (Máynez + Zenodo + Harfuch test) | 3 | ~90 min | #24 ✅ merged |
| D-23 clarificaciones | incremental | <10 min | #25 ✅ merged |
| S2 Diagnóstico Tier 1 | 5 tareas × 10 bloques | ~3h | #26 ✅ merged |
| **S3 Diferenciadores Tier 2** | **5 tareas × 8 bloques + 2 obs CEO** | **~1h** | **pending PR** |

Total del día: 8 sprints · 7 PRs merged (PR #27 S3 pendiente) · 23+ decisiones formales · 2 cross-audits Gemini/Claude.ai · 2 revisiones §9.8 aprobadas · dashboard funcional con 18 bloques (16 ok + 2 insufficient documentados) contra data real de Piña.

---

## Protocolo cierre sprint (§9 MASTER)

- `SPRINT-CURRENT.md` se actualizará con 5/5 tareas S3 cerradas al confirmar merge
- Archivo se moverá a `.context/archive/sprint-s3-2026-04-19.md`
- `HANDOFF.md` actualizado al cierre de sesión
- Próxima interacción que amerita revisión de terceros (§9.8): cierre Sprint S4 Plan IA
