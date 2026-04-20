# SPRINT-CURRENT — Sprint S3 Diferenciadores Tier 2 (Killer Features)

**Sprint actual:** S3 · **Status:** 🟢 EN EJECUCIÓN · autorizado CEO 2026-04-19 post-merge PR #26
**Sprint previo cerrado:** S2 · 2026-04-19 · archivo `.context/archive/sprint-s2-2026-04-19.md` · reporte `backend/research/2026-04-19/SPRINT-S2-REPORTE-EJECUTIVO.md`
**Decisiones vinculantes:** D-19 (matriz 5×5 · modificador temporal) · D-22 (competidores client-owned · proxies S2 reciclables) · D-23 (confirmación humana obligatoria) · revisión §9.8 S2 (aprobada con 2 observaciones menores post-merge)

---

## Objetivo

Implementar los **8 bloques Tier 2 Diferenciadores Defensibles** del diagnóstico. Son las killer features que separan CRECE v2 de Brandwatch/Meltwater/Sprout Social. Cada bloque = backend service + endpoint REST + frontend card + test E2E.

**Criterio acceptance:** los 8 bloques Tier 2 operativos con muestra de casos reales del piloto · Filtro de Realidad (B13) cambia IPD visible (demo del valor) · dashboard `/dashboard/diagnostico-tier2/[id]` navegable.

---

## Observaciones CEO §9.8 integradas como requisitos S3

### Observación 1 — Contexto explicativo del B01 ER (UI)

El headline B01 de Piña (1.2% vs piso 4.6% Nano X) es consistente con D-19 pero puede leerse como fracaso propio del cliente cuando es realidad estructural del dominio político. **Requisito S3:** la card B01 debe mostrar contexto explicativo dual:
- "Tu ER está por debajo del benchmark mexicano empírico (v1 preliminar 4.6% Nano X, n=316)"
- "El benchmark histórico de la industria comercial (Gemini DR · IM commercial) sobre-estimaba este rango ~100× — ver D-19"
- Tooltip o link "¿por qué mi benchmark es más bajo que los rangos de Sprout Social?"

Este ajuste se aplica como part of Sprint S3 frontend pass (no re-abre Sprint S2).

### Observación 2 — Drill-down B10 Humanización

El B10 score 15.14 "Institucional" requiere drill-down habilitado ANTES del Sprint S4 Plan IA:
- Endpoint `GET /api/v1/diagnostico/{dirigente_id}/humanizacion/examples` que devuelve `{top_5_institucional, top_5_humanizante, keywords_analizadas}`
- Frontend: la card B10 incluye botón "Ver ejemplos" que abre drawer con los 10 posts (5+5)
- Sin este drill-down el Plan IA S4 no podrá traducir el score en recomendaciones específicas

Aplicado como S3 T0.5 (pre-arranque bloques Tier 2).

---

## T0 · Memory limit Docker (elevado por CEO de DIFERIDO-05)

**Rationale:** en Sprint S2 Postgres entró en WAL recovery 3× durante batch Plutchik (sin pérdida de datos). Sprint S3 procesa 8 clasificadores NLP adicionales (mayor presión memoria). WAL recovery puede escalar y convertirse en pérdida de datos. **Debe resolverse ANTES de arrancar los 8 bloques Tier 2.**

- [ ] **T0.1** Subir `memory_limit` en `docker-compose.yml` para `crece-db` (recomendación: 4GB) y `crece-backend` (recomendación: 2GB)
- [ ] **T0.2** Reducir `pool_size` del backend async session factory si el container tiene <2GB disponibles
- [ ] **T0.3** Smoke test: correr `run_plutchik_batch.py --limit 100` después del cambio y verificar que Postgres NO entra en recovery mode (tail de logs `docker logs crece-db`)
- [ ] **T0.4** Documentar cambios en `backend/README.md` sección "Recursos Docker recomendados dev/prod"

**Criterio acceptance T0:** batch NLP de 100+ posts completa sin WAL recovery event.

## T0.5 · Drill-down B10 Humanización (observación CEO §9.8)

- [ ] Extender `backend/app/services/diagnostico/humanizacion_service.py` con método `get_examples(dirigente_id, org_id) -> {top_5_institucional, top_5_humanizante}`
- [ ] Endpoint `GET /api/v1/diagnostico/{dirigente_id}/humanizacion/examples`
- [ ] Frontend: botón "Ver ejemplos" en card B10 (extends `cards.tsx`) que abre Drawer/Dialog con los 10 posts + keywords resaltadas
- [ ] E2E test: click en "Ver ejemplos" → 10 posts visibles

## T0.6 · Contexto explicativo B01 ER (observación CEO §9.8)

- [ ] Frontend: extender card B01 en `cards.tsx` con tooltip/link explicativo sobre el benchmark empírico D-19 vs la tabla comercial IM descartada
- [ ] Texto base: "Tu ER {er_actual}% · Benchmark empírico MX {piso}% · El benchmark comercial histórico (Sprout/Rival IQ) sobre-estimaba este rango hasta 100× — ver D-19"
- [ ] Link al `methodology.md` del bundle Zenodo v1 (Track A Apache 2.0 público)

---

## 8 bloques Tier 2 (MASTER §3.2)

| # | Bloque | Pregunta | Input crítico | Fuente |
|---|---|---|---|---|
| B11 | Cross-Partisan Validation Score | ¿Mi mensaje cruza líneas partidistas? | authors comments + afiliación inferida | §3.2 #11 |
| B12 | CIB Detector multinivel | ¿Hay comportamiento coordinado inauténtico? | TF-IDF + clustering + account age + framework ITESO | §3.2 #12 |
| B13 | Filtro de Realidad | ¿Cuál es mi ER orgánico sin CIB? | toggle UI que recalcula métricas excluyendo CIB | §3.2 #13 |
| B14 | Topic Drift Detector | ¿Mi caption habla de lo que los comments discuten? | TF-IDF caption vs comments | §3.2 #14 |
| B15 | Rage Click Flag | ¿Mi engagement es indignación o conversión? | sentiment × velocity heurística | §3.2 #15 |
| B16 | Rastreador Promesas de Campaña | ¿Cumplí lo que prometí? | tabla `promesas_dirigente` + NLP co-ocurrencia | §3.2 #16 |
| B17 | Veda INE Compliance | ¿Puedo publicar esto en ventana veda? | filtro heurístico sobre queue publicación | §3.2 #17 |
| B18 | Escaneo Violencia Política | ¿Hay amenazas o violencia política de género? | diccionarios hate speech MX + detector | §3.2 #18 |

---

## Tareas (estructura)

### T1 — Backend services (8 services Python)
- [ ] `backend/app/services/diagnostico_tier2/` con 8 archivos: `cross_partisan_service.py`, `cib_detector_service.py`, `filtro_realidad_service.py`, `topic_drift_service.py`, `rage_click_service.py`, `promesas_service.py`, `veda_compliance_service.py`, `violencia_politica_service.py`
- [ ] Cada service con método async `compute(dirigente_id, org_id) -> dict`
- [ ] Tests unitarios por service en `backend/tests/diagnostico_tier2/`

### T2 — Endpoints REST
- [ ] `backend/app/api/v1/endpoints/diagnostico_tier2.py` con 8 endpoints individuales + 1 agregado
- [ ] Filtro de Realidad (B13) necesita query parameter `?filtro_cib=true` que recompute los bloques Tier 1 excluyendo cuentas CIB detectadas en B12
- [ ] Auth JWT + org_id scoping

### T3 — NLP clasificadores adicionales
- [ ] Clasificador de afiliación partidista (B11) — diccionarios MC/MORENA/PAN/PRI + heurística sobre content
- [ ] Clasificador hate speech MX (B18) — diccionario seed + extensibilidad a Perspective API si el presupuesto lo permite
- [ ] Detector de sarcasmo/outrage (B15) — heurística sentiment spike + keywords negativos + velocity

### T4 — Frontend 8 cards Tier 2 + drill-downs
- [ ] `frontend/src/app/dashboard/diagnostico-tier2/[dirigenteId]/page.tsx`
- [ ] 8 cards con visualizaciones específicas (red graph CIB, heatmap topic drift, timeline veda, etc.)
- [ ] Toggle "Filtro de Realidad" en el header global del dashboard que replica hacia Tier 1 (demo del valor)

### T5 — Integración + E2E
- [ ] 8 tests E2E Playwright (1 por bloque)
- [ ] Toggle Filtro Realidad cambia IPD visible y números Tier 1 (demostración del valor)

---

## Gaps pendientes de S2 (requisitos de reactivación documentados)

Per observación CEO §9.8, los dos bloques insufficient_data del Sprint S2 quedan con criterio explícito de reactivación (no son pendientes fantasma):

- **B07 Growth Attribution Time-Decay** — retomar cuando `scrape-all-profiles-daily` haya acumulado **≥14 días de snapshots de followers**. Hasta entonces la card muestra `insufficient_data` con contador "faltan X días". Verificar cada día con `SELECT count(DISTINCT date(created_at)) FROM social_profile_snapshots;`
- **B08 Share of Voice** — retomar cuando `run_topic_extraction.py` haya procesado **≥500 posts con `topics_extracted` poblado**. Hasta entonces la card muestra `insufficient_data` con contador "faltan X posts por clasificar". Verificar con `SELECT count(*) FROM social_posts WHERE topics_extracted IS NOT NULL;`

Estos criterios NO son tareas de S3 — son watchers. El servicio detecta automáticamente cuando el umbral se cumple y pasa de `insufficient_data` a `ok` sin código nuevo. Solo se monitorean.

---

## Paralelización operativa sugerida

- **Bloque A (compute + NLP):** B11 + B12 + B14 + B15 (NLP-heavy)
- **Bloque B (meta):** B13 Filtro Realidad + B17 Veda Compliance (transversales sobre Tier 1)
- **Bloque C (registro + texto):** B16 Promesas + B18 Violencia Política
- **Bloque D (frontend + drill-down B10/B01):** T4 + T0.5 + T0.6

Clock estimado: **6-10h con 4-5 agents concurrentes** post-T0 cierre.

---

## Criterio acceptance del Sprint S3

Sprint S3 se declara completo cuando:

1. **T0** memory_limit Docker aplicado + smoke test NLP sin WAL recovery
2. **T0.5** drill-down B10 operativo con endpoint + UI drawer
3. **T0.6** contexto explicativo B01 agregado en UI
4. 8 services Tier 2 + 8 endpoints con tests unitarios pasando
5. 8 cards frontend renderizando con datos reales
6. Toggle Filtro Realidad (B13) demuestra cambio visible en IPD
7. 8 tests E2E Playwright verdes

Con 6/7 dura + demo Filtro Realidad funcional → arranque Sprint S4 autorizado.

---

## Protocolo actualización

Al cierre de cada T: `- [x]` + link output. Al cerrar sprint: archivar a `.context/archive/sprint-s3-YYYY-MM-DD.md` + reset para Sprint S4.
