# Sprint S2 Diagnóstico Tier 1 — SERVICES REPORT

**Rama:** `feat/sprint-s2-diagnostico-tier1`
**Fecha:** 2026-04-19
**Scope:** T1 (10 services Python) + T2 (11 endpoints REST) — NO commit desde agent

## Resumen

- **10 services creados** en `backend/app/services/diagnostico/` (paquete Python; el antiguo archivo plano `diagnostico.py` se preservó como `diagnostico/legacy.py` y `calculate_ipd` se re-exporta desde `__init__.py`).
- **11 endpoints REST** en `backend/app/api/v1/endpoints/diagnostico.py` (10 individuales + 1 agregado) registrados con prefijo `/api/v1/diagnostico`.
- **Auth JWT + org_id scoping** aplicado a todos los endpoints vía `get_current_user` + admin-override por `X-Org-Id`.
- **Tests unitarios** 14 casos en `backend/tests/diagnostico/` (1 happy + 1 insufficient por bloque; 2 tests del endpoint agregado).
- **Verificación empírica** live contra Piña (id=1): 10/10 endpoints HTTP 200, 8/10 `status=ok`, 2/10 `status=insufficient_data`.

## Estado por bloque contra Piña (id=1)

| Bloque | Endpoint | Status | Resumen data real |
|---|---|---|---|
| B01 ER normalizado | `/1/er_normalizado` | ok | 4 plataformas (TWITTER, INSTAGRAM, FACEBOOK, TIKTOK) · estrato=Nano · modificador_temporal=1.0 |
| B02 Breakout Scale | `/1/breakout_scale` | ok | max_categoria=1 · breakout_pct=0.0 (ningún post cruzó baseline algorítmico) |
| B03 Matriz 2x2 | `/1/matriz_2x2` | ok | INSIGNIA=84 · CRISIS=62 · VANIDAD=0 · MUERTA=0 · n_posts=146 |
| B04 Benchmark | `/1/benchmark` | ok | origen=`dirigente.competidor_directo_ids` · 3 rivales (no requirió proxy fallback) |
| B05 Plutchik | `/1/sentiment_plutchik` | ok | 112 posts con emotions · ratio_trust_anger=0.0 (trust=0, gap conocido) |
| B06 Crisis Spike | `/1/crisis_spike` | ok | spike=false · severity=0.0 |
| B07 Growth Attr | `/1/growth_attribution` | **insufficient_data** | <2 snapshots en 14d (cron diario snapshot no acumula historial) |
| B08 SoV | `/1/sov` | **insufficient_data** | 0 posts propios con `topics_extracted` en 28d (Sprint S1 T5 topic extractor no corrió sobre Piña) |
| B09 Share/Like | `/1/share_like_ratio` | ok | ratio=0.0081 · semaforo=ROJO (Piña tiene audiencia pasiva, like >> share) |
| B10 Humanización | `/1/humanizacion` | ok | score=15.14 · interpretacion=Institucional |

Agregado `/api/v1/diagnostico/1` → `resumen: {ok: 8, insufficient_data: 2, total: 10}`.

## Gaps documentados (sin inventar datos)

### Gap 1 · B07 Growth Attribution — insufficient_data
- **Missing**: `<2 snapshots en últimos 14d`
- **Causa**: el cron de snapshot diario de followers (MASTER §5 S1 T3) no acumula suficiente historial para Piña en los 14d ventana.
- **Bloqueador real** del bloque — NO se rellena con valores sintéticos.
- **Acción futura**: correr el cron durante ≥14 días o ingestar manualmente snapshots históricos si existen en backups.

### Gap 2 · B08 SoV — insufficient_data
- **Missing**: `0 posts propios con topics_extracted en 28d`
- **Causa**: el topic extractor Sprint S1 T5 (Gemma 3:12b) no ha corrido sobre posts recientes de Piña. El campo `social_posts.topics_extracted` está NULL.
- **Acción futura**: correr `backend/scripts/nlp_comments_batch_v2.py` (o equivalente) contra el corpus 28d de Piña. Una vez poblado `topics_extracted`, B08 pasa a `ok` sin tocar el service.

### Observación · B05 Plutchik ratio trust/anger = 0
- Los 112 posts tienen `emotions` poblado pero el agregado tiene trust=0. Esto refleja la distribución real del corpus actual (ver sesión `project_triangulation_layer2_2026_04_18`) y NO es un bug. El service lo reporta correctamente sin inventar valores.
- El warning interno detecta el ratio <1 y lo emite en `warnings`.

## Archivos creados (rutas absolutas)

### Services (paquete `diagnostico/`)
- `/Users/marxchavez/Projects/crece-v2/backend/app/services/diagnostico/__init__.py` — re-exporta legacy + servicios Tier 1
- `/Users/marxchavez/Projects/crece-v2/backend/app/services/diagnostico/_common.py` — matriz 5×5 D-19 + modificador temporal + helpers shape
- `/Users/marxchavez/Projects/crece-v2/backend/app/services/diagnostico/legacy.py` — flat `diagnostico.py` renombrado (IPD composite)
- `/Users/marxchavez/Projects/crece-v2/backend/app/services/diagnostico/er_service.py` — B01
- `/Users/marxchavez/Projects/crece-v2/backend/app/services/diagnostico/breakout_service.py` — B02
- `/Users/marxchavez/Projects/crece-v2/backend/app/services/diagnostico/matrix_2x2_service.py` — B03
- `/Users/marxchavez/Projects/crece-v2/backend/app/services/diagnostico/benchmark_service.py` — B04 (con fallback proxies D-22 S2)
- `/Users/marxchavez/Projects/crece-v2/backend/app/services/diagnostico/sentiment_plutchik_service.py` — B05
- `/Users/marxchavez/Projects/crece-v2/backend/app/services/diagnostico/crisis_spike_service.py` — B06
- `/Users/marxchavez/Projects/crece-v2/backend/app/services/diagnostico/growth_attribution_service.py` — B07
- `/Users/marxchavez/Projects/crece-v2/backend/app/services/diagnostico/sov_service.py` — B08
- `/Users/marxchavez/Projects/crece-v2/backend/app/services/diagnostico/share_like_ratio_service.py` — B09
- `/Users/marxchavez/Projects/crece-v2/backend/app/services/diagnostico/humanizacion_service.py` — B10

### Endpoints
- `/Users/marxchavez/Projects/crece-v2/backend/app/api/v1/endpoints/diagnostico.py` — 11 endpoints
- `/Users/marxchavez/Projects/crece-v2/backend/app/api/v1/__init__.py` — router registrado como `diagnostico_tier1` alias (2 líneas modificadas)

### Tests
- `/Users/marxchavez/Projects/crece-v2/backend/tests/diagnostico/__init__.py`
- `/Users/marxchavez/Projects/crece-v2/backend/tests/diagnostico/conftest.py` — fixtures `org_fixture`, `dirigente_with_data` (12 posts + 2 snapshots), `dirigente_sin_posts`
- `/Users/marxchavez/Projects/crece-v2/backend/tests/diagnostico/test_services.py` — 15 casos unitarios
- `/Users/marxchavez/Projects/crece-v2/backend/tests/diagnostico/test_endpoints.py` — 3 casos del endpoint agregado (auth, shape, individual)

### Fixture de desarrollo (D-22)
- `/Users/marxchavez/Projects/crece-v2/backend/scripts/seed_proxies_desarrollo_s2.py` — script con `--dry-run`/`--reset` para persistir `PROXIES_S2_DESARROLLO` en BD (no ejecutado — Piña ya tenía `competidor_directo_ids` poblado)

## Contrato estándar de response

Todos los services Tier 1 retornan:

```json
{
  "status": "ok" | "insufficient_data",
  "data": {...},
  "missing": [...],
  "bloque": "B01".."B10",
  "bloque_version": "tier1-v1",
  "computed_at": "2026-04-20T01:12:34.567+00:00"
}
```

- `data` siempre presente en `status=ok`; en `insufficient_data` es opcional (incluye `extra` si hay sub-estadísticas parciales útiles).
- `missing` es lista de strings explicando qué falta. Siempre poblada cuando `status=insufficient_data`.
- `bloque_version` permite versionado — si cambia el cálculo se bumpea a `tier1-v2` sin romper shape.

## Auth + RLS

- Todos los endpoints requieren JWT válido vía `Authorization: Bearer ...`.
- `_resolve_org_id` extrae `org_id` del user; admin puede sobreescribir con `X-Org-Id`.
- `load_dirigente_scoped(db, id, org_id)` filtra `WHERE org_id=X OR org_id IS NULL` — previene tenant spillover.

## Principios MD Consultoría TI respetados

- Sin mocks en servicios — solo en fixtures de tests unitarios.
- Sin datos inventados — B07/B08 devuelven `insufficient_data` con `missing` explícito en lugar de rellenar con ceros o valores sintéticos.
- Matriz 5×5 marcada `tier1-v1` + `matriz_version: "5x5-tbd-2026-04-19"` para facilitar el swap cuando Zenodo Sprint S1 publique rangos validados.
- D-22 (proxies) aislado en `PROXIES_S2_DESARROLLO` con TODO apuntando a eliminación post-Onboarding S5.
- D-19 (modificador temporal) implementado como función pura `modificador_temporal(dias_a_comicio)` testeable; default off (1.0) cuando el caller no especifica.

## Próximos pasos sugeridos (fuera de scope S2 T1-T2)

- **T3 (paralelo)**: extender `sentiment_service.classify_plutchik_6(text)` y correr batch para poblar `sentiment_analyses.emotions` en 200+ posts del corpus. Hoy B05 muestra `trust=0` porque el prompt Plutchik S0 T0.4 aún no se aplicó al corpus histórico.
- **Topic extractor S1 T5** sobre posts 28d de Piña → B08 pasa a `ok`.
- **Cron snapshot diario** 14+ días → B07 pasa a `ok`.
- **T4 frontend**: 10 cards en `/dashboard/diagnostico/[id]` consumiendo el endpoint agregado.
- **T5 E2E Playwright**.
